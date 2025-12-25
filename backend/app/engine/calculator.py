"""
Cost calculator.
Calculates costs for normalized resources.
"""
import logging
from typing import Dict, List
from decimal import Decimal

from sqlalchemy.orm import Session
from app.models.models import PricingVersion
from app.engine.matcher import ServiceMatcher

logger = logging.getLogger(__name__)


class CostCalculator:
    """
    Calculates costs for resources.
    """
    
    def __init__(self, db: Session, pricing_version: PricingVersion):
        self.db = db
        self.pricing_version = pricing_version
        self.matcher = ServiceMatcher(db, pricing_version)
    
    def calculate_resource_cost(self, resource: Dict) -> Dict:
        """
        Calculate cost for a single resource.
        
        Args:
            resource: Normalized resource
        
        Returns:
            Cost result with monthly_cost, pricing_details, warnings
        """
        # Get adapter for this resource
        adapter = self.matcher.match_resource(resource)
        
        if not adapter:
            return {
                "monthly_cost": 0.0,
                "pricing_details": {"error": "No adapter available"},
                "warnings": [f"Unsupported service: {resource.get('service')}"]
            }
        
        # Calculate cost using adapter
        try:
            # Pass resource attributes to adapter
            cost_result = adapter.calculate_cost(resource.get("attributes", {}))
            
            # Add resource metadata
            cost_result["resource_type"] = resource.get("resource_type")
            cost_result["resource_name"] = resource.get("name")
            cost_result["service_code"] = resource.get("service")
            cost_result["region"] = resource.get("region")
            
            return cost_result
        
        except Exception as e:
            logger.error(f"Error calculating cost for {resource.get('name')}: {e}", exc_info=True)
            return {
                "monthly_cost": 0.0,
                "pricing_details": {"error": str(e)},
                "warnings": [f"Calculation error: {str(e)}"]
            }
    
    def calculate_all_costs(self, resources: List[Dict]) -> List[Dict]:
        """
        Calculate costs for all resources.
        
        Args:
            resources: List of normalized resources
        
        Returns:
            List of cost results
        """
        results = []
        
        for resource in resources:
            cost_result = self.calculate_resource_cost(resource)
            results.append(cost_result)
        
        logger.info(f"Calculated costs for {len(results)} resources")
        return results
