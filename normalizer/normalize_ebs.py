import ijson
import json
import sqlite3
import os
import sys

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Default paths (can be overridden by args)
RAW_FILE = os.path.join(BASE_DIR, "data", "raw", "amazonec2_pricing.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "normalized", "amazonebs.json")
DB_FILE = os.path.join(BASE_DIR, "data", "ebs_temp.db")

from region_utils import resolve_region

def init_db(cursor):
    cursor.execute('DROP TABLE IF EXISTS products')
    cursor.execute('''
        CREATE TABLE products (
            sku TEXT PRIMARY KEY,
            region TEXT,
            volume_api_name TEXT,
            volume_type TEXT,
            group_desc TEXT,
            usage_type TEXT
        )
    ''')
    cursor.execute('DROP TABLE IF EXISTS prices')
    cursor.execute('''
        CREATE TABLE prices (
            sku TEXT,
            term_type TEXT,
            price REAL,
            unit TEXT,
            description TEXT,
            UNIQUE(sku, term_type, unit) 
        )
    ''') 
    # Added unit to unique constraint because same SKU might have different dimensions? 
    # Usually EBS SKU is specific, but sometimes ranges.

def parse_products(cursor, file_path):
    print("Parsing Products (EBS)...")
    with open(file_path, 'rb') as f:
        products = ijson.kvitems(f, 'products')
        
        count = 0
        batch = []
        for sku, product in products:
            attr = product.get('attributes', {})
            family = attr.get('productFamily')

            # Filter for Storage / EBS
            # Common flags: 
            # productFamily = "Storage" (sometimes "System Operation" for IOPS?)
            # attributes[volumeApiName] exists (e.g. gp2, io1)
            
            # We specifically want EBS Volumes (Storage)
            # Some IOPS charges come as "System Operation" family but stick to volumeApiName check.
            
            vol_api = attr.get('volumeApiName')
            
            # Robust filter: Must have volumeApiName OR be standard storage
            if not vol_api:
                # Sometimes standard magnetic doesn't have api name?
                # Check usageType for "EBS:VolumeUsage"
                ut = attr.get('usagetype', '')
                if 'EBS:VolumeUsage' not in ut and 'EBS:VolumeP-IOPS' not in ut:
                    continue

            region = resolve_region(attr)
            if not region: continue
            
            vol_type = attr.get('volumeType') # General Purpose, Provisioned IOPS
            group = attr.get('group') # EBS IOPS?
            usage_type = attr.get('usagetype')

            batch.append((sku, region, vol_api, vol_type, group, usage_type))
            
            if len(batch) >= 10000:
                cursor.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?,?)", batch)
                batch = []
                count += 10000
                print(f"EBS Products processed: {count}...", end='\r')
        
        if batch:
            cursor.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?,?)", batch)
    print(f"\nEBS Products done.")

def parse_terms(cursor, file_path):
    print("Parsing Terms (OnDemand)...")
    with open(file_path, 'rb') as f:
        terms = ijson.kvitems(f, 'terms.OnDemand')
        count = 0
        batch = []
        for sku, offers in terms:
            for offer_code, offer in offers.items():
                for dim_code, dim in offer.get('priceDimensions', {}).items():
                    price_unit = dim.get('pricePerUnit', {}).get('USD')
                    unit = dim.get('unit') # GB-Mo, IOPS-Mo
                    desc = dim.get('description')
                    
                    if price_unit and unit:
                        batch.append((sku, 'OnDemand', float(price_unit), unit, desc))
            
            if len(batch) >= 10000:
                cursor.executemany("INSERT OR IGNORE INTO prices VALUES (?,?,?,?,?)", batch)
                batch = []
                count += 10000
                print(f"Terms processed: {count}...", end='\r')
        
        if batch:
            cursor.executemany("INSERT OR IGNORE INTO prices VALUES (?,?,?,?,?)", batch)
    print("\nTerms done.")

def export_json(cursor, output_file):
    print("Exporting EBS to JSON...")
    # Select joined data
    # Filter for standard storage units (GB-Mo) mostly, but user might want IOPS
    # User said: "unit (GB-Mo)". We will prioritize GB-Mo but keep others if useful (maybe filter in query)
    
    cursor.execute('''
        SELECT p.region, p.volume_api_name, p.volume_type, pr.unit, pr.price, p.usage_type
        FROM products p
        JOIN prices pr ON p.sku = pr.sku
        WHERE pr.term_type = 'OnDemand'
        AND (pr.unit LIKE '%GB-Mo%' OR pr.unit LIKE '%IOPS-Mo%')
    ''')
    
    rows = cursor.fetchall()
    normalized = []
    
    for r in rows:
        normalized.append({
            "service": "AmazonEBS",
            "region": r[0],
            "attributes": {
                "volumeApiName": r[1], # gp2, gp3
                "volumeType": r[2],    # General Purpose SSD
                "usagetype": r[5]
            },
            "unit": r[3],
            "ondemand": str(r[4]), # Keep as string for precision? or float logic
            "price": str(r[4])
        })
    
    with open(output_file, 'w') as f:
        json.dump(normalized, f, indent=0)
    print(f"Exported {len(normalized)} EBS records to {output_file}")

def main():
    raw_file = RAW_FILE
    output_file = OUTPUT_FILE
    
    if len(sys.argv) > 2:
        raw_file = sys.argv[1]
        output_file = sys.argv[2] # This might be passed as amazonec2.json if main calls it generic
        # Wait, main calls with output file logic. 
        # If we call this manually/specifically, we should ensure output is amazonebs.json
        if "amazonec2" in output_file and "ebs" not in output_file.lower():
             output_file = output_file.replace("amazonec2", "amazonebs").replace("ec2", "ebs")

    if not os.path.exists(raw_file):
        print(f"File not found: {raw_file}")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    init_db(cursor)
    
    try:
        parse_products(cursor, raw_file)
        conn.commit()
        
        parse_terms(cursor, raw_file)
        conn.commit()
        
        export_json(cursor, output_file)
        
    finally:
        conn.close()
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)

if __name__ == "__main__":
    main()
