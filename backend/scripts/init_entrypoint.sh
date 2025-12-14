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

# Change to backend directory
cd /app/backend

# Run Alembic migrations
echo "📦 Running database migrations..."
alembic upgrade head

# Seed pricing data
echo "🌱 Seeding pricing data..."
python scripts/seed_pricing_data.py

# Migrate formulas to use pricing.* references
echo "🔄 Migrating formulas..."
python scripts/migrate_formulas_to_pricing.py

echo "✅ Database initialization complete!"
exit 0
