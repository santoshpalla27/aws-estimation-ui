"""
Background pricing scheduler.
Runs pricing ingestion jobs on a schedule.
"""
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.db.database import get_sync_session
from app.pricing.ingestion import download_pricing_data
from app.pricing.normalization import normalize_pricing_data

logger = logging.getLogger(__name__)


class PricingScheduler:
    """Background scheduler for pricing updates."""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
    
    def run_pricing_update(self):
        """
        Run pricing update job.
        Downloads and normalizes pricing data.
        """
        logger.info("Starting pricing update job")
        
        try:
            # Download pricing data
            logger.info("Downloading pricing data from AWS")
            pricing_files = download_pricing_data()
            
            if not pricing_files:
                logger.warning("No pricing files downloaded")
                return
            
            logger.info(f"Downloaded {len(pricing_files)} pricing files")
            
            # Normalize into database
            logger.info("Normalizing pricing data")
            with next(get_sync_session()) as db:
                version = normalize_pricing_data(db, pricing_files)
                logger.info(f"Created pricing version: {version.version}")
            
            logger.info("Pricing update completed successfully")
        
        except Exception as e:
            logger.error(f"Pricing update failed: {e}", exc_info=True)
    
    def start(self):
        """Start the scheduler."""
        if not settings.pricing_update_enabled:
            logger.info("Pricing updates disabled in configuration")
            return
        
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        # Parse cron schedule
        cron_parts = settings.pricing_update_schedule.split()
        if len(cron_parts) != 5:
            logger.error(f"Invalid cron schedule: {settings.pricing_update_schedule}")
            return
        
        minute, hour, day, month, day_of_week = cron_parts
        
        # Add job to scheduler
        self.scheduler.add_job(
            self.run_pricing_update,
            trigger=CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            ),
            id="pricing_update",
            name="Pricing Update Job",
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        
        logger.info(f"Pricing scheduler started with schedule: {settings.pricing_update_schedule}")
    
    def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            return
        
        self.scheduler.shutdown()
        self.is_running = False
        logger.info("Pricing scheduler stopped")
    
    def run_now(self):
        """Run pricing update immediately (for manual triggers)."""
        logger.info("Running pricing update manually")
        self.run_pricing_update()


# Global scheduler instance
pricing_scheduler = PricingScheduler()
