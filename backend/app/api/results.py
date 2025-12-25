"""
Results API endpoints.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import get_async_session
from app.models.models import UploadJob, AnalysisResult, ResourceCost

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/results/{job_id}")
async def get_results(
    job_id: UUID,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get analysis results for a job.
    
    Args:
        job_id: Upload job ID
        db: Database session
    
    Returns:
        Complete analysis results
    """
    # Get upload job
    result = await db.execute(
        select(UploadJob).where(UploadJob.job_id == job_id)
    )
    upload_job = result.scalar_one_or_none()
    
    if not upload_job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check status
    if upload_job.status == "pending":
        return {
            "job_id": str(job_id),
            "status": "pending",
            "message": "Job not started. Call /api/analyze to start."
        }
    
    if upload_job.status in ["parsing", "calculating"]:
        return {
            "job_id": str(job_id),
            "status": upload_job.status,
            "message": f"Job in progress: {upload_job.status}"
        }
    
    if upload_job.status == "failed":
        return {
            "job_id": str(job_id),
            "status": "failed",
            "error": upload_job.error_message
        }
    
    # Get analysis results
    analysis_result_query = await db.execute(
        select(AnalysisResult)
        .where(AnalysisResult.job_id == job_id)
        .options(selectinload(AnalysisResult.resource_costs))
    )
    analysis_result = analysis_result_query.scalar_one_or_none()
    
    if not analysis_result:
        raise HTTPException(status_code=404, detail="Results not found")
    
    # Format resource costs
    resources = []
    for resource_cost in analysis_result.resource_costs:
        resources.append({
            "name": resource_cost.resource_name,
            "type": resource_cost.resource_type,
            "service": resource_cost.service_code,
            "region": resource_cost.region_code,
            "monthly_cost": float(resource_cost.monthly_cost),
            "pricing_details": resource_cost.pricing_details,
            "warnings": resource_cost.warnings or []
        })
    
    return {
        "job_id": str(job_id),
        "status": "completed",
        "total_monthly_cost": float(analysis_result.total_monthly_cost),
        "total_resources": analysis_result.total_resources,
        "supported_resources": analysis_result.total_supported_resources,
        "unsupported_resources": analysis_result.total_unsupported_resources,
        "breakdown_by_service": analysis_result.breakdown_by_service,
        "breakdown_by_region": analysis_result.breakdown_by_region,
        "resources": resources,
        "warnings": analysis_result.warnings or [],
        "errors": analysis_result.errors or [],
        "pricing_version": analysis_result.pricing_version_id
    }


@router.get("/status/{job_id}")
async def get_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get job status.
    
    Args:
        job_id: Upload job ID
        db: Database session
    
    Returns:
        Job status
    """
    result = await db.execute(
        select(UploadJob).where(UploadJob.job_id == job_id)
    )
    upload_job = result.scalar_one_or_none()
    
    if not upload_job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": str(job_id),
        "status": upload_job.status,
        "created_at": upload_job.created_at.isoformat(),
        "updated_at": upload_job.updated_at.isoformat(),
        "error": upload_job.error_message
    }
