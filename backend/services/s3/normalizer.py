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
    logger.info("S3: Pass 1 - Extracting pricing terms...")
    conn.execute("CREATE TEMP TABLE IF NOT EXISTS temp_terms (sku TEXT PRIMARY KEY, price REAL)")
    conn.execute("DELETE FROM temp_terms") 
    
    count = 0
    batch = []
    BATCH_SIZE = 5000
    
    try:
        with open(raw_file_path, 'rb') as f:
            for sku, terms_dict in ijson.kvitems(f, 'terms.OnDemand'):
                price = 0.0
                if terms_dict:
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
        logger.error(f"S3: Term extraction failed: {e}")
        raise
    logger.info(f"S3: Pass 1 complete. Loaded {count} terms.")

def normalize(raw_file, output_db_path=None):
    if not output_db_path:
         base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
         output_db_path = os.path.join(base_dir, 'data', 'pricing.db')
    
    logger.info(f"S3: Checking normalization for {raw_file}...")
    
    raw_path = Path(raw_file)
    if not raw_path.exists():
        logger.error(f"S3: Raw file {raw_file} not found.")
        return

    raw_mtime = raw_path.stat().st_mtime
    conn = get_db_connection(output_db_path)
    create_pricing_table(conn, 's3')
    create_index(conn, 's3', ['productFamily', 'storageClass', 'volumeType'])
    
    if should_skip_normalization(conn, 's3', raw_mtime):
        logger.info("S3: Data is up-to-date. Skipping normalization.")
        conn.close()
        return

    try:
        populate_temp_terms(conn, raw_file)
        
        logger.info("S3: Pass 2 - Normalizing products...")
        cursor = conn.execute("SELECT sku, price FROM temp_terms")
        price_map = {row[0]: row[1] for row in cursor}
        conn.execute("DROP TABLE temp_terms")
        conn.commit()
        
        count = 0
        batch = []
        batch_size = 2000
        summary_samples = []

        with open(raw_file, 'rb') as f:
            for sku, product in ijson.kvitems(f, 'products'):
                attr = product.get('attributes', {})
                if attr.get('servicecode') != 'AmazonS3':
                    continue
                
                price = price_map.get(sku, 0.0)
                
                item = {
                    "sku": sku,
                    "price": price,
                    "location": attr.get('location'),
                    "attributes": {
                        "productFamily": attr.get('productFamily'),
                        "storageClass": attr.get('storageClass'),
                        "volumeType": attr.get('volumeType'),
                        "dataTransferType": attr.get('dataTransferType'),
                        "fromLocation": attr.get('fromLocation'),
                        "toLocation": attr.get('toLocation'),
                        "usagetype": attr.get('usagetype'),
                        "operation": attr.get('operation')
                    }
                }
                
                batch.append(item)
                if len(summary_samples) < 100:
                    summary_samples.append(item)
                
                if len(batch) >= batch_size:
                    insert_pricing_batch(conn, 's3', batch)
                    count += len(batch)
                    batch = []
            
            if batch:
                insert_pricing_batch(conn, 's3', batch)
                count += len(batch)
                
        update_normalization_metadata(conn, 's3', raw_mtime)
        logger.info(f"S3: Normalization complete. inserted {count} rows.")
        
        summary_path = raw_path.parent.parent / 'normalized' / 's3' / 'summary.json'
        if not summary_path.parent.exists():
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            
        with open(summary_path, 'w') as f:
            json.dump({
                "count": count,
                "samples": summary_samples
            }, f, indent=2)
            
    except Exception as e:
        logger.error(f"S3: Normalization failed: {e}")
    finally:
        conn.close()
