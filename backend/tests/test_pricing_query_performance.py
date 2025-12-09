import os
import sqlite3
import json
import time
import pytest
import shutil
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.core.pricing_db import create_pricing_table, create_index, insert_pricing_batch
from backend.services.ec2.pricing_index import PricingIndex as EC2PricingIndex

TEST_DB_PATH = Path("test_perf_pricing.db")

@pytest.fixture(scope="module")
def perf_db():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
        
    conn = sqlite3.connect(str(TEST_DB_PATH))
    # Enable WAL
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    
    create_pricing_table(conn, 'ec2')
    # Create Indexes
    create_index(conn, 'ec2', ['instanceType', 'vcpu', 'memory', 'operatingSystem'])
    
    # Insert 50k rows
    print("\nGenerating 50k rows...")
    batch = []
    start_gen = time.time()
    for i in range(50000):
        item = {
            "sku": f"SKU_{i}",
            "price": 0.1 + (i * 0.0001),
            "location": "US East (N. Virginia)",
            "attributes": {
                "instanceType": f"t3.{'micro' if i % 2 == 0 else 'small'}",
                "vcpu": "2" if i % 2 == 0 else "4",
                "memory": "1 GiB" if i % 2 == 0 else "2 GiB",
                "operatingSystem": "Linux" if i % 3 == 0 else "Windows",
                # Add some random data to bloat JSON slightly
                "extra": "x" * 50
            }
        }
        batch.append(item)
        if len(batch) >= 5000:
            insert_pricing_batch(conn, 'ec2', batch)
            batch = []
    
    if batch:
        insert_pricing_batch(conn, 'ec2', batch)
    
    conn.commit()
    conn.close()
    
    print(f"Data generation took {time.time() - start_gen:.2f}s")
    
    # Monkeypatch the DB path for the index
    # We do this by mocking _get_db_path or just passing it if we allowed injection.
    # BasePricingIndex _get_db_path uses constants, so we patch module or set explicitly.
    # But wait, BasePricingIndex is instantiated. We can check if we can subclass for test.
    
    yield TEST_DB_PATH
    
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

class TestPricingIndex(EC2PricingIndex):
    def _get_db_path(self):
        return str(TEST_DB_PATH)

def test_query_performance(perf_db):
    index = TestPricingIndex()
    
    # 1. Warmup
    index.query({"instanceType": "t3.micro"})
    
    # 2. Indexed Query (attributes.instanceType)
    start = time.time()
    items, total = index.query({"instanceType": "t3.micro"}, page=1, per_page=50)
    duration = (time.time() - start) * 1000
    print(f"\nIndexed Query (instanceType='t3.micro'): {duration:.2f}ms, Total: {total}")
    assert duration < 200, "Indexed query exceeded 200ms"
    assert total > 0
    assert len(items) == 50
    
    # 3. Main Column Query (location)
    start = time.time()
    items, total = index.query({"location": "US East (N. Virginia)"}, page=1, per_page=50)
    duration = (time.time() - start) * 1000
    print(f"Main Column Query (location): {duration:.2f}ms, Total: {total}")
    assert duration < 200, "Main column query exceeded 200ms"
    
    # 4. Complex Filter
    start = time.time()
    items, total = index.query({
        "instanceType": "t3.small", 
        "operatingSystem": "Windows",
        "vcpu": "4"
    }, page=1, per_page=50)
    duration = (time.time() - start) * 1000
    print(f"Complex Filter: {duration:.2f}ms, Total: {total}")
    assert duration < 200
    
    # 5. Pagination
    items_p2, total_p2 = index.query({"instanceType": "t3.micro"}, page=2, per_page=50)
    assert len(items_p2) == 50
    assert items_p2[0]['sku'] != items[0]['sku'] # Should be different page

if __name__ == "__main__":
    # verification manual run
    pytest.main([__file__])
