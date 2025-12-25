"""
Updated async EC2 adapter using normalized pricing tables.
NO JSON filtering - deterministic SKU matching.
"""
import logging
from typing import Dict, Any, List
from decimal import Decimal
from sqlalchemy import select, text

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


class AsyncEC2AdapterNormalized(AsyncPricingAdapter):
    """
    Async EC2 adapter using normalized pricing_ec2 table.
    Deterministic SKU matching - no JSON filtering.
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
        """Validate EC2 resource."""
        missing = []
        for attr in self.required_attributes:
            if attr not in resource:
                missing.append(attr)
        
        if missing:
            raise ValidationError(
                f"Missing required attributes for {self.service_code}: {', '.join(missing)}"
            )
        
        region = resource.get("region")
        if region not in self.supported_regions:
            raise ValidationError(
                f"Region '{region}' not supported for {self.service_code}"
            )
        
        instance_type = resource.get("instance_type")
        if not isinstance(instance_type, str) or "." not in instance_type:
            raise ValidationError(
                f"Invalid instance_type format: '{instance_type}'"
            )
    
    async def match_pricing(self, resource: Dict[str, Any]) -> PricingRule:
        """
        Match EC2 instance to pricing using normalized table.
        Deterministic query - no JSON filtering.
        """
        instance_type = resource["instance_type"]
        region = resource["region"]
        operating_system = resource.get("operating_system", "Linux")
        tenancy = resource.get("tenancy", "Shared")
        capacity_status = resource.get("capacity_status", "Used")
        
        # Query normalized pricing_ec2 table
        query = text("""
            SELECT id, sku, price_per_unit, unit, 'USD' as currency
            FROM pricing_ec2
            WHERE version_id = :version_id
              AND instance_type = :instance_type
              AND region = :region
              AND operating_system = :operating_system
              AND tenancy = :tenancy
              AND capacity_status = :capacity_status
            LIMIT 1
        """)
        
        result = await self.db.execute(query, {
            "version_id": self.pricing_version.id,
            "instance_type": instance_type,
            "region": region,
            "operating_system": operating_system,
            "tenancy": tenancy,
            "capacity_status": capacity_status
        })
        
        row = result.fetchone()
        
        if row is None:
            raise PricingMatchError(
                f"No pricing found for EC2: instance_type={instance_type}, "
                f"region={region}, os={operating_system}, tenancy={tenancy}"
            )
        
        return PricingRule(
            id=row.id,
            service_code=self.service_code,
            region_code=region,
            price_per_unit=Decimal(str(row.price_per_unit)),
            unit=row.unit,
            currency=row.currency,
            attributes={"sku": row.sku}
        )
    
    def calculate(self, resource: Dict[str, Any], pricing_rule: PricingRule) -> CostResult:
        """
        Calculate EC2 cost using REQUIRED usage model.
        
        CRITICAL: usage_model is REQUIRED. No defaults.
        This prevents hardcoded time assumptions.
        """
        if pricing_rule.unit != "Hrs":
            raise ValueError(f"Expected unit 'Hrs', got '{pricing_rule.unit}'")
        
        # CRITICAL: usage_model is REQUIRED (no defaults)
        from app.models.usage_model import UsageModel
        
        if "usage_model" not in resource:
            raise ValueError(
                "usage_model is REQUIRED for EC2 cost calculation. "
                "Specify usage pattern (ALWAYS_ON, BUSINESS_HOURS, PARTIAL, SPOT). "
                "No defaults allowed to prevent hardcoded time assumptions."
            )
        
        usage_model = resource["usage_model"]
        if not isinstance(usage_model, UsageModel):
            raise ValueError(
                f"usage_model must be UsageModel instance, got {type(usage_model)}"
            )
        
        hourly_rate = pricing_rule.price_per_unit
        hours_per_month = usage_model.get_effective_hours()
        monthly_cost = hourly_rate * hours_per_month
        
        steps = [
            CalculationStep(
                description="Hourly instance rate from normalized pricing",
                formula="price_per_unit",
                inputs={
                    "instance_type": resource["instance_type"],
                    "region": resource["region"],
                    "operating_system": resource.get("operating_system", "Linux"),
                    "tenancy": resource.get("tenancy", "Shared"),
                    "sku": pricing_rule.attributes.get("sku")
                },
                result=hourly_rate,
                unit="USD/hour"
            ),
            CalculationStep(
                description=f"Usage model: {usage_model.pattern.value} (EXPLICIT)",
                formula="get_effective_hours()",
                inputs={
                    "pattern": usage_model.pattern.value,
                    "hours": float(hours_per_month)
                },
                result=hours_per_month,
                unit="hours/month"
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
        
        free_tier_status = FreeTierStatus.NOT_APPLICABLE
        warnings = []
        
        if resource["instance_type"] in ["t2.micro", "t3.micro"]:
            free_tier_status = FreeTierStatus.EXCEEDED
            warnings.append("Free tier eligible but not calculated")
        
        if usage_model.pattern.value != "always_on":
            warnings.append(f"Using {usage_model.pattern.value} usage pattern")
        
        return CostResult(
            monthly_cost=monthly_cost,
            pricing_rule_id=pricing_rule.id,
            unit="USD/month",
            calculation_steps=steps,
            free_tier_applied=free_tier_status,
            warnings=warnings,
            resource_id=resource.get("name", "unknown")
        )
