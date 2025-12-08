import ijson
import json
import sqlite3
import os
import sys

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_FILE = os.path.join(BASE_DIR, "data", "raw", "rds_pricing.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "normalized", "rds.json")
DB_FILE = os.path.join(BASE_DIR, "data", "rds_temp.db")

def init_db(cursor):
    cursor.execute('DROP TABLE IF EXISTS products')
    cursor.execute('''
        CREATE TABLE products (
            sku TEXT PRIMARY KEY,
            region TEXT,
            engine TEXT,
            instance_type TEXT,
            deployment_option TEXT
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

from region_utils import resolve_region

def parse_products(cursor, file_path):
    print("Parsing RDS Products...")
    with open(file_path, 'rb') as f:
        products = ijson.kvitems(f, 'products')
        
        count = 0
        discard_count = 0
        batch = []
        for sku, product in products:
            attr = product.get('attributes', {})
            
            if attr.get('productFamily') != 'Database Instance':
                continue

            region = resolve_region(attr)
            
            if not region:
                discard_count += 1
                continue

            engine = attr.get('databaseEngine')
            instance = attr.get('instanceType')
            deployment = attr.get('deploymentOption') # Single-AZ, Multi-AZ

            batch.append((sku, region, engine, instance, deployment))
            
            if len(batch) >= 10000:
                cursor.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?)", batch)
                batch = []
                count += 10000
                print(f"Products processed: {count}...", end='\r')
        
        if batch:
            cursor.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?)", batch)
    print(f"\nProducts done. Discarded {discard_count} records due to missing region.")

def parse_terms(cursor, file_path):
    print("Parsing RDS Terms (OnDemand)...")
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
                print(f"Terms processed: {count}...", end='\r')
        
        if batch:
            cursor.executemany("INSERT OR IGNORE INTO prices VALUES (?,?,?)", batch)
    print("\nTerms done.")

def export_json(cursor, output_file):
    print("Exporting RDS to JSON...")
    cursor.execute('''
        SELECT p.region, p.engine, p.instance_type, p.deployment_option, pr.price
        FROM products p
        JOIN prices pr ON p.sku = pr.sku
        WHERE p.instance_type IS NOT NULL
        AND pr.term_type = 'OnDemand'
    ''')
    
    rows = cursor.fetchall()
    
    normalized = []
    for r in rows:
        normalized.append({
            "service": "RDS",
            "region": r[0],
            "engine": r[1],
            "instance": r[2],
            "deployment": r[3],
            "ondemand": r[4]
        })
    
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
