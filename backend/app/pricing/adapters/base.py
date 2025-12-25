"""
Strict pricing adapter contract.
Enforces validation and prevents silent miscalculations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class ValidationError(Exception):
    """Raised when adapter validation fails."""
    pass


class PricingMatchError(Exception):
    """Raised when no pricing rule can be matched."""
    pass


class CalculationError(Exception):
    """Raised when cost calculation fails."""
    pass


class UnitMismatchError(Exception):
    """Raised when pricing units don't match resource units."""
    pass


class FreeTierStatus(Enum):
    """Free tier application status."""
    NOT_APPLICABLE = "not_applicable"
    APPLIED = "applied"
    EXCEEDED = "exceeded"
    UNKNOWN = "unknown"


@dataclass
class CalculationStep:
    """
    Single step in cost calculation.
    Provides audit trail for cost derivation.
    """
    description: str
    formula: str
    inputs: Dict[str, Any]
    result: Decimal
    unit: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "description": self.description,
            "formula": self.formula,
            "inputs": self.inputs,
            "result": float(self.result),
            "unit": self.unit
        }


@dataclass
class CostResult:
    """
    Mandatory cost calculation result.
    
    NO silent zeroes allowed - every field must be explicitly set.
    NO implicit success - calculation steps must be provided.
    """
    monthly_cost: Decimal
    pricing_rule_id: int
    unit: str
    calculation_steps: List[CalculationStep]
    free_tier_applied: FreeTierStatus
    
    # Optional metadata
    warnings: List[str] = None
    resource_id: str = None
    
    def __post_init__(self):
        """Validate cost result on creation."""
        # Ensure monthly_cost is Decimal
        if not isinstance(self.monthly_cost, Decimal):
            self.monthly_cost = Decimal(str(self.monthly_cost))
        
        # Validate required fields
        if self.monthly_cost < 0:
            raise CalculationError("monthly_cost cannot be negative")
        
        if self.pricing_rule_id is None:
            raise CalculationError("pricing_rule_id must be set")
        
        if not self.unit:
            raise CalculationError("unit must be specified")
        
        if not self.calculation_steps:
            raise CalculationError("calculation_steps cannot be empty - must show work")
        
        if self.free_tier_applied is None:
            raise CalculationError("free_tier_applied must be explicitly set")
        
        # Initialize warnings if None
        if self.warnings is None:
            self.warnings = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "monthly_cost": float(self.monthly_cost),
            "pricing_rule_id": self.pricing_rule_id,
            "unit": self.unit,
            "calculation_steps": [step.to_dict() for step in self.calculation_steps],
            "free_tier_applied": self.free_tier_applied.value,
            "warnings": self.warnings,
            "resource_id": self.resource_id
        }


@dataclass
class PricingRule:
    """
    Matched pricing rule from database.
    """
    id: int
    service_code: str
    region_code: str
    price_per_unit: Decimal
    unit: str
    currency: str
    attributes: Dict[str, Any]
    
    def __post_init__(self):
        """Validate pricing rule."""
        if not isinstance(self.price_per_unit, Decimal):
            self.price_per_unit = Decimal(str(self.price_per_unit))
        
        if self.price_per_unit < 0:
            raise ValueError("price_per_unit cannot be negative")
        
        if not self.unit:
            raise ValueError("unit must be specified")


class PricingAdapter(ABC):
    """
    Abstract base class for all pricing adapters.
    
    STRICT CONTRACT:
    - Must declare required_attributes
    - Must declare supported_regions
    - Must implement validate() - raises on missing/invalid attributes
    - Must implement match_pricing() - raises if no rule found
    - Must implement calculate() - returns CostResult with full audit trail
    
    NO SILENT FAILURES ALLOWED.
    """
    
    @property
    @abstractmethod
    def required_attributes(self) -> List[str]:
        """
        List of required resource attributes.
        Adapter MUST fail if any are missing.
        """
        pass
    
    @property
    @abstractmethod
    def supported_regions(self) -> List[str]:
        """
        List of supported AWS regions.
        Adapter MUST fail if region is not in this list.
        """
        pass
    
    @property
    @abstractmethod
    def service_code(self) -> str:
        """AWS service code (e.g., 'AmazonEC2')."""
        pass
    
    @abstractmethod
    def validate(self, resource: Dict[str, Any]) -> None:
        """
        Validate resource has all required attributes.
        
        Args:
            resource: Resource to validate
        
        Raises:
            ValidationError: If validation fails (REQUIRED)
        
        MUST check:
        - All required_attributes are present
        - Region is supported
        - Attribute values are valid types
        """
        pass
    
    @abstractmethod
    def match_pricing(self, resource: Dict[str, Any]) -> PricingRule:
        """
        Match resource to a pricing rule.
        
        Args:
            resource: Resource to match
        
        Returns:
            PricingRule from database
        
        Raises:
            PricingMatchError: If no pricing rule found (REQUIRED)
            
        MUST NOT return None - raise error if no match.
        """
        pass
    
    @abstractmethod
    def calculate(self, resource: Dict[str, Any], pricing_rule: PricingRule) -> CostResult:
        """
        Calculate cost for resource using pricing rule.
        
        Args:
            resource: Resource to calculate cost for
            pricing_rule: Matched pricing rule
        
        Returns:
            CostResult with full calculation audit trail
        
        Raises:
            CalculationError: If calculation fails (REQUIRED)
            UnitMismatchError: If units don't match (REQUIRED)
        
        MUST:
        - Validate unit compatibility
        - Provide calculation_steps showing all work
        - Set free_tier_applied explicitly
        - Return CostResult (never None)
        """
        pass
    
    def calculate_cost(self, resource: Dict[str, Any]) -> CostResult:
        """
        Complete cost calculation pipeline with validation.
        
        This is the main entry point that enforces the contract.
        
        Args:
            resource: Resource to calculate cost for
        
        Returns:
            CostResult with full audit trail
        
        Raises:
            ValidationError: If validation fails
            PricingMatchError: If no pricing rule found
            CalculationError: If calculation fails
        """
        # Step 1: Validate (MUST NOT be silent)
        self.validate(resource)
        
        # Step 2: Match pricing (MUST find a rule or error)
        pricing_rule = self.match_pricing(resource)
        
        # Step 3: Calculate (MUST return CostResult with steps)
        cost_result = self.calculate(resource, pricing_rule)
        
        # Validate result
        if not isinstance(cost_result, CostResult):
            raise CalculationError(
                f"Adapter {self.__class__.__name__} must return CostResult, got {type(cost_result)}"
            )
        
        return cost_result
    
    def _validate_required_attributes(self, resource: Dict[str, Any]) -> None:
        """
        Helper to validate required attributes are present.
        
        Args:
            resource: Resource to validate
        
        Raises:
            ValidationError: If any required attribute is missing
        """
        missing = []
        for attr in self.required_attributes:
            if attr not in resource:
                missing.append(attr)
        
        if missing:
            raise ValidationError(
                f"Missing required attributes for {self.service_code}: {', '.join(missing)}"
            )
    
    def _validate_region(self, resource: Dict[str, Any]) -> None:
        """
        Helper to validate region is supported.
        
        Args:
            resource: Resource to validate
        
        Raises:
            ValidationError: If region is not supported
        """
        region = resource.get("region")
        
        if not region:
            raise ValidationError(f"Region is required for {self.service_code}")
        
        if region not in self.supported_regions:
            raise ValidationError(
                f"Region '{region}' not supported for {self.service_code}. "
                f"Supported: {', '.join(self.supported_regions)}"
            )
    
    def _validate_unit_match(self, resource_unit: str, pricing_unit: str) -> None:
        """
        Helper to validate units match.
        
        Args:
            resource_unit: Unit from resource
            pricing_unit: Unit from pricing rule
        
        Raises:
            UnitMismatchError: If units don't match
        """
        if resource_unit != pricing_unit:
            raise UnitMismatchError(
                f"Unit mismatch: resource uses '{resource_unit}', "
                f"pricing uses '{pricing_unit}'"
            )
