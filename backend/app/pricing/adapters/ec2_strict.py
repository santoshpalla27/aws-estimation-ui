"""
Example strict EC2 pricing adapter implementation.
Demonstrates the mandatory contract enforcement.
"""
import logging
from typing import Dict, Any, List
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.pricing.adapters.base import (
    PricingAdapter,
    PricingRule,
    CostResult,
    CalculationStep,
    FreeTierStatus,
    ValidationError,
    PricingMatchError,
    CalculationError,
    UnitMismatchError
)
from app.models.models import PricingDimension, PricingVersion

logger = logging.getLogger(__name__)


class StrictEC2Adapter(PricingAdapter):
    """
    Strict EC2 pricing adapter.
    Enforces all contract requirements.
    """
    
    def __init__(self, db: Session, pricing_version: PricingVersion):
        self.db = db
        self.pricing_version = pricing_version
    
    @property
    def required_attributes(self) -> List[str]:
        """EC2 requires instance_type and region."""
        return ["instance_type", "region"]
    
    @property
    def supported_regions(self) -> List[str]:
        """All AWS commercial regions."""
        return [
            "us-east-1", "us-east-2", "us-west-1", "us-west-2",
            "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1",
            "ap-south-1", "ap-southeast-1", "ap-southeast-2",
            "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
            "ca-central-1", "sa-east-1"
        ]
    
    @property
    def service_code(self) -> str:
        return "AmazonEC2"
    
    def validate(self, resource: Dict[str, Any]) -> None:
        """
        Validate EC2 resource.
        
        Raises:
            ValidationError: If validation fails
        """
        # Check required attributes
        self._validate_required_attributes(resource)
        
        # Check region
        self._validate_region(resource)
        
        # Validate instance_type format
        instance_type = resource.get("instance_type")
        if not isinstance(instance_type, str) or not instance_type:
            raise ValidationError(
                f"instance_type must be a non-empty string, got {type(instance_type)}"
            )
        
        # Validate instance_type pattern (e.g., t3.micro)
        if "." not in instance_type:
            raise ValidationError(
                f"Invalid instance_type format: '{instance_type}'. "
                f"Expected format: 'family.size' (e.g., 't3.micro')"
            )
        
        logger.info(f"Validation passed for EC2 instance {instance_type} in {resource.get('region')}")
    
    def match_pricing(self, resource: Dict[str, Any]) -> PricingRule:
        """
        Match EC2 instance to pricing rule.
        
        Raises:
            PricingMatchError: If no pricing found
        """
        instance_type = resource["instance_type"]
        region = resource["region"]
        tenancy = resource.get("tenancy", "Shared")
        operating_system = resource.get("operating_system", "Linux")
        
        # Query pricing database
        query = select(PricingDimension).where(
            PricingDimension.version_id == self.pricing_version.id,
            PricingDimension.service_code == "AmazonEC2",
            PricingDimension.region_code == region,
            PricingDimension.attributes["instanceType"].astext == instance_type,
            PricingDimension.attributes["tenancy"].astext == tenancy,
            PricingDimension.attributes["operatingSystem"].astext == operating_system
        )
        
        result = self.db.execute(query).scalar_one_or_none()
        
        # MUST find pricing or error
        if result is None:
            raise PricingMatchError(
                f"No pricing found for EC2 instance_type='{instance_type}', "
                f"region='{region}', tenancy='{tenancy}', os='{operating_system}'"
            )
        
        # Convert to PricingRule
        pricing_rule = PricingRule(
            id=result.id,
            service_code=result.service_code,
            region_code=result.region_code,
            price_per_unit=result.price_per_unit,
            unit=result.unit,
            currency=result.currency,
            attributes=result.attributes
        )
        
        logger.info(f"Matched pricing rule {pricing_rule.id} for {instance_type}")
        return pricing_rule
    
    def calculate(self, resource: Dict[str, Any], pricing_rule: PricingRule) -> CostResult:
        """
        Calculate EC2 instance cost.
        
        Raises:
            CalculationError: If calculation fails
            UnitMismatchError: If units don't match
        """
        # Validate unit (EC2 pricing is per hour)
        expected_unit = "Hrs"
        self._validate_unit_match(expected_unit, pricing_rule.unit)
        
        # Extract values
        hourly_rate = pricing_rule.price_per_unit
        hours_per_month = Decimal("730")  # Standard month
        
        # Build calculation steps
        steps = []
        
        # Step 1: Hourly rate
        steps.append(CalculationStep(
            description="Hourly instance rate from pricing database",
            formula="price_per_unit",
            inputs={
                "instance_type": resource["instance_type"],
                "region": resource["region"],
                "pricing_rule_id": pricing_rule.id
            },
            result=hourly_rate,
            unit="USD/hour"
        ))
        
        # Step 2: Monthly hours
        steps.append(CalculationStep(
            description="Hours in standard month",
            formula="730 hours (365 days / 12 months * 24 hours)",
            inputs={},
            result=hours_per_month,
            unit="hours"
        ))
        
        # Step 3: Monthly cost
        monthly_cost = hourly_rate * hours_per_month
        steps.append(CalculationStep(
            description="Monthly cost calculation",
            formula="hourly_rate * hours_per_month",
            inputs={
                "hourly_rate": float(hourly_rate),
                "hours_per_month": float(hours_per_month)
            },
            result=monthly_cost,
            unit="USD/month"
        ))
        
        # EC2 has no free tier for most instances
        free_tier_status = FreeTierStatus.NOT_APPLICABLE
        warnings = []
        
        # Check if t2.micro or t3.micro (free tier eligible)
        if resource["instance_type"] in ["t2.micro", "t3.micro"]:
            free_tier_status = FreeTierStatus.EXCEEDED
            warnings.append(
                "Instance type is free tier eligible (750 hours/month), "
                "but free tier calculation not implemented"
            )
        
        # Create result
        result = CostResult(
            monthly_cost=monthly_cost,
            pricing_rule_id=pricing_rule.id,
            unit="USD/month",
            calculation_steps=steps,
            free_tier_applied=free_tier_status,
            warnings=warnings,
            resource_id=resource.get("name", "unknown")
        )
        
        logger.info(f"Calculated cost ${monthly_cost} for {resource['instance_type']}")
        return result
