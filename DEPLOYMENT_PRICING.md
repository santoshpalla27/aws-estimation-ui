# Hybrid Pricing Architecture - Deployment Guide

## Prerequisites

- PostgreSQL 15+
- Redis 7+
- Python 3.11+
- AWS credentials (for pricing ingestion)

## Step 1: Database Migration

```bash
cd backend
alembic upgrade head
```

This creates:
- `pricing_versions` table
- `pricing_rates` table
- `pricing_metadata` table
- `pricing_changes` table

## Step 2: Seed Initial Pricing Data

```bash
# Update DATABASE_URL in scripts/seed_pricing_data.py
python scripts/seed_pricing_data.py
```

This migrates pricing from YAML files to PostgreSQL.

## Step 3: Verify Pricing Data

```sql
-- Check pricing version
SELECT * FROM pricing_versions;

-- Check pricing rates
SELECT service, region, COUNT(*) 
FROM pricing_rates 
WHERE version = '2024-12'
GROUP BY service, region;

-- Sample rates
SELECT * FROM pricing_rates 
WHERE service = 'AWSLambda' AND region = 'us-east-1'
LIMIT 10;
```

## Step 4: Configure Redis

Ensure Redis is running and accessible:
```bash
redis-cli ping
# Should return: PONG
```

## Step 5: Deploy Application

```bash
docker compose down
docker compose up -d --build
```

## Step 6: Test Pricing Resolution

```bash
# Test API endpoint
curl -X POST http://localhost:8000/api/v1/estimates \
  -H "Content-Type: application/json" \
  -d '{
    "services": [{
      "id": "lambda-1",
      "service_type": "AWSLambda",
      "region": "us-east-1",
      "config": {
        "memory_mb": 1024,
        "avg_duration_ms": 1000,
        "invocations_per_month": 1000000
      }
    }]
  }'
```

Expected response should include:
```json
{
  "pricing_metadata": {
    "version": "2024-12",
    "source": "manual_seed",
    "fetched_at": "2024-12-01T00:00:00Z"
  }
}
```

## Step 7: Setup Pricing Ingestion (Optional)

### Manual Run
```bash
# Update AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

# Run pricing update
python scripts/run_pricing_update.py
```

### Scheduled Run (Cron)
```bash
# Add to crontab
0 0 * * * cd /path/to/backend && python scripts/run_pricing_update.py
```

### Scheduled Run (Airflow)
```python
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

dag = DAG(
    'pricing_ingestion',
    schedule_interval='0 0 * * *',  # Daily at midnight
    start_date=datetime(2024, 12, 1),
    catchup=False
)

run_pricing_update = BashOperator(
    task_id='run_pricing_update',
    bash_command='cd /path/to/backend && python scripts/run_pricing_update.py',
    dag=dag
)
```

## Troubleshooting

### Issue: Pricing key not found
```
PricingKeyNotFoundError: Pricing key 'compute.gb_second' not found
```

**Solution:** Run seeding script or check if pricing data exists in database.

### Issue: No active pricing version
```
PricingVersionNotFoundError: No active pricing version found
```

**Solution:**
```sql
UPDATE pricing_versions SET is_active = true WHERE version = '2024-12';
```

### Issue: Redis connection failed
```
pricing_cache_error
```

**Solution:** Verify Redis is running and connection string is correct.

## Monitoring

### Check Pricing Freshness
```sql
SELECT 
    service,
    region,
    MAX(fetched_at) as last_updated,
    EXTRACT(DAY FROM NOW() - MAX(fetched_at)) as age_days
FROM pricing_rates
WHERE version = (SELECT version FROM pricing_versions WHERE is_active = true)
GROUP BY service, region
ORDER BY age_days DESC;
```

### Check Pricing Changes
```sql
SELECT 
    service,
    region,
    pricing_key,
    old_rate,
    new_rate,
    change_percent,
    detected_at
FROM pricing_changes
WHERE new_version = '2024-12'
ORDER BY ABS(change_percent) DESC
LIMIT 20;
```

## Rollback

If issues occur, rollback to previous version:

```sql
-- Deactivate current version
UPDATE pricing_versions SET is_active = false WHERE version = '2024-12';

-- Activate previous version
UPDATE pricing_versions SET is_active = true WHERE version = '2024-11';
```

## Performance Tuning

### Redis Cache Hit Rate
```bash
redis-cli info stats | grep keyspace_hits
redis-cli info stats | grep keyspace_misses
```

Target: >95% cache hit rate

### Database Query Performance
```sql
EXPLAIN ANALYZE 
SELECT * FROM pricing_rates 
WHERE version = '2024-12' 
  AND service = 'AWSLambda' 
  AND region = 'us-east-1' 
  AND pricing_key = 'compute.gb_second';
```

Should use index: `idx_pricing_lookup`
