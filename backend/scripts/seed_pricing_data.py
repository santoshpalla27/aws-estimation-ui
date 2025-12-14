"""
Pricing Data Seeding Script
Seeds initial pricing data from pricing_data.yaml files into database
Run once after database migration
"""

import asyncio
import yaml
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models.pricing_models import PricingVersion, PricingRate, PricingMetadata
import structlog

logger = structlog.get_logger()

# Database URL - update as needed
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/aws_cost_estimation"

async def seed_pricing_data():
    """Seed pricing data from YAML files into database"""
    
    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    plugins_dir = Path("backend/plugins")
    version = "2024-12"
    
    async with async_session() as session:
        # Create pricing version
        pricing_version = PricingVersion(
            version=version,
            created_at=datetime.utcnow(),
            source_type="manual_seed",
            is_active=True,
            metadata={"source": "pricing_data.yaml files"}
        )
        
        # Check if version exists
        stmt = select(PricingVersion).where(PricingVersion.version == version)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if not existing:
            session.add(pricing_version)
            logger.info("created_pricing_version", version=version)
        else:
            logger.info("pricing_version_exists", version=version)
        
        # Process each service
        total_rates = 0
        for service_dir in plugins_dir.iterdir():
            if not service_dir.is_dir():
                continue
            
            pricing_file = service_dir / "pricing_data.yaml"
            if not pricing_file.exists():
                logger.warning("no_pricing_file", service=service_dir.name)
                continue
            
            # Load pricing data
            with open(pricing_file, 'r') as f:
                pricing_data = yaml.safe_load(f)
            
            service_id = pricing_data['service']
            regions = pricing_data.get('regions', {})
            
            # Insert rates for each region
            for region, rates in regions.items():
                # Extract free_tier and multipliers
                free_tier = rates.pop('free_tier', None)
                multipliers = pricing_data.get('architecture_multipliers') or pricing_data.get('tier_multipliers')
                
                # Insert pricing metadata
                metadata = PricingMetadata(
                    version=version,
                    service=service_id,
                    region=region,
                    free_tier=free_tier,
                    multipliers=multipliers,
                    source_url=pricing_data.get('source')
                )
                session.add(metadata)
                
                # Insert each rate
                for key, value in rates.items():
                    if isinstance(value, dict):
                        # Nested structure (e.g., free_tier)
                        continue
                    
                    rate = PricingRate(
                        version=version,
                        service=service_id,
                        region=region,
                        pricing_key=key,
                        rate=Decimal(str(value)),
                        fetched_at=datetime.utcnow()
                    )
                    session.add(rate)
                    total_rates += 1
            
            logger.info("processed_service", service=service_id, regions=len(regions))
        
        # Commit all changes
        await session.commit()
        logger.info("seeding_complete", version=version, total_rates=total_rates)
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_pricing_data())
