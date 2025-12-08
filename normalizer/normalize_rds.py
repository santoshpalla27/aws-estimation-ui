import ijson
import json
import sqlite3
import os

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

def parse_products(cursor, file_path):
    print("Parsing RDS Products...")
    with open(file_path, 'rb') as f:
        products = ijson.kvitems(f, 'products')
        
        count = 0
        batch = []
        for sku, product in products:
            attr = product.get('attributes', {})
            
            if attr.get('productFamily') != 'Database Instance':
                continue

            region = attr.get('regionCode', 'us-east-1')
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
    print("\nProducts done.")

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

def export_json(cursor):
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
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(normalized, f, indent=0)
    print(f"Exported {len(normalized)} records to {OUTPUT_FILE}")

def main():
    if not os.path.exists(RAW_FILE):
        print(f"File not found: {RAW_FILE}")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    init_db(cursor)
    
    try:
        parse_products(cursor, RAW_FILE)
        conn.commit()
        
        parse_terms(cursor, RAW_FILE)
        conn.commit()
        
        export_json(cursor)
        
    finally:
        conn.close()
        # os.remove(DB_FILE)

if __name__ == "__main__":
    main()
