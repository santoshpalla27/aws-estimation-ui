import json
import logging
import ijson
import os
import sqlite3
from pathlib import Path
from backend.app.core.database import get_db_connection
from backend.app.core.pricing_db import create_pricing_table, insert_pricing_batch, should_skip_normalization, update_normalization_metadata, create_index

logger = logging.getLogger(__name__)

def populate_temp_terms(conn: sqlite3.Connection, raw_file_path: str):
    """
    Pass 1: Stream 'terms.OnDemand' to a temporary SQLite table.
    Map: sku -> price
    """
    logger.info("EC2: Pass 1 - Extracting pricing terms...")
    
    conn.execute("CREATE TEMP TABLE IF NOT EXISTS temp_terms (sku TEXT PRIMARY KEY, price REAL)")
    conn.execute("DELETE FROM temp_terms") # Clear if reusing conn
    
    count = 0
    batch = []
    BATCH_SIZE = 5000
    
    try:
        with open(raw_file_path, 'rb') as f: # specific for ijson binary
            # ijson.kvitems(f, 'terms.OnDemand') yields (sku, term_dict)
            for sku, terms_dict in ijson.kvitems(f, 'terms.OnDemand'):
                # Logic to extract price:
                # term_dict is { "termCode": { ... priceDimensions: { ... pricePerUnit: { "USD": "0.123"} } } }
                
                price = 0.0
                if terms_dict:
                     # Get first term (often there's only one OnDemand term per SKU)
                    first_term_key = next(iter(terms_dict))
                    term = terms_dict[first_term_key]
                    
                    price_dims = term.get('priceDimensions', {})
                    if price_dims:
                         first_pd_key = next(iter(price_dims))
                         price_str = price_dims[first_pd_key].get('pricePerUnit', {}).get('USD', '0')
                         try:
                             price = float(price_str)
                         except ValueError:
                             price = 0.0
                
                batch.append((sku, price))
                count += 1
                
                if len(batch) >= BATCH_SIZE:
                    conn.executemany("INSERT OR IGNORE INTO temp_terms (sku, price) VALUES (?, ?)", batch)
                    batch = []
                    
            if batch:
                 conn.executemany("INSERT OR IGNORE INTO temp_terms (sku, price) VALUES (?, ?)", batch)
                 
    except Exception as e:
        logger.error(f"EC2: Term extraction failed: {e}")
        # Identify if ijson failed or file issue
        raise

    logger.info(f"EC2: Pass 1 complete. Loaded {count} terms.")

def normalize(raw_file, output_db_path=None):
    """
    Normalizes EC2 raw pricing data into SQLite using streaming.
    """
    if not output_db_path:
        # Default to data/pricing.db
         base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
         output_db_path = os.path.join(base_dir, 'data', 'pricing.db')
    
    logger.info(f"EC2: Checking normalization for {raw_file}...")
    
    raw_path = Path(raw_file)
    if not raw_path.exists():
        logger.error(f"EC2: Raw file {raw_file} not found.")
        return

    raw_mtime = raw_path.stat().st_mtime
    
    conn = get_db_connection(output_db_path)
    create_pricing_table(conn, 'ec2')
    # Create indexes for optimized queries
    create_index(conn, 'ec2', ['instanceType', 'vcpu', 'memory', 'operatingSystem', 'networkPerformance', 'storage'])
    
    if should_skip_normalization(conn, 'ec2', raw_mtime):
        logger.info("EC2: Data is up-to-date. Skipping normalization.")
        conn.close()
        return

    try:
        # 1. Populate Terms (Pass 1)
        populate_temp_terms(conn, raw_file)
        
        # 2. Process Products (Pass 2)
        logger.info("EC2: Pass 2 - Normalizing products...")
        
        # We prepare to insert into final table.
        # We can do this via python streaming or pure SQL if we loaded products to temp.
        # But products have complex attributes we want to flatten/json-ify. 
        # Python streaming of products -> lookup in temp_terms -> insert is good.
        
        # However, looking up in temp_terms 1-by-1 in python loop is slow (SELECT ...).
        # Better: 
        #   Batch products in Python.
        #   For each batch, do a bulk query/join? 
        #   OR: Load 'products' into `temp_products` table and then do one big INSERT INTO final SELECT ... JOIN ...
        #   "Load products to temp table" approach is cleaner for logic if JSON is simple. 
        #   But 'attributes' parsing might be easier in Python.
        
        # Optimization: Read `temp_terms` into memory dict? 
        # If 100k items * 16 bytes (sku+float) ~ 2MB. 
        # EC2 has >500k skus? 10-20MB. Very feasible to load terms into memory map!
        
        # Let's switch strategy slightly: Load temp_terms to dict for fast O(1) lookup.
        cursor = conn.execute("SELECT sku, price FROM temp_terms")
        price_map = {row[0]: row[1] for row in cursor}
        logger.info(f"EC2: Loaded {len(price_map)} prices into memory cache.")
        
        # Clear temp table to free sqlite resources (though specific to session)
        conn.execute("DROP TABLE temp_terms")
        conn.commit()
        
        count = 0
        batch = []
        batch_size = 2000
        summary_samples = []

        with open(raw_file, 'rb') as f:
            for sku, product in ijson.kvitems(f, 'products'):
                attr = product.get('attributes', {})
                if attr.get('servicecode') != 'AmazonEC2':
                    continue
                if attr.get('productFamily') != 'Compute Instance':
                    continue
                
                # Lookup Price
                price = price_map.get(sku, 0.0)
                
                # Prepare Item
                item = {
                    "sku": sku,
                    "price": price,
                    "location": attr.get('location'),
                    "attributes": {
                        "instanceType": attr.get('instanceType'),
                        "vcpu": attr.get('vcpu'),
                        "memory": attr.get('memory'),
                        "operatingSystem": attr.get('operatingSystem'),
                        "networkPerformance": attr.get('networkPerformance'),
                        "physicalProcessor": attr.get('physicalProcessor'),
                        "clockSpeed": attr.get('clockSpeed'),
                        "storage": attr.get('storage'),
                        "gpu": attr.get('gpu'), # sometimes present
                    }
                }
                
                batch.append(item)
                if len(summary_samples) < 100:
                    summary_samples.append(item)
                
                if len(batch) >= batch_size:
                    insert_pricing_batch(conn, 'ec2', batch)
                    count += len(batch)
                    batch = []
                    if count % 10000 == 0:
                        logger.info(f"EC2: Processed {count} products...")
            
            if batch:
                insert_pricing_batch(conn, 'ec2', batch)
                count += len(batch)
                
        update_normalization_metadata(conn, 'ec2', raw_mtime)
        logger.info(f"EC2: Normalization complete. inserted {count} rows.")
        
        # Write Summary JSON for acceptance criteria
        summary_path = raw_path.parent.parent / 'normalized' / 'ec2' / 'summary.json'
        if not summary_path.parent.exists():
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            
        with open(summary_path, 'w') as f:
            json.dump({
                "count": count,
                "samples": summary_samples
            }, f, indent=2)
            
    except Exception as e:
        logger.error(f"EC2: Normalization failed: {e}")
        # Don't rollback whole transaction logic here as we committed batches.
        # But we haven't updated metadata, so it will retry next time.
    finally:
        conn.close()
