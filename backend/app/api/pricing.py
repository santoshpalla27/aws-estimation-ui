"""
Pricing API endpoints.
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_async_session
from app.models.models import PricingVersion, PricingService, PricingDimension
from app.pricing.scheduler import pricing_scheduler

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/pricing/versions")
async def get_pricing_versions(
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get all pricing versions.
    
    Returns:
        List of pricing versions
    """
    result = await db.execute(
        select(PricingVersion).order_by(PricingVersion.created_at.desc())
    )
    versions = result.scalars().all()
    
    return {
        "versions": [
            {
                "id": v.id,
                "version": v.version,
                "is_active": v.is_active,
                "created_at": v.created_at.isoformat(),
                "source": v.source
            }
            for v in versions
        ]
    }


@router.get("/pricing/services")
async def get_pricing_services(
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get supported services.
    
    Returns:
        List of supported services
    """
    result = await db.execute(
        select(PricingService).order_by(PricingService.service_name)
    )
    services = result.scalars().all()
    
    return {
        "services": [
            {
                "code": s.service_code,
                "name": s.service_name,
                "description": s.description
            }
            for s in services
        ]
    }


@router.get("/pricing/stats")
async def get_pricing_stats(
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get pricing statistics.
    
    Returns:
        Pricing data statistics
    """
    # Get active version
    active_version_result = await db.execute(
        select(PricingVersion).where(PricingVersion.is_active == True)
    )
    active_version = active_version_result.scalar_one_or_none()
    
    if not active_version:
        return {
            "active_version": None,
            "total_dimensions": 0,
            "message": "No active pricing version. Run pricing ingestion."
        }
    
    # Count dimensions
    count_result = await db.execute(
        select(func.count(PricingDimension.id))
        .where(PricingDimension.version_id == active_version.id)
    )
    total_dimensions = count_result.scalar()
    
    return {
        "active_version": active_version.version,
        "version_created": active_version.created_at.isoformat(),
        "total_dimensions": total_dimensions,
        "scheduler_running": pricing_scheduler.is_running
    }


@router.post("/pricing/update")
async def trigger_pricing_update():
    """
    Manually trigger pricing update.
    
    Returns:
        Update status
    """
    try:
        pricing_scheduler.run_now()
        return {
            "status": "started",
            "message": "Pricing update started. This may take 30-60 minutes."
        }
    except Exception as e:
        logger.error(f"Failed to trigger pricing update: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
