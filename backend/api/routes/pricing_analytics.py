"""
Pricing Analytics Dashboard API
Provides endpoints for pricing analytics and monitoring
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any
from datetime import datetime, timedelta
from models.pricing_models import PricingRate, PricingVersion, PricingChange
from core.database import get_db
from services.pricing_monitoring import PricingFreshnessMonitor, PricingChangeAlert

router = APIRouter(prefix="/api/v1/pricing", tags=["pricing"])


@router.get("/analytics/overview")
async def get_pricing_overview(db: AsyncSession = Depends(get_db)):
    """Get pricing analytics overview"""
    
    # Get active version
    stmt = select(PricingVersion).where(PricingVersion.is_active == True)
    result = await db.execute(stmt)
    active_version = result.scalar_one_or_none()
    
    if not active_version:
        raise HTTPException(404, "No active pricing version")
    
    # Count total rates
    stmt = select(func.count(PricingRate.id)).where(
        PricingRate.version == active_version.version
    )
    result = await db.execute(stmt)
    total_rates = result.scalar()
    
    # Count services
    stmt = select(func.count(func.distinct(PricingRate.service))).where(
        PricingRate.version == active_version.version
    )
    result = await db.execute(stmt)
    total_services = result.scalar()
    
    # Count regions
    stmt = select(func.count(func.distinct(PricingRate.region))).where(
        PricingRate.version == active_version.version
    )
    result = await db.execute(stmt)
    total_regions = result.scalar()
    
    # Get freshness
    monitor = PricingFreshnessMonitor(db)
    freshness = await monitor.check_freshness()
    
    return {
        "version": active_version.version,
        "created_at": active_version.created_at.isoformat(),
        "source_type": active_version.source_type,
        "total_rates": total_rates,
        "total_services": total_services,
        "total_regions": total_regions,
        "freshness": freshness
    }


@router.get("/analytics/changes")
async def get_pricing_changes(
    version: str = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get recent pricing changes"""
    
    if not version:
        # Get latest version
        stmt = select(PricingVersion).order_by(PricingVersion.created_at.desc()).limit(1)
        result = await db.execute(stmt)
        latest_version = result.scalar_one_or_none()
        if latest_version:
            version = latest_version.version
    
    stmt = select(PricingChange).where(
        PricingChange.new_version == version
    ).order_by(PricingChange.change_percent.desc()).limit(limit)
    
    result = await db.execute(stmt)
    changes = result.scalars().all()
    
    return {
        "version": version,
        "total_changes": len(changes),
        "changes": [
            {
                "service": c.service,
                "region": c.region,
                "pricing_key": c.pricing_key,
                "old_rate": float(c.old_rate) if c.old_rate else None,
                "new_rate": float(c.new_rate),
                "change_percent": float(c.change_percent) if c.change_percent else None,
                "detected_at": c.detected_at.isoformat()
            }
            for c in changes
        ]
    }


@router.get("/analytics/service/{service_id}")
async def get_service_pricing_analytics(
    service_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get pricing analytics for specific service"""
    
    # Get active version
    stmt = select(PricingVersion).where(PricingVersion.is_active == True)
    result = await db.execute(stmt)
    active_version = result.scalar_one_or_none()
    
    if not active_version:
        raise HTTPException(404, "No active pricing version")
    
    # Get all rates for service
    stmt = select(PricingRate).where(
        PricingRate.version == active_version.version,
        PricingRate.service == service_id
    )
    result = await db.execute(stmt)
    rates = result.scalars().all()
    
    if not rates:
        raise HTTPException(404, f"No pricing data for service {service_id}")
    
    # Group by region
    by_region = {}
    for rate in rates:
        if rate.region not in by_region:
            by_region[rate.region] = []
        by_region[rate.region].append({
            "pricing_key": rate.pricing_key,
            "rate": float(rate.rate),
            "unit": rate.unit,
            "fetched_at": rate.fetched_at.isoformat()
        })
    
    return {
        "service": service_id,
        "version": active_version.version,
        "regions": by_region,
        "total_rates": len(rates)
    }


@router.get("/analytics/freshness")
async def get_pricing_freshness(db: AsyncSession = Depends(get_db)):
    """Get pricing data freshness status"""
    monitor = PricingFreshnessMonitor(db)
    return await monitor.check_freshness()


@router.get("/analytics/versions")
async def get_pricing_versions(db: AsyncSession = Depends(get_db)):
    """Get all pricing versions"""
    stmt = select(PricingVersion).order_by(PricingVersion.created_at.desc())
    result = await db.execute(stmt)
    versions = result.scalars().all()
    
    return {
        "versions": [
            {
                "version": v.version,
                "created_at": v.created_at.isoformat(),
                "source_type": v.source_type,
                "is_active": v.is_active
            }
            for v in versions
        ]
    }


@router.post("/analytics/activate-version/{version}")
async def activate_pricing_version(
    version: str,
    db: AsyncSession = Depends(get_db)
):
    """Activate a specific pricing version"""
    
    # Deactivate all versions
    stmt = select(PricingVersion)
    result = await db.execute(stmt)
    all_versions = result.scalars().all()
    
    for v in all_versions:
        v.is_active = (v.version == version)
    
    await db.commit()
    
    return {"message": f"Activated pricing version {version}"}
