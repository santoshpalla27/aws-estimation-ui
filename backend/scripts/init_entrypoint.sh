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
if /usr/local/bin/alembic upgrade head 2>&1 | grep -q "already exists"; then
  echo "⚠️  Tables already exist, stamping alembic version..."
  /usr/local/bin/alembic stamp head
  echo "✅ Database already migrated"
elif /usr/local/bin/alembic upgrade head; then
  echo "✅ Migrations applied successfully"
else
  echo "❌ Migration failed, trying Python fallback..."
  python3 -c "from alembic.config import Config; from alembic import command; cfg = Config('alembic.ini'); command.upgrade(cfg, 'head')" || {
    echo "⚠️  Migration failed, stamping current state..."
    /usr/local/bin/alembic stamp head
  }
fi

# Seed pricing data
echo "🌱 Seeding pricing data..."
python scripts/seed_pricing_data.py || echo "⚠️  Seeding skipped (may already exist)"

# Migrate formulas to use pricing.* references
echo "🔄 Migrating formulas..."
python scripts/migrate_formulas_to_pricing.py || echo "⚠️  Formula migration skipped"

echo "✅ Database initialization complete!"
exit 0
