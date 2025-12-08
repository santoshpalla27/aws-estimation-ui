import ijson
import json
import sqlite3
import os
import sys

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_FILE = os.path.join(BASE_DIR, "data", "raw", "s3_pricing.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "normalized", "s3.json")
DB_FILE = os.path.join(BASE_DIR, "data", "s3_temp.db")


def init_db(cursor):
    cursor.execute('DROP TABLE IF EXISTS products')
    cursor.execute('''
        CREATE TABLE products (
            sku TEXT PRIMARY KEY,
            region TEXT,
            product_family TEXT,
            storage_class TEXT,
            volume_type TEXT,
            group_attr TEXT,
            transfer_type TEXT,
            from_loc TEXT,
            to_loc TEXT
        )
    ''')
    cursor.execute('DROP TABLE IF EXISTS prices')
    cursor.execute('''
        CREATE TABLE prices (
            sku TEXT,
            unit TEXT,
            price REAL,
            description TEXT,
            begin_range TEXT,
            end_range TEXT,
            UNIQUE(sku, begin_range, end_range)
        )
    ''') 

from region_utils import resolve_region

def parse_products(cursor, file_path):
    print("Parsing S3 Products...")
    with open(file_path, 'rb') as f:
        products = ijson.kvitems(f, 'products')
        
        count = 0
        discard_count = 0
        batch = []
        for sku, product in products:
            attr = product.get('attributes', {})
            
            fam = attr.get('productFamily')
            # Allow Storage, API Request, Fee, and Data Transfer
            if fam not in ['Storage', 'API Request', 'Fee', 'Data Transfer']:
                continue 
            
            region = resolve_region(attr)
            
            if not region:
                discard_count += 1
                continue

            s_class = attr.get('storageClass')
            vol_type = attr.get('volumeType')
            group = attr.get('group') 
            
            # Data Transfer attributes
            transfer_type = attr.get('transferType')
            from_loc = attr.get('fromLocation')
            to_loc = attr.get('toLocation')

            batch.append((sku, region, fam, s_class, vol_type, group, transfer_type, from_loc, to_loc))
            
            if len(batch) >= 10000:
                cursor.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?,?,?,?,?)", batch)
                batch = []
                count += 10000
                print(f"Products processed: {count}...", end='\r')
        
        if batch:
            cursor.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?,?,?,?,?)", batch)
    print(f"\nProducts done. Discarded {discard_count} records due to missing region.")

def parse_terms(cursor, file_path):
    print("Parsing S3 Terms...")
    with open(file_path, 'rb') as f:
        terms = ijson.kvitems(f, 'terms.OnDemand')
        count = 0
        batch = []
        for sku, offers in terms:
            for offer_code, offer in offers.items():
                for dim_code, dim in offer.get('priceDimensions', {}).items():
                    price_unit = dim.get('pricePerUnit', {}).get('USD')
                    unit = dim.get('unit')
                    desc = dim.get('description')
                    begin_r = dim.get('beginRange')
                    end_r = dim.get('endRange')
                    
                    if price_unit:
                        batch.append((sku, unit, float(price_unit), desc, begin_r, end_r))
            
            if len(batch) >= 10000:
                cursor.executemany("INSERT OR IGNORE INTO prices VALUES (?,?,?,?,?,?)", batch)
                batch = []
                count += 10000
                print(f"Terms processed: {count}...", end='\r')
        
        if batch:
            cursor.executemany("INSERT OR IGNORE INTO prices VALUES (?,?,?,?,?,?)", batch)
    print("\nTerms done.")

def export_json(cursor, output_file):
    print("Exporting S3 to JSON...")
    cursor.execute('''
        SELECT p.region, p.product_family, p.storage_class, p.group_attr, 
               p.transfer_type, p.from_loc, p.to_loc,
               pr.unit, pr.price, pr.begin_range, pr.end_range
        FROM products p
        JOIN prices pr ON p.sku = pr.sku
    ''')
    
    rows = cursor.fetchall()
    
    normalized = []
    for r in rows:
        item = {
            "service": "S3",
            "region": r[0],
            "family": r[1],
            "unit": r[7],
            "price": r[8]
        }
        
        # Add optional fields only if they exist to keep JSON clean
        if r[2]: item["class"] = r[2]
        if r[3]: item["group"] = r[3]
        if r[4]: item["transferType"] = r[4]
        if r[5]: item["fromLocation"] = r[5]
        if r[6]: item["toLocation"] = r[6]
        if r[9]: item["beginRange"] = r[9]
        if r[10]: item["endRange"] = r[10]
        
        normalized.append(item)
    
    with open(output_file, 'w') as f:
        json.dump(normalized, f, indent=0)
    print(f"Exported {len(normalized)} records to {output_file}")

def main():
    # Allow command line args for file paths
    raw_file = RAW_FILE
    output_file = OUTPUT_FILE
    
    if len(sys.argv) > 2:
        raw_file = sys.argv[1]
        output_file = sys.argv[2]
        
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
        # os.remove(DB_FILE)

if __name__ == "__main__":
    main()
