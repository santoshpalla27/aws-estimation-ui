import pytest
import sqlite3
import json
from pathlib import Path
from backend.app.core.database import PricingDB

@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test_pricing.db"
    return PricingDB(db_path)

def test_initialize_and_insert(db):
    service = "test_service"
    fields = ["region", "instance_type"]
    
    db.initialize_service_table(service, fields)
    
    records = [
        {"region": "us-east-1", "instance_type": "t3.micro", "price": 0.01},
        {"region": "us-west-1", "instance_type": "t3.micro", "price": 0.02},
        {"region": "us-east-1", "instance_type": "m5.large", "price": 0.10}
    ]
    
    db.insert_records(service, records, fields)
    
    # Verify directly via sqlite
    conn = sqlite3.connect(db.db_path)
    cursor = conn.execute(f"SELECT count(*) FROM pricing_{service}")
    assert cursor.fetchone()[0] == 3
    conn.close()

def test_query_and_find(db):
    service = "test_service"
    fields = ["region", "instance_type"]
    db.initialize_service_table(service, fields)
    
    records = [
        {"region": "us-east-1", "instance_type": "t3.micro", "data": "A"},
        {"region": "us-east-1", "instance_type": "t3.small", "data": "B"},
        {"region": "us-west-1", "instance_type": "t3.micro", "data": "C"}
    ]
    db.insert_records(service, records, fields)
    
    # Find One
    res = db.find_one(service, {"region": "us-east-1", "instance_type": "t3.micro"})
    assert res['data'] == "A"
    
    # Query Pagination
    res = db.query(service, {"region": "us-east-1"}, page=1, per_page=1)
    assert res['total'] == 2
    assert len(res['items']) == 1
    assert res['items'][0]['data'] == "A"  # Order insertion dependent usually, but sqlite handles.

def test_performance(db, benchmark=None):
    # Optional benchmark if pytest-benchmark installed, otherwise strict time check
    service = "perf_test"
    fields = ["col_a", "col_b"]
    db.initialize_service_table(service, fields)
    
    # Insert 10k rows
    records = [{"col_a": f"val_{i%100}", "col_b": f"sub_{i%10}", "id": i} for i in range(10000)]
    db.insert_records(service, records, fields)
    
    import time
    start = time.time()
    db.query(service, {"col_a": "val_50"}, page=1, per_page=10)
    end = time.time()
    
    assert (end - start) < 0.2 # 200ms expectation
