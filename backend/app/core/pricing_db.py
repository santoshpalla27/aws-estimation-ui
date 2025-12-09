import sqlite3
import logging
import json
from datetime import datetime
from backend.app.core.database import get_db_connection

logger = logging.getLogger(__name__)

class PricingDB:
    def __init__(self, db_path):
        self.conn = get_db_connection(db_path)

    def initialize_service_table(self, service_name: str, indexed_fields: list):
        create_pricing_table(self.conn, service_name)
        create_index(self.conn, service_name, indexed_fields)

    def insert_records(self, service_name: str, items: list, indexed_fields: list = None):
        insert_pricing_batch(self.conn, service_name, items)

    def close(self):
        self.conn.close()

def create_pricing_table(conn: sqlite3.Connection, service_name: str):
    """Creates the pricing table for a specific service."""
    table_name = f"pricing_{service_name}"
    
    # 1. Create table
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            sku TEXT PRIMARY KEY,
            price REAL,
            location TEXT,
            attributes TEXT
        )
    """)
    
    # 2. Indexes for common lookups
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{service_name}_location ON {table_name}(location)")
    
    # 3. Create metadata table if not exists (shared for all services)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS normalization_meta (
            service TEXT PRIMARY KEY,
            last_normalized_at DATETIME,
            source_file_mtime REAL
        )
    """)
    
    conn.commit()

def should_skip_normalization(conn: sqlite3.Connection, service_name: str, raw_file_mtime: float) -> bool:
    """Checks if normalization can be skipped based on file modification time."""
    cursor = conn.execute(
        "SELECT source_file_mtime FROM normalization_meta WHERE service = ?", 
        (service_name,)
    )
    row = cursor.fetchone()
    if row and row[0] == raw_file_mtime:
        return True
    return False

def update_normalization_metadata(conn: sqlite3.Connection, service_name: str, raw_file_mtime: float):
    """Updates metadata after successful normalization."""
    conn.execute("""
        INSERT OR REPLACE INTO normalization_meta (service, last_normalized_at, source_file_mtime)
        VALUES (?, ?, ?)
    """, (service_name, datetime.utcnow().isoformat(), raw_file_mtime))
    conn.commit()

def insert_pricing_batch(conn: sqlite3.Connection, service_name: str, items: list):
    """
    Inserts a batch of pricing items.
    Items should be dicts with: sku, price, location, attributes (dict)
    """
    if not items:
        return
        
    table_name = f"pricing_{service_name}"
    
    data = []
    for item in items:
        # separate standard columns from extra attributes
        sku = item.get('sku')
        price = item.get('price')
        location = item.get('location')
        
        # Everything else goes into attributes JSON
        attributes_json = json.dumps(item.get('attributes', {}))
        
        data.append((sku, price, location, attributes_json))
        
    try:
        conn.executemany(f"""
            INSERT OR REPLACE INTO {table_name} (sku, price, location, attributes)
            VALUES (?, ?, ?, ?)
        """, data)
        conn.commit()
    except Exception as e:
        logger.error(f"Batch insert failed: {e}")
        conn.rollback()
        raise

def create_index(conn: sqlite3.Connection, service_name: str, fields: list):
    """
    Creates indexes for the specified fields.
    Supports indexing JSON attributes via json_extract.
    Fields should be a list of strings, e.g. ['location', 'attributes.instanceType'].
    """
    table_name = f"pricing_{service_name}"
    
    for field in fields:
        if '.' in field and not field.startswith('json_extract'):
            pass
            
        index_name = f"idx_{service_name}_{field.replace('.', '_')}"
        
        if field in ['sku', 'price', 'location']:
            # Standard column index
            sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({field})"
        else:
            # JSON index
            sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}(json_extract(attributes, '$.{field}'))"
            
        try:
            conn.execute(sql)
        except Exception as e:
            logger.warning(f"Failed to create index {index_name}: {e}")
    
    conn.commit()
