"""
Scheduled Pricing Ingestion Job
Runs daily to update pricing from AWS Pricing API
Can be triggered manually or via cron/Airflow
"""

import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from services.pricing_ingestion import PricingIngestionPipeline
from core.config import settings
import structlog

logger = structlog.get_logger()


async def run_daily_pricing_update():
    """Daily pricing update job"""
    logger.info("starting_daily_pricing_update")
    
    pipeline = PricingIngestionPipeline(settings.DATABASE_URL)
    
    # Services to update
    services = [
        "AWSLambda",
        "AmazonEC2",
        "AmazonRDS",
        "AmazonS3",
        "AmazonDynamoDB",
        "AmazonVPC",
        "ApplicationLoadBalancer",
        "AmazonCloudWatch"
    ]
    
    # Regions to fetch
    regions = [
        "us-east-1",
        "us-west-2",
        "eu-west-1",
        "ap-south-1",
        "ap-southeast-1"
    ]
    
    try:
        await pipeline.run(services, regions)
        logger.info("daily_pricing_update_complete")
    except Exception as e:
        logger.error("daily_pricing_update_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_daily_pricing_update())
