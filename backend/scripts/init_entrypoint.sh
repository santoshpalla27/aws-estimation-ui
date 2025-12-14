#!/bin/bash
# Database Initialization Entrypoint
# Runs all initialization tasks and exits

set -e

echo "🚀 Starting database initialization..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
until pg_isready -h postgres -p 5432 -U ${POSTGRES_USER:-costuser}; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "✅ PostgreSQL is ready!"

# Change to app directory (where backend code is)
cd /app

# Run Alembic migrations using the CLI
echo "📦 Running database migrations..."
/usr/local/bin/alembic upgrade head || python3 -c "from alembic.config import Config; from alembic import command; cfg = Config('alembic.ini'); command.upgrade(cfg, 'head')"

# Seed pricing data
echo "🌱 Seeding pricing data..."
python scripts/seed_pricing_data.py

# Migrate formulas to use pricing.* references
echo "🔄 Migrating formulas..."
python scripts/migrate_formulas_to_pricing.py

echo "✅ Database initialization complete!"
exit 0
