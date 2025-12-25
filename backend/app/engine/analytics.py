"""
Cost analytics with explicit resource status tracking.
Provides accurate aggregation with no inference from zero costs.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class ResourceStatus(str, Enum):
    """
    Explicit resource cost calculation status.
    
    SUPPORTED: Successfully calculated cost
    UNSUPPORTED: Resource type not supported by pricing engine
    ERROR: Calculation failed due to error
    """
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


@dataclass
class ResourceCostResult:
    """
    Cost result for a single resource with explicit status.
    
    NO inference from monthly_cost == 0.
    Status MUST be explicitly set.
    """
    resource_id: str
    resource_type: str
    resource_name: str
    status: ResourceStatus
    
    # Cost data (only valid if status == SUPPORTED)
    monthly_cost: Decimal = Decimal("0")
    pricing_rule_id: Optional[int] = None
    calculation_steps: List[Dict] = field(default_factory=list)
    
    # Metadata
    service_code: Optional[str] = None
    region: Optional[str] = None
    
    # Status details
    error_message: Optional[str] = None
    unsupported_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate resource cost result."""
        # Ensure monthly_cost is Decimal
        if not isinstance(self.monthly_cost, Decimal):
            self.monthly_cost = Decimal(str(self.monthly_cost))
        
        # Validate status-specific requirements
        if self.status == ResourceStatus.SUPPORTED:
            if self.pricing_rule_id is None:
                raise ValueError(
                    f"SUPPORTED resource {self.resource_id} must have pricing_rule_id"
                )
            if not self.calculation_steps:
                raise ValueError(
                    f"SUPPORTED resource {self.resource_id} must have calculation_steps"
                )
        
        elif self.status == ResourceStatus.UNSUPPORTED:
            if not self.unsupported_reason:
                raise ValueError(
                    f"UNSUPPORTED resource {self.resource_id} must have unsupported_reason"
                )
        
        elif self.status == ResourceStatus.ERROR:
            if not self.error_message:
                raise ValueError(
                    f"ERROR resource {self.resource_id} must have error_message"
                )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "resource_name": self.resource_name,
            "status": self.status.value,
            "monthly_cost": float(self.monthly_cost),
            "pricing_rule_id": self.pricing_rule_id,
            "calculation_steps": self.calculation_steps,
            "service_code": self.service_code,
            "region": self.region,
            "error_message": self.error_message,
            "unsupported_reason": self.unsupported_reason,
            "warnings": self.warnings
        }


@dataclass
class CostAnalytics:
    """
    Aggregated cost analytics with explicit correctness states.
    
    Aggregation Rules:
    - SUPPORTED: Included in totals
    - UNSUPPORTED: Excluded from totals, reported separately
    - ERROR: Excluded from totals, flagged
    """
    
    # Totals (SUPPORTED resources only)
    total_monthly_cost: Decimal
    total_supported_resources: int
    
    # Breakdowns (SUPPORTED resources only)
    cost_by_service: Dict[str, Decimal]
    cost_by_region: Dict[str, Decimal]
    cost_by_resource_type: Dict[str, Decimal]
    
    # Resource details
    supported_resources: List[ResourceCostResult]
    unsupported_resources: List[ResourceCostResult]
    error_resources: List[ResourceCostResult]
    
    # Coverage metrics
    total_resources: int
    coverage_percentage: float
    
    # Warnings and errors
    global_warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "summary": {
                "total_monthly_cost": float(self.total_monthly_cost),
                "total_resources": self.total_resources,
                "supported_resources": self.total_supported_resources,
                "unsupported_resources": len(self.unsupported_resources),
                "error_resources": len(self.error_resources),
                "coverage_percentage": self.coverage_percentage
            },
            "breakdowns": {
                "by_service": {k: float(v) for k, v in self.cost_by_service.items()},
                "by_region": {k: float(v) for k, v in self.cost_by_region.items()},
                "by_resource_type": {k: float(v) for k, v in self.cost_by_resource_type.items()}
            },
            "supported_resources": [r.to_dict() for r in self.supported_resources],
            "unsupported_resources": [
                {
                    "resource_id": r.resource_id,
                    "resource_type": r.resource_type,
                    "resource_name": r.resource_name,
                    "reason": r.unsupported_reason,
                    "service_code": r.service_code
                }
                for r in self.unsupported_resources
            ],
            "error_resources": [
                {
                    "resource_id": r.resource_id,
                    "resource_type": r.resource_type,
                    "resource_name": r.resource_name,
                    "error": r.error_message,
                    "service_code": r.service_code
                }
                for r in self.error_resources
            ],
            "warnings": self.global_warnings
        }


class CostAggregator:
    """
    Aggregates resource cost results with explicit status handling.
    
    NO inference from monthly_cost == 0.
    Status determines aggregation behavior.
    """
    
    def __init__(self, resource_results: List[ResourceCostResult]):
        """
        Initialize aggregator.
        
        Args:
            resource_results: List of resource cost results with explicit status
        """
        self.resource_results = resource_results
    
    def aggregate(self) -> CostAnalytics:
        """
        Aggregate cost results with explicit status handling.
        
        Returns:
            CostAnalytics with complete breakdown
        """
        # Separate by status
        supported = [r for r in self.resource_results if r.status == ResourceStatus.SUPPORTED]
        unsupported = [r for r in self.resource_results if r.status == ResourceStatus.UNSUPPORTED]
        errors = [r for r in self.resource_results if r.status == ResourceStatus.ERROR]
        
        logger.info(
            f"Aggregating: {len(supported)} supported, "
            f"{len(unsupported)} unsupported, {len(errors)} errors"
        )
        
        # Calculate total (SUPPORTED only)
        total_cost = sum(r.monthly_cost for r in supported)
        
        # Aggregate by service (SUPPORTED only)
        cost_by_service = {}
        for r in supported:
            if r.service_code:
                cost_by_service[r.service_code] = (
                    cost_by_service.get(r.service_code, Decimal("0")) + r.monthly_cost
                )
        
        # Aggregate by region (SUPPORTED only)
        cost_by_region = {}
        for r in supported:
            if r.region:
                cost_by_region[r.region] = (
                    cost_by_region.get(r.region, Decimal("0")) + r.monthly_cost
                )
        
        # Aggregate by resource type (SUPPORTED only)
        cost_by_type = {}
        for r in supported:
            cost_by_type[r.resource_type] = (
                cost_by_type.get(r.resource_type, Decimal("0")) + r.monthly_cost
            )
        
        # Calculate coverage
        total_resources = len(self.resource_results)
        coverage = (len(supported) / total_resources * 100) if total_resources > 0 else 0
        
        # Collect global warnings
        warnings = []
        if len(unsupported) > 0:
            warnings.append(
                f"{len(unsupported)} resource(s) not supported by pricing engine"
            )
        if len(errors) > 0:
            warnings.append(
                f"{len(errors)} resource(s) failed cost calculation"
            )
        if coverage < 100:
            warnings.append(
                f"Pricing coverage: {coverage:.1f}% - some resources excluded from totals"
            )
        
        return CostAnalytics(
            total_monthly_cost=total_cost,
            total_supported_resources=len(supported),
            cost_by_service=cost_by_service,
            cost_by_region=cost_by_region,
            cost_by_resource_type=cost_by_type,
            supported_resources=supported,
            unsupported_resources=unsupported,
            error_resources=errors,
            total_resources=total_resources,
            coverage_percentage=coverage,
            global_warnings=warnings
        )
    
    def get_unsupported_summary(self) -> Dict[str, List[str]]:
        """
        Get summary of unsupported resources grouped by reason.
        
        Returns:
            Dictionary mapping reasons to resource lists
        """
        summary = {}
        
        for r in self.resource_results:
            if r.status == ResourceStatus.UNSUPPORTED:
                reason = r.unsupported_reason or "Unknown reason"
                if reason not in summary:
                    summary[reason] = []
                summary[reason].append(f"{r.resource_type}.{r.resource_name}")
        
        return summary
    
    def get_error_summary(self) -> Dict[str, List[str]]:
        """
        Get summary of error resources grouped by error type.
        
        Returns:
            Dictionary mapping error types to resource lists
        """
        summary = {}
        
        for r in self.resource_results:
            if r.status == ResourceStatus.ERROR:
                error = r.error_message or "Unknown error"
                # Extract error type from message
                error_type = error.split(":")[0] if ":" in error else error
                
                if error_type not in summary:
                    summary[error_type] = []
                summary[error_type].append(f"{r.resource_type}.{r.resource_name}")
        
        return summary
    
    def get_missing_coverage(self) -> Dict[str, int]:
        """
        Get missing pricing coverage by service.
        
        Returns:
            Dictionary mapping service codes to count of unsupported resources
        """
        coverage = {}
        
        for r in self.resource_results:
            if r.status == ResourceStatus.UNSUPPORTED and r.service_code:
                coverage[r.service_code] = coverage.get(r.service_code, 0) + 1
        
        return coverage
