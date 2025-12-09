import sqlite3
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def get_db_connection(db_path: Path) -> sqlite3.Connection:
    """
    Returns a configured sqlite3 connection.
    Enables WAL mode and sets appropriate timeouts.
    """
    # Ensure directory exists
    db_path = Path(db_path)
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    # Enable Write-Ahead Logging for concurrency and performance
    conn.execute("PRAGMA journal_mode=WAL")
    
    # Synchronous NORMAL is safe for WAL and faster
    conn.execute("PRAGMA synchronous=NORMAL")
    
    # Increase cache size (neg value = kb, pos value = pages) -> -64000 = 64MB
    conn.execute("PRAGMA cache_size=-64000")
    
    return conn
