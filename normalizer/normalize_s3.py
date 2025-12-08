import ijson
import json
import sqlite3
import os

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
            volume_type TEXT
        )
    ''')
    cursor.execute('DROP TABLE IF EXISTS prices')
    cursor.execute('''
        CREATE TABLE prices (
            sku TEXT,
            unit TEXT,
            price REAL,
            description TEXT
        )
    ''') 

def parse_products(cursor, file_path):
    print("Parsing S3 Products...")
    with open(file_path, 'rb') as f:
        products = ijson.kvitems(f, 'products')
        
        count = 0
        batch = []
        for sku, product in products:
            attr = product.get('attributes', {})
            
            # S3 has many families: Storage, Data Transfer, API Request, etc.
            fam = attr.get('productFamily')
            if fam not in ['Storage', 'API Request', 'Fee']: # Filter out Transfer for now if too complex
                # Actually user wants 'Data transfer' calculator. We should include it.
                # However, Data Transfer is often shared or global.
                pass 
            
            region = attr.get('regionCode', 'us-east-1')
            s_class = attr.get('storageClass')
            vol_type = attr.get('volumeType')

            batch.append((sku, region, fam, s_class, vol_type))
            
            if len(batch) >= 10000:
                cursor.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?)", batch)
                batch = []
                count += 10000
                print(f"Products processed: {count}...", end='\r')
        
        if batch:
            cursor.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?)", batch)
    print("\nProducts done.")

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
                    
                    if price_unit:
                        batch.append((sku, unit, float(price_unit), desc))
            
            if len(batch) >= 10000:
                cursor.executemany("INSERT OR IGNORE INTO prices VALUES (?,?,?,?)", batch)
                batch = []
                count += 10000
                print(f"Terms processed: {count}...", end='\r')
        
        if batch:
            cursor.executemany("INSERT OR IGNORE INTO prices VALUES (?,?,?,?)", batch)
    print("\nTerms done.")

def export_json(cursor, output_file):
    print("Exporting S3 to JSON...")
    cursor.execute('''
        SELECT p.region, p.product_family, p.storage_class, pr.unit, pr.price
        FROM products p
        JOIN prices pr ON p.sku = pr.sku
    ''')
    
    rows = cursor.fetchall()
    
    normalized = []
    # Reduce size
    for r in rows:
        normalized.append({
            "service": "S3",
            "region": r[0],
            "family": r[1],
            "class": r[2],
            "unit": r[3],
            "price": r[4]
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
