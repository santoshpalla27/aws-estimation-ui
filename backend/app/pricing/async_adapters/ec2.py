"""
Async EC2 pricing adapter.
All database queries are async.
"""
import logging
from typing import Dict, Any, List
from decimal import Decimal

from app.pricing.async_adapters.base import AsyncPricingAdapter
from app.pricing.adapters.base import (
    PricingRule,
    CostResult,
    CalculationStep,
    FreeTierStatus,
    ValidationError,
    PricingMatchError
)

logger = logging.getLogger(__name__)


class AsyncEC2Adapter(AsyncPricingAdapter):
    """
    Async EC2 pricing adapter.
    Database queries are async, calculations are sync.
    """
    
    @property
    def required_attributes(self) -> List[str]:
        return ["instance_type", "region"]
    
    @property
    def supported_regions(self) -> List[str]:
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
        """Validate EC2 resource (synchronous)."""
        # Check required attributes
        missing = []
        for attr in self.required_attributes:
            if attr not in resource:
                missing.append(attr)
        
        if missing:
            raise ValidationError(
                f"Missing required attributes for {self.service_code}: {', '.join(missing)}"
            )
        
        # Check region
        region = resource.get("region")
        if region not in self.supported_regions:
            raise ValidationError(
                f"Region '{region}' not supported for {self.service_code}"
            )
        
        # Validate instance_type format
        instance_type = resource.get("instance_type")
        if not isinstance(instance_type, str) or "." not in instance_type:
            raise ValidationError(
                f"Invalid instance_type format: '{instance_type}'"
            )
    
    async def match_pricing(self, resource: Dict[str, Any]) -> PricingRule:
        """Match EC2 instance to pricing rule (async database query)."""
        instance_type = resource["instance_type"]
        region = resource["region"]
        tenancy = resource.get("tenancy", "Shared")
        operating_system = resource.get("operating_system", "Linux")
        
        # Async database query
        dimension = await self._query_pricing_dimension(
            service_code="AmazonEC2",
            region_code=region,
            filters={
                "instanceType": instance_type,
                "tenancy": tenancy,
                "operatingSystem": operating_system
            }
        )
        
        # Convert to PricingRule
        return PricingRule(
            id=dimension.id,
            service_code=dimension.service_code,
            region_code=dimension.region_code,
            price_per_unit=dimension.price_per_unit,
            unit=dimension.unit,
            currency=dimension.currency,
            attributes=dimension.attributes
        )
    
    def calculate(self, resource: Dict[str, Any], pricing_rule: PricingRule) -> CostResult:
        """Calculate EC2 cost (synchronous calculation)."""
        # Validate unit
        if pricing_rule.unit != "Hrs":
            raise ValueError(f"Expected unit 'Hrs', got '{pricing_rule.unit}'")
        
        # Calculate
        hourly_rate = pricing_rule.price_per_unit
        hours_per_month = Decimal("730")
        monthly_cost = hourly_rate * hours_per_month
        
        # Build calculation steps
        steps = [
            CalculationStep(
                description="Hourly instance rate",
                formula="price_per_unit",
                inputs={
                    "instance_type": resource["instance_type"],
                    "region": resource["region"]
                },
                result=hourly_rate,
                unit="USD/hour"
            ),
            CalculationStep(
                description="Hours in month",
                formula="730 hours",
                inputs={},
                result=hours_per_month,
                unit="hours"
            ),
            CalculationStep(
                description="Monthly cost",
                formula="hourly_rate * hours_per_month",
                inputs={
                    "hourly_rate": float(hourly_rate),
                    "hours_per_month": float(hours_per_month)
                },
                result=monthly_cost,
                unit="USD/month"
            )
        ]
        
        # Check free tier
        free_tier_status = FreeTierStatus.NOT_APPLICABLE
        warnings = []
        
        if resource["instance_type"] in ["t2.micro", "t3.micro"]:
            free_tier_status = FreeTierStatus.EXCEEDED
            warnings.append("Free tier eligible but not calculated")
        
        return CostResult(
            monthly_cost=monthly_cost,
            pricing_rule_id=pricing_rule.id,
            unit="USD/month",
            calculation_steps=steps,
            free_tier_applied=free_tier_status,
            warnings=warnings,
            resource_id=resource.get("name", "unknown")
        )
