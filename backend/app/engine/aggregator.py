"""
Cost aggregator.
Aggregates costs by service, region, and resource type.
"""
import logging
from typing import Dict, List
from decimal import Decimal
from collections import defaultdict

logger = logging.getLogger(__name__)


class CostAggregator:
    """
    Aggregates cost results.
    """
    
    def __init__(self, cost_results: List[Dict]):
        self.cost_results = cost_results
    
    def aggregate_by_service(self) -> Dict[str, float]:
        """
        Aggregate costs by service.
        
        Returns:
            Dictionary mapping service codes to total costs
        """
        service_costs = defaultdict(float)
        
        for result in self.cost_results:
            service = result.get("service_code", "Unknown")
            cost = result.get("monthly_cost", 0.0)
            service_costs[service] += cost
        
        return dict(service_costs)
    
    def aggregate_by_region(self) -> Dict[str, float]:
        """
        Aggregate costs by region.
        
        Returns:
            Dictionary mapping regions to total costs
        """
        region_costs = defaultdict(float)
        
        for result in self.cost_results:
            region = result.get("region", "Unknown")
            cost = result.get("monthly_cost", 0.0)
            region_costs[region] += cost
        
        return dict(region_costs)
    
    def aggregate_by_resource_type(self) -> Dict[str, float]:
        """
        Aggregate costs by resource type.
        
        Returns:
            Dictionary mapping resource types to total costs
        """
        type_costs = defaultdict(float)
        
        for result in self.cost_results:
            resource_type = result.get("resource_type", "Unknown")
            cost = result.get("monthly_cost", 0.0)
            type_costs[resource_type] += cost
        
        return dict(type_costs)
    
    def get_total_cost(self) -> float:
        """
        Get total monthly cost.
        
        Returns:
            Total cost across all resources
        """
        return sum(result.get("monthly_cost", 0.0) for result in self.cost_results)
    
    def get_resource_counts(self) -> Dict[str, int]:
        """
        Get resource counts.
        
        Returns:
            Dictionary with total, supported, and unsupported counts
        """
        total = len(self.cost_results)
        supported = sum(
            1 for r in self.cost_results
            if r.get("monthly_cost", 0) > 0 or not r.get("pricing_details", {}).get("error")
        )
        unsupported = total - supported
        
        return {
            "total": total,
            "supported": supported,
            "unsupported": unsupported
        }
    
    def collect_warnings(self) -> List[str]:
        """
        Collect all warnings from cost results.
        
        Returns:
            List of unique warnings
        """
        warnings = set()
        
        for result in self.cost_results:
            result_warnings = result.get("warnings", [])
            warnings.update(result_warnings)
        
        return list(warnings)
    
    def collect_errors(self) -> List[Dict]:
        """
        Collect all errors from cost results.
        
        Returns:
            List of error dictionaries
        """
        errors = []
        
        for result in self.cost_results:
            error = result.get("pricing_details", {}).get("error")
            if error:
                errors.append({
                    "resource": result.get("resource_name"),
                    "type": result.get("resource_type"),
                    "error": error
                })
        
        return errors
    
    def aggregate_all(self) -> Dict:
        """
        Perform all aggregations.
        
        Returns:
            Complete aggregation result
        """
        return {
            "total_monthly_cost": self.get_total_cost(),
            "breakdown_by_service": self.aggregate_by_service(),
            "breakdown_by_region": self.aggregate_by_region(),
            "breakdown_by_type": self.aggregate_by_resource_type(),
            "resource_counts": self.get_resource_counts(),
            "warnings": self.collect_warnings(),
            "errors": self.collect_errors()
        }
