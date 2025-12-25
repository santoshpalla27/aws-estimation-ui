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
from app.terraform.service_mapping import get_service_code
from app.engine.aggregator import CostAggregator

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_service_code(resource_type: str) -> str:
    """Get service code for resource type."""
    try:
        return get_service_code(resource_type)
    except ValueError:
        # Unknown resource type - will be marked as UNSUPPORTED
        return "Unknown"


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
        
        
        # CRITICAL: Get ACTIVE pricing version using version manager
        from app.pricing.version_manager import PricingVersionManager, VersionStatus
        
        version_manager = PricingVersionManager(db)
        pricing_version = version_manager.get_active_version()
        
        if not pricing_version:
            raise HTTPException(
                status_code=500,
                detail="No ACTIVE pricing version. Run pricing ingestion and activation first."
            )
        
        # Verify version is actually ACTIVE (double-check)
        if pricing_version.status != VersionStatus.ACTIVE:
            raise HTTPException(
                status_code=500,
                detail=f"Pricing version {pricing_version.id} is not ACTIVE (status: {pricing_version.status})"
            )
        
        
        # CRITICAL: Use Terraform Semantic Evaluator (not regex-based parser)
        logger.info(f"Evaluating Terraform semantically for job {job_id}")
        
        from app.terraform.evaluator.engine import TerraformEvaluationEngine
        from app.terraform.evaluator.errors import (
            UnresolvedReferenceError,
            ExpansionLimitExceededError,
            InvalidExpressionError
        )
        
        try:
            # Use semantic evaluator instead of old parser
            evaluator = TerraformEvaluationEngine(
                max_count_expansion=settings.max_count_expansion,
                max_for_each_expansion=settings.max_for_each_expansion
            )
            
            file_path = Path(upload_job.file_path)
            
            # Evaluate Terraform - this will:
            # 1. Parse HCL
            # 2. Resolve variables and locals
            # 3. Evaluate conditionals
            # 4. Expand count
            # 5. Expand for_each
            # 6. Resolve all expressions
            # 7. FAIL HARD on unresolved references
            if file_path.is_file():
                expanded_resources = evaluator.evaluate_terraform_file(file_path)
            else:
                expanded_resources = evaluator.evaluate_terraform_directory(file_path)
            
            logger.info(f"Evaluated {len(expanded_resources)} resources")
            
        except UnresolvedReferenceError as e:
            # CRITICAL: Fail on unresolved variables
            error_msg = f"Terraform evaluation failed: {str(e)}"
            logger.error(error_msg)
            upload_job.status = "failed"
            upload_job.error_message = error_msg
            await db.commit()
            raise HTTPException(status_code=400, detail=error_msg)
        
        except ExpansionLimitExceededError as e:
            # CRITICAL: Fail on expansion limit (no silent truncation)
            error_msg = f"Expansion limit exceeded: {str(e)}"
            logger.error(error_msg)
            upload_job.status = "failed"
            upload_job.error_message = error_msg
            await db.commit()
            raise HTTPException(status_code=400, detail=error_msg)
        
        except InvalidExpressionError as e:
            # CRITICAL: Fail on invalid expressions
            error_msg = f"Invalid Terraform expression: {str(e)}"
            logger.error(error_msg)
            upload_job.status = "failed"
            upload_job.error_message = error_msg
            await db.commit()
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Convert ExpandedResource objects to normalized format for calculator
        normalized_resources = []
        for resource in expanded_resources:
            normalized_resources.append({
                "provider": "aws",
                "service": self._get_service_code(resource.resource_type),
                "type": resource.resource_type,
                "resource_type": resource.resource_type,
                "name": resource.logical_id,
                "region": resource.resolved_region,
                "attributes": resource.resolved_attributes
            })
        
        logger.info(f"Normalized {len(normalized_resources)} resources")
        
        # Update status
        upload_job.status = "calculating"
        await db.commit()
        
        # Calculate costs (ASYNC - no blocking)
        logger.info("Calculating costs")
        from app.engine.async_calculator import AsyncCostCalculator
        
        calculator = AsyncCostCalculator(db, pricing_version)
        cost_results = await calculator.calculate_all_costs(normalized_resources)
        
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
        
        # CRITICAL: Log coverage
        coverage = aggregated.get("coverage_percentage", 0)
        logger.info(f"Pricing coverage: {coverage:.1f}%")
        
        db.add(analysis_result)
        await db.flush()
        
        # Store individual resource costs with explicit status
        for cost_result in cost_results:
            resource_cost = ResourceCost(
                analysis_id=analysis_result.id,
                resource_type=cost_result.get("resource_type", "Unknown"),
                resource_name=cost_result.get("resource_name", "Unknown"),
                service_code=cost_result.get("service_code", "Unknown"),
                region_code=cost_result.get("region"),
                monthly_cost=Decimal(str(cost_result.get("monthly_cost", 0))),
                attributes={
                    "status": cost_result.get("status"),
                    "pricing_rule_id": cost_result.get("pricing_rule_id"),
                    "calculation_steps": cost_result.get("calculation_steps", []),
                    "error_message": cost_result.get("error_message"),
                    "unsupported_reason": cost_result.get("unsupported_reason")
                },
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
            "unsupported_resources": aggregated["resource_counts"]["unsupported"],
            "error_resources": aggregated["resource_counts"]["error"],
            "coverage_percentage": aggregated.get("coverage_percentage", 0),
            "warnings": aggregated["warnings"],
            "errors": aggregated["errors"][:10]  # Limit errors in response
        }
    
    except Exception as e:
        logger.error(f"Analysis failed for job {job_id}: {e}", exc_info=True)
        
        upload_job.status = "failed"
        upload_job.error_message = str(e)
        await db.commit()
        
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
