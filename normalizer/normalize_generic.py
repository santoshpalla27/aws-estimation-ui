import ijson
import json
import sqlite3
import os
import sys

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Function to be called by main.py
def normalize_generic(service_name, raw_file, output_file):
    print(f"Generic Normalization for {service_name}...")
    
    db_file = os.path.join(BASE_DIR, "data", f"{service_name}_temp.db")
    
    # SQLite to handle volume
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    cursor.execute('DROP TABLE IF EXISTS products')
    cursor.execute('CREATE TABLE products (sku TEXT PRIMARY KEY, region TEXT, attributes TEXT)')
    
    cursor.execute('DROP TABLE IF EXISTS prices')
    cursor.execute('CREATE TABLE prices (sku TEXT, unit TEXT, price REAL, description TEXT)')
    
    # 1. Products
    print(f"  Parsing Products...")
    try:
        with open(raw_file, 'rb') as f:
            # ijson generator
            products = ijson.kvitems(f, 'products')
            batch = []
            count = 0
            
            for sku, product in products:
                attr = product.get('attributes', {})
                region = attr.get('regionCode', 'us-east-1') # specific field
                if not region and 'location' in attr:
                     # Heuristic for region if code missing?
                     pass
                
                # Store attributes as JSON string
                batch.append((sku, region, json.dumps(attr)))
                
                if len(batch) >= 5000:
                    cursor.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?)", batch)
                    batch = []
                    count += 5000
                    print(f"  {count} products...", end='\r')
            
            if batch:
                 cursor.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?)", batch)
                 
    except Exception as e:
        print(f"  Error parsing products: {e}")
        conn.close()
        return

    # 2. Terms
    print(f"\n  Parsing Terms...")
    try:
        with open(raw_file, 'rb') as f:
            terms = ijson.kvitems(f, 'terms.OnDemand')
            batch = []
            count = 0
            
            for sku, offers in terms:
                for offer_code, offer in offers.items():
                    for dim_code, dim in offer.get('priceDimensions', {}).items():
                         price_unit = dim.get('pricePerUnit', {}).get('USD')
                         unit = dim.get('unit')
                         desc = dim.get('description')
                         
                         if price_unit:
                             batch.append((sku, unit, float(price_unit), desc))
                             # Take first valid price dimension for simplicity in generic
                             break 
                
                if len(batch) >= 5000:
                    cursor.executemany("INSERT OR IGNORE INTO prices VALUES (?,?,?,?)", batch)
                    batch = []
                    count += 5000
                    print(f"  {count} terms...", end='\r')
            
            if batch:
                cursor.executemany("INSERT OR IGNORE INTO prices VALUES (?,?,?,?)", batch)

    except Exception as e:
        print(f"  Error parsing terms: {e}")

    # 3. Export
    print(f"\n  Exporting...")
    cursor.execute('''
        SELECT p.region, p.attributes, pr.unit, pr.price, pr.description
        FROM products p
        JOIN prices pr ON p.sku = pr.sku
    ''')
    
    normalized = []
    
    while True:
        rows = cursor.fetchmany(1000)
        if not rows:
            break
        for r in rows:
            attr = json.loads(r[1])
            normalized.append({
                "service": service_name,
                "region": r[0],
                "attributes": attr,
                "unit": r[2],
                "price": r[3],
                "description": r[4]
            })
            
    with open(output_file, 'w') as f:
        json.dump(normalized, f, indent=0)
    
    print(f"  Saved {len(normalized)} items to {os.path.basename(output_file)}")
    
    conn.close()
    try:
        os.remove(db_file)
    except:
        pass

if __name__ == "__main__":
    # Test standalone
    if len(sys.argv) > 2:
        normalize_generic("test", sys.argv[1], sys.argv[2])
