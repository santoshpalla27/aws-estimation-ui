"""
Cost aggregator with EXPLICIT status-based aggregation.
NO inference from monthly_cost amount.
"""
import logging
from typing import Dict, List
from decimal import Decimal
from collections import defaultdict

logger = logging.getLogger(__name__)


class CostAggregator:
    """
    Aggregates cost results with explicit status handling.
    
    CRITICAL: Uses explicit 'status' field, NOT cost amount inference.
    """
    
    def __init__(self, cost_results: List[Dict]):
        self.cost_results = cost_results
    
    def aggregate_by_service(self) -> Dict[str, float]:
        """
        Aggregate costs by service (SUPPORTED resources only).
        
        Returns:
            Dictionary mapping service codes to total costs
        """
        service_costs = defaultdict(float)
        
        for result in self.cost_results:
            # CRITICAL: Only include SUPPORTED resources
            status = result.get("status")
            if status != "SUPPORTED":
                continue
            
            service = result.get("service_code", "Unknown")
            cost = result.get("monthly_cost", 0.0)
            service_costs[service] += cost
        
        return dict(service_costs)
    
    def aggregate_by_region(self) -> Dict[str, float]:
        """
        Aggregate costs by region (SUPPORTED resources only).
        
        Returns:
            Dictionary mapping regions to total costs
        """
        region_costs = defaultdict(float)
        
        for result in self.cost_results:
            # CRITICAL: Only include SUPPORTED resources
            status = result.get("status")
            if status != "SUPPORTED":
                continue
            
            region = result.get("region", "Unknown")
            cost = result.get("monthly_cost", 0.0)
            region_costs[region] += cost
        
        return dict(region_costs)
    
    def aggregate_by_resource_type(self) -> Dict[str, float]:
        """
        Aggregate costs by resource type (SUPPORTED resources only).
        
        Returns:
            Dictionary mapping resource types to total costs
        """
        type_costs = defaultdict(float)
        
        for result in self.cost_results:
            # CRITICAL: Only include SUPPORTED resources
            status = result.get("status")
            if status != "SUPPORTED":
                continue
            
            resource_type = result.get("resource_type", "Unknown")
            cost = result.get("monthly_cost", 0.0)
            type_costs[resource_type] += cost
        
        return dict(type_costs)
    
    def get_total_cost(self) -> float:
        """
        Get total monthly cost (SUPPORTED resources only).
        
        Returns:
            Total cost across SUPPORTED resources
        """
        total = 0.0
        for result in self.cost_results:
            # CRITICAL: Only include SUPPORTED resources
            status = result.get("status")
            if status == "SUPPORTED":
                total += result.get("monthly_cost", 0.0)
        
        return total
    
    def get_resource_counts(self) -> Dict[str, int]:
        """
        Get resource counts by explicit status.
        
        Returns:
            Dictionary with total, supported, unsupported, and error counts
        """
        total = len(self.cost_results)
        supported = sum(1 for r in self.cost_results if r.get("status") == "SUPPORTED")
        unsupported = sum(1 for r in self.cost_results if r.get("status") == "UNSUPPORTED")
        errors = sum(1 for r in self.cost_results if r.get("status") == "ERROR")
        
        return {
            "total": total,
            "supported": supported,
            "unsupported": unsupported,
            "error": errors
        }
    
    def get_coverage_percentage(self) -> float:
        """
        Get pricing coverage percentage.
        
        Returns:
            Percentage of resources with SUPPORTED status
        """
        counts = self.get_resource_counts()
        if counts["total"] == 0:
            return 0.0
        
        return (counts["supported"] / counts["total"]) * 100.0
    
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
        
        # Add coverage warning if incomplete
        coverage = self.get_coverage_percentage()
        if coverage < 100.0:
            warnings.add(
                f"Pricing coverage: {coverage:.1f}% - "
                f"some resources excluded from totals"
            )
        
        return list(warnings)
    
    def collect_errors(self) -> List[Dict]:
        """
        Collect all ERROR status resources.
        
        Returns:
            List of error dictionaries
        """
        errors = []
        
        for result in self.cost_results:
            status = result.get("status")
            if status == "ERROR":
                errors.append({
                    "resource": result.get("resource_name"),
                    "type": result.get("resource_type"),
                    "error": result.get("error_message", "Unknown error")
                })
        
        return errors
    
    def collect_unsupported(self) -> List[Dict]:
        """
        Collect all UNSUPPORTED status resources.
        
        Returns:
            List of unsupported resource dictionaries
        """
        unsupported = []
        
        for result in self.cost_results:
            status = result.get("status")
            if status == "UNSUPPORTED":
                unsupported.append({
                    "resource": result.get("resource_name"),
                    "type": result.get("resource_type"),
                    "reason": result.get("unsupported_reason", "Unknown reason")
                })
        
        return unsupported
    
    def aggregate_all(self) -> Dict:
        """
        Perform all aggregations with explicit status handling.
        
        Returns:
            Complete aggregation result
        """
        counts = self.get_resource_counts()
        coverage = self.get_coverage_percentage()
        
        return {
            "total_monthly_cost": self.get_total_cost(),
            "breakdown_by_service": self.aggregate_by_service(),
            "breakdown_by_region": self.aggregate_by_region(),
            "breakdown_by_type": self.aggregate_by_resource_type(),
            "resource_counts": counts,
            "coverage_percentage": coverage,
            "warnings": self.collect_warnings(),
            "errors": self.collect_errors(),
            "unsupported": self.collect_unsupported()
        }
