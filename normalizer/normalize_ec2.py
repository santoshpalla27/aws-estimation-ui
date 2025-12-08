import ijson
import json
import sqlite3
import os
import sys

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_FILE = os.path.join(BASE_DIR, "data", "raw", "ec2_pricing.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "normalized", "ec2.json")
DB_FILE = os.path.join(BASE_DIR, "data", "ec2_temp.db")

def init_db(cursor):
    cursor.execute('DROP TABLE IF EXISTS products')
    cursor.execute('''
        CREATE TABLE products (
            sku TEXT PRIMARY KEY,
            region TEXT,
            instance_type TEXT,
            vcpu INTEGER,
            memory TEXT,
            storage TEXT,
            network TEXT,
            os TEXT
        )
    ''')
    cursor.execute('DROP TABLE IF EXISTS prices')
    cursor.execute('''
        CREATE TABLE prices (
            sku TEXT,
            term_type TEXT,
            price REAL,
            UNIQUE(sku, term_type)
        )
    ''') 
    # term_type: 'OnDemand', 'Reserved-1yr-NoUpfront', 'Spot' (Spot is separate API usually? user said bulk file.)
    # Bulk file has OnDemand and Reserved. Spot is usually separate or not in this file (Spot is dynamic).
    # User said "Spot toggle" in features. Bulk API often *doesn't* have Spot.
    # We will focus on OnDemand/Reserved for now.

def parse_products(cursor, file_path):
    print("Parsing Products...")
    with open(file_path, 'rb') as f:
        # AWS JSON structure: {"products": { "SKU": { "attributes": {...} } } }
        # ijson.kvitems(f, 'products') yields (key, value)
        products = ijson.kvitems(f, 'products')
        
        count = 0
        batch = []
        for sku, product in products:
            attr = product.get('attributes', {})
            if attr.get('servicecode') != 'AmazonEC2': 
                continue # Generic filter
            
            # We strictly want Compute Instances usually, or Dedicated Host.
            # "productFamily" == "Compute Instance"
            if attr.get('productFamily') != 'Compute Instance':
                continue

            region = attr.get('regionCode', 'us-east-1') # specific field 'regionCode' exists in newer files? 
            # Often it's 'location' (Human readable) -> needs mapping? 
            # Wait, AWS Bulk API 1.0 often doesn't have regionCode in attributes?
            # It usually splits by region file? NO, the link was `index.json` which is ALL REGIONS (7GB).
            # If so, 'regionCode' should be in attributes.
            
            # Attributes
            instance_type = attr.get('instanceType')
            vcpu = attr.get('vcpu')
            memory = attr.get('memory')
            storage = attr.get('storage')
            network = attr.get('networkPerformance')
            os_type = attr.get('operatingSystem')

            batch.append((sku, region, instance_type, vcpu, memory, storage, network, os_type))
            
            if len(batch) >= 10000:
                cursor.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?,?,?,?)", batch)
                batch = []
                count += 10000
                print(f"Products processed: {count}...", end='\r')
        
        if batch:
            cursor.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?,?,?,?)", batch)
    print("\nProducts done.")

def parse_terms(cursor, file_path):
    print("Parsing Terms (OnDemand)...")
    # terms -> OnDemand -> SKU -> Key -> priceDimensions -> Key -> pricePerUnit -> USD
    with open(file_path, 'rb') as f:
        terms = ijson.kvitems(f, 'terms.OnDemand')
        count = 0
        batch = []
        for sku, offers in terms:
            for offer_code, offer in offers.items():
                for dim_code, dim in offer.get('priceDimensions', {}).items():
                    price_unit = dim.get('pricePerUnit', {}).get('USD')
                    if price_unit:
                        batch.append((sku, 'OnDemand', float(price_unit)))
            
            if len(batch) >= 10000:
                cursor.executemany("INSERT OR IGNORE INTO prices VALUES (?,?,?)", batch)
                batch = []
                count += 10000
                print(f"OnDemand terms processed: {count}...", end='\r')
        
        if batch:
            cursor.executemany("INSERT OR IGNORE INTO prices VALUES (?,?,?)", batch)
    print("\nOnDemand done.")
    
    # Reserved parsing is complex (Terms/Reserved). Can be added similarly.
    # For MVP we do OnDemand.

def export_json(cursor, output_file):
    print("Exporting to JSON...")
    # Join products and prices
    # We want structured output: [{service: EC2, region:..., instance:..., price: ...}]
    cursor.execute('''
        SELECT p.region, p.instance_type, p.vcpu, p.memory, p.os, pr.price
        FROM products p
        JOIN prices pr ON p.sku = pr.sku
        WHERE p.instance_type IS NOT NULL
        AND pr.term_type = 'OnDemand'
    ''')
    
    rows = cursor.fetchall()
    
    # Organize by Region -> Instance -> OS? Or flat list? 
    # User requested: "service": "EC2", "region": "ap-south-1", "instance": "t3.micro", "ondemand": 0.0104
    
    normalized = []
    # Optimization: Dict lookup? 
    # Let's just dump the list.
    
    for r in rows:
        normalized.append({
            "service": "EC2",
            "region": r[0],
            "instance": r[1],
            "vcpu": r[2],
            "memory": r[3],
            "os": r[4],
            "ondemand": r[5]
        })
    
    with open(output_file, 'w') as f:
        json.dump(normalized, f, indent=0) # Compact JSON
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
        
        # We need to pass output_file to export_json or modify export_json to take it
        export_json(cursor, output_file)
        
    finally:
        conn.close()
        # os.remove(DB_FILE)

if __name__ == "__main__":
    main()
