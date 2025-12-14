"""
Database Initialization and Migration Script
Runs all initialization tasks: migration, seeding, and formula migration
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from alembic.config import Config
from alembic import command

logger = structlog.get_logger()


async def run_alembic_upgrade():
    """Run Alembic database migrations"""
    logger.info("running_alembic_migrations")
    
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("alembic_migrations_complete")
        return True
    except Exception as e:
        logger.error("alembic_migration_failed", error=str(e))
        return False


async def run_pricing_seed():
    """Seed pricing data from YAML files"""
    logger.info("seeding_pricing_data")
    
    try:
        from scripts.seed_pricing_data import seed_pricing_data
        await seed_pricing_data()
        logger.info("pricing_seed_complete")
        return True
    except Exception as e:
        logger.error("pricing_seed_failed", error=str(e))
        return False


async def run_formula_migration():
    """Migrate formulas to use pricing.* references"""
    logger.info("migrating_formulas")
    
    try:
        from scripts.migrate_formulas_to_pricing import FormulaPricingMigrator
        
        plugins_dir = Path("plugins")
        migrator = FormulaPricingMigrator(plugins_dir)
        stats = migrator.migrate_all_services()
        
        logger.info(
            "formula_migration_complete",
            total=stats['total_services'],
            migrated=stats['migrated'],
            skipped=stats['skipped'],
            errors=stats['errors']
        )
        return stats['errors'] == 0
    except Exception as e:
        logger.error("formula_migration_failed", error=str(e))
        return False


async def main():
    """Run all initialization tasks"""
    logger.info("starting_database_initialization")
    
    # Wait for database to be ready
    logger.info("waiting_for_database")
    await asyncio.sleep(5)
    
    # Step 1: Run Alembic migrations
    if not await run_alembic_upgrade():
        logger.error("initialization_failed_at_migration")
        sys.exit(1)
    
    # Step 2: Seed pricing data
    if not await run_pricing_seed():
        logger.error("initialization_failed_at_seeding")
        sys.exit(1)
    
    # Step 3: Migrate formulas
    if not await run_formula_migration():
        logger.error("initialization_failed_at_formula_migration")
        sys.exit(1)
    
    logger.info("database_initialization_complete")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
