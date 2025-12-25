"""
Analysis API endpoints.
"""
import logging
from pathlib import Path
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.database import get_async_session
from app.models.models import UploadJob, AnalysisResult, ResourceCost, PricingVersion
from app.terraform.parser import TerraformParser
from app.terraform.variables import VariableResolver
from app.terraform.modules import ModuleResolver
from app.terraform.normalizer import ResourceNormalizer
from app.engine.calculator import CostCalculator
from app.engine.aggregator import CostAggregator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/analyze/{job_id}")
async def analyze_terraform(
    job_id: UUID,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Analyze Terraform files and calculate costs.
    
    Args:
        job_id: Upload job ID
        db: Database session
    
    Returns:
        Analysis results
    """
    # Get upload job
    result = await db.execute(
        select(UploadJob).where(UploadJob.job_id == job_id)
    )
    upload_job = result.scalar_one_or_none()
    
    if not upload_job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if upload_job.status == "completed":
        raise HTTPException(status_code=400, detail="Job already completed")
    
    try:
        # Update status
        upload_job.status = "parsing"
        await db.commit()
        
        # Get active pricing version
        pricing_result = await db.execute(
            select(PricingVersion).where(PricingVersion.is_active == True)
        )
        pricing_version = pricing_result.scalar_one_or_none()
        
        if not pricing_version:
            raise HTTPException(
                status_code=500,
                detail="No active pricing version. Run pricing ingestion first."
            )
        
        # Parse Terraform
        logger.info(f"Parsing Terraform for job {job_id}")
        parser = TerraformParser()
        file_path = Path(upload_job.file_path)
        
        if file_path.is_file():
            parsed = parser.parse(file_path)
        else:
            parsed = parser.parse(file_path)
        
        # Resolve variables
        logger.info("Resolving variables")
        resolver = VariableResolver(
            parsed["variables"],
            parsed["locals"]
        )
        resolver.resolve_all()
        
        # Expand modules
        logger.info("Expanding modules")
        module_resolver = ModuleResolver(file_path.parent if file_path.is_file() else file_path)
        module_resources = module_resolver.expand_all_modules(parsed["modules"])
        
        # Combine resources
        all_resources = parsed["resources"] + module_resources
        
        # Normalize resources
        logger.info("Normalizing resources")
        normalizer = ResourceNormalizer()
        normalized_resources = normalizer.normalize_all(all_resources)
        
        # Update status
        upload_job.status = "calculating"
        await db.commit()
        
        # Calculate costs
        logger.info("Calculating costs")
        
        # Use sync session for calculator
        from app.db.database import get_sync_session
        with next(get_sync_session()) as sync_db:
            calculator = CostCalculator(sync_db, pricing_version)
            cost_results = calculator.calculate_all_costs(normalized_resources)
        
        # Aggregate results
        logger.info("Aggregating results")
        aggregator = CostAggregator(cost_results)
        aggregated = aggregator.aggregate_all()
        
        # Store results
        analysis_result = AnalysisResult(
            job_id=job_id,
            pricing_version_id=pricing_version.id,
            total_monthly_cost=Decimal(str(aggregated["total_monthly_cost"])),
            total_resources=aggregated["resource_counts"]["total"],
            total_supported_resources=aggregated["resource_counts"]["supported"],
            total_unsupported_resources=aggregated["resource_counts"]["unsupported"],
            breakdown_by_service=aggregated["breakdown_by_service"],
            breakdown_by_region=aggregated["breakdown_by_region"],
            warnings=aggregated["warnings"],
            errors=aggregated["errors"]
        )
        
        db.add(analysis_result)
        await db.flush()
        
        # Store individual resource costs
        for cost_result in cost_results:
            resource_cost = ResourceCost(
                analysis_id=analysis_result.id,
                resource_type=cost_result.get("resource_type", "Unknown"),
                resource_name=cost_result.get("resource_name", "Unknown"),
                service_code=cost_result.get("service_code", "Unknown"),
                region_code=cost_result.get("region"),
                monthly_cost=Decimal(str(cost_result.get("monthly_cost", 0))),
                attributes=cost_result.get("pricing_details", {}),
                pricing_details=cost_result.get("pricing_details", {}),
                warnings=cost_result.get("warnings")
            )
            db.add(resource_cost)
        
        # Update job status
        upload_job.status = "completed"
        await db.commit()
        
        logger.info(f"Analysis completed for job {job_id}")
        
        return {
            "job_id": str(job_id),
            "status": "completed",
            "total_monthly_cost": float(aggregated["total_monthly_cost"]),
            "total_resources": aggregated["resource_counts"]["total"],
            "supported_resources": aggregated["resource_counts"]["supported"],
            "unsupported_resources": aggregated["resource_counts"]["unsupported"]
        }
    
    except Exception as e:
        logger.error(f"Analysis failed for job {job_id}: {e}", exc_info=True)
        
        upload_job.status = "failed"
        upload_job.error_message = str(e)
        await db.commit()
        
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
