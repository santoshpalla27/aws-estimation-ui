# Database Initialization Container

## Overview

The `db-init` container is a one-time initialization service that automatically sets up the database when you deploy the application. It runs before the backend starts and handles all setup tasks.

## What It Does

1. **Waits for PostgreSQL** - Ensures database is ready
2. **Runs Alembic Migrations** - Creates all tables and indexes
3. **Seeds Pricing Data** - Loads pricing from YAML files into PostgreSQL
4. **Migrates Formulas** - Updates formulas to use `pricing.*` references

## How It Works

### Docker Compose Configuration

```yaml
db-init:
  build:
    context: ./backend
    dockerfile: Dockerfile
  depends_on:
    postgres:
      condition: service_healthy
  command: /bin/bash /app/backend/scripts/init_entrypoint.sh
  restart: "no"  # Run once and exit

backend:
  depends_on:
    db-init:
      condition: service_completed_successfully  # Wait for init to finish
```

### Execution Flow

```
1. PostgreSQL starts → healthcheck passes
2. db-init starts → runs init_entrypoint.sh
   ├─ Wait for PostgreSQL readiness
   ├─ Run: alembic upgrade head
   ├─ Run: python scripts/seed_pricing_data.py
   ├─ Run: python scripts/migrate_formulas_to_pricing.py
   └─ Exit with code 0
3. Backend starts → database is ready
```

## Benefits

### Before (Manual Setup)
```bash
# SSH into server
ssh user@server

# Run migrations manually
cd /root/aws-estimation-ui/backend
alembic upgrade head

# Seed data manually
python scripts/seed_pricing_data.py

# Migrate formulas manually
python scripts/migrate_formulas_to_pricing.py

# Restart services
docker compose restart backend
```

### After (Automated)
```bash
# Just deploy
docker compose up -d

# Everything happens automatically! ✨
```

## Deployment

### First Time Deployment
```bash
cd /root/aws-estimation-ui
git pull
docker compose up -d
```

The init container will:
- ✅ Create all database tables
- ✅ Load pricing data
- ✅ Migrate formulas
- ✅ Exit successfully
- ✅ Backend starts with ready database

### Subsequent Deployments
```bash
docker compose up -d
```

The init container will:
- ✅ Run migrations (idempotent - safe to run multiple times)
- ✅ Skip seeding if data exists
- ✅ Skip formula migration if already done
- ✅ Exit successfully

## Logs

### View Init Container Logs
```bash
docker compose logs db-init
```

**Expected Output:**
```
🚀 Starting database initialization...
⏳ Waiting for PostgreSQL...
✅ PostgreSQL is ready!
📦 Running database migrations...
INFO  [alembic.runtime.migration] Running upgrade -> create_pricing_tables
🌱 Seeding pricing data...
INFO  [seed_pricing_data] created_pricing_version version=2024-12
INFO  [seed_pricing_data] seeding_complete version=2024-12 total_rates=1250
🔄 Migrating formulas...
INFO  [formula_migrator] service_migrated service=AWSLambda
✅ Database initialization complete!
```

### Check Init Status
```bash
docker compose ps db-init
```

**Expected:**
```
NAME                STATE               
db-init             Exited (0)  # Success!
```

## Troubleshooting

### Init Container Failed

**Check logs:**
```bash
docker compose logs db-init
```

**Common Issues:**

1. **PostgreSQL not ready**
   - Wait longer for PostgreSQL healthcheck
   - Check: `docker compose logs postgres`

2. **Migration failed**
   - Check Alembic configuration
   - Verify DATABASE_URL is correct

3. **Seeding failed**
   - Check pricing_data.yaml files exist
   - Verify file permissions

**Retry:**
```bash
docker compose rm -f db-init
docker compose up -d db-init
```

### Re-run Initialization

If you need to re-run initialization:

```bash
# Remove init container
docker compose rm -f db-init

# Re-run
docker compose up -d db-init

# Check logs
docker compose logs -f db-init
```

## Files

- `backend/scripts/init_entrypoint.sh` - Bash script that runs all tasks
- `backend/scripts/init_database.py` - Python script (alternative)
- `backend/scripts/seed_pricing_data.py` - Pricing data seeding
- `backend/scripts/migrate_formulas_to_pricing.py` - Formula migration

## Environment Variables

The init container uses the same environment variables as the backend:

- `DATABASE_URL` - PostgreSQL connection string
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password

## Production Considerations

### Idempotency
All scripts are idempotent (safe to run multiple times):
- Migrations: Alembic tracks applied migrations
- Seeding: Checks if data exists before inserting
- Formula migration: Skips already migrated formulas

### Zero Downtime
The init container runs before the backend starts, ensuring:
- Database is ready before accepting requests
- No race conditions
- Clean startup

### Rollback
If initialization fails:
- Container exits with error code
- Backend won't start (depends_on condition)
- Safe to fix and retry

## Summary

The `db-init` container provides:
- ✅ Automated database setup
- ✅ Zero manual steps
- ✅ Consistent deployments
- ✅ Idempotent operations
- ✅ Clear logging
- ✅ Safe failure handling

**Just run `docker compose up -d` and everything works!** 🎉
