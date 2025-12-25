"""
Async cost calculator.
Calculates costs for normalized resources using async database access.
"""
import logging
from typing import Dict, List
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import PricingVersion
from app.engine.async_matcher import AsyncServiceMatcher

logger = logging.getLogger(__name__)


class AsyncCostCalculator:
    """
    Calculates costs for resources using async database access.
    """
    
    def __init__(self, db: AsyncSession, pricing_version: PricingVersion):
        self.db = db
        self.pricing_version = pricing_version
        self.matcher = AsyncServiceMatcher(db, pricing_version)
    
    async def calculate_resource_cost(self, resource: Dict) -> Dict:
        """
        Calculate cost for a single resource.
        
        Args:
            resource: Normalized resource
        
        Returns:
            Cost result with status, monthly_cost, pricing_details
        """
        # Get adapter for this resource
        adapter = await self.matcher.match_resource_async(resource)
        
        if not adapter:
            # CRITICAL: Explicit UNSUPPORTED status
            return {
                "status": "UNSUPPORTED",
                "resource_type": resource.get("resource_type"),
                "resource_name": resource.get("name"),
                "service_code": resource.get("service"),
                "region": resource.get("region"),
                "monthly_cost": 0.0,
                "unsupported_reason": f"No adapter available for service: {resource.get('service')}",
                "warnings": []
            }
        
        # Calculate cost using adapter
        try:
            # Validate resource first
            adapter.validate(resource.get("attributes", {}))
            
            # Match pricing
            pricing_rule = await adapter.match_pricing(resource.get("attributes", {}))
            
            # Calculate cost
            cost_result = adapter.calculate(
                resource.get("attributes", {}),
                pricing_rule
            )
            
            # Add resource metadata
            result = {
                "status": "SUPPORTED",
                "resource_type": resource.get("resource_type"),
                "resource_name": resource.get("name"),
                "service_code": resource.get("service"),
                "region": resource.get("region"),
                "monthly_cost": float(cost_result.monthly_cost),
                "pricing_rule_id": cost_result.pricing_rule_id,
                "calculation_steps": [
                    {
                        "description": step.description,
                        "formula": step.formula,
                        "result": float(step.result)
                    }
                    for step in cost_result.calculation_steps
                ],
                "warnings": cost_result.warnings
            }
            
            return result
        
        except Exception as e:
            # CRITICAL: Explicit ERROR status
            logger.error(f"Error calculating cost for {resource.get('name')}: {e}", exc_info=True)
            return {
                "status": "ERROR",
                "resource_type": resource.get("resource_type"),
                "resource_name": resource.get("name"),
                "service_code": resource.get("service"),
                "region": resource.get("region"),
                "monthly_cost": 0.0,
                "error_message": str(e),
                "warnings": []
            }
    
    async def calculate_all_costs(self, resources: List[Dict]) -> List[Dict]:
        """
        Calculate costs for all resources.
        
        Args:
            resources: List of normalized resources
        
        Returns:
            List of cost results with explicit status
        """
        results = []
        
        for resource in resources:
            cost_result = await self.calculate_resource_cost(resource)
            results.append(cost_result)
        
        logger.info(f"Calculated costs for {len(results)} resources")
        
        # Log status breakdown
        supported = sum(1 for r in results if r["status"] == "SUPPORTED")
        unsupported = sum(1 for r in results if r["status"] == "UNSUPPORTED")
        errors = sum(1 for r in results if r["status"] == "ERROR")
        
        logger.info(
            f"Status breakdown: {supported} SUPPORTED, "
            f"{unsupported} UNSUPPORTED, {errors} ERROR"
        )
        
        return results
