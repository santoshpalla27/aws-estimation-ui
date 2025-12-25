"""
Async RDS adapter using normalized pricing tables.
NO JSON filtering - deterministic SKU matching.
"""
import logging
from typing import Dict, Any, List
from decimal import Decimal
from sqlalchemy import text

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


class AsyncRDSAdapterNormalized(AsyncPricingAdapter):
    """
    Async RDS adapter using normalized pricing_rds table.
    Deterministic SKU matching - no JSON filtering.
    """
    
    @property
    def required_attributes(self) -> List[str]:
        return ["instance_class", "engine", "region"]
    
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
        return "AmazonRDS"
    
    def validate(self, resource: Dict[str, Any]) -> None:
        """Validate RDS resource."""
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
    
    async def match_pricing(self, resource: Dict[str, Any]) -> PricingRule:
        """
        Match RDS instance to pricing using normalized table.
        Deterministic query - no JSON filtering.
        """
        instance_class = resource["instance_class"]
        engine = resource["engine"]
        region = resource["region"]
        deployment_option = resource.get("deployment_option", "Single-AZ")
        
        # Query normalized pricing_rds table
        query = text("""
            SELECT id, sku, price_per_unit, unit, 'USD' as currency
            FROM pricing_rds
            WHERE version_id = :version_id
              AND instance_class = :instance_class
              AND engine = :engine
              AND region = :region
              AND deployment_option = :deployment_option
            LIMIT 1
        """)
        
        result = await self.db.execute(query, {
            "version_id": self.pricing_version.id,
            "instance_class": instance_class,
            "engine": engine,
            "region": region,
            "deployment_option": deployment_option
        })
        
        row = result.fetchone()
        
        if row is None:
            raise PricingMatchError(
                f"No pricing found for RDS: instance_class={instance_class}, "
                f"engine={engine}, region={region}, deployment={deployment_option}"
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
        Calculate RDS cost using REQUIRED usage model.
        
        CRITICAL: usage_model is REQUIRED. No defaults.
        """
        if pricing_rule.unit != "Hrs":
            raise ValueError(f"Expected unit 'Hrs', got '{pricing_rule.unit}'")
        
        # CRITICAL: usage_model is REQUIRED (no defaults)
        from app.models.usage_model import UsageModel
        
        if "usage_model" not in resource:
            raise ValueError(
                "usage_model is REQUIRED for RDS cost calculation. "
                "Specify usage pattern (ALWAYS_ON, BUSINESS_HOURS, PARTIAL). "
                "No defaults allowed."
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
                description="Hourly RDS instance rate from normalized pricing",
                formula="price_per_unit",
                inputs={
                    "instance_class": resource["instance_class"],
                    "engine": resource["engine"],
                    "deployment_option": resource.get("deployment_option", "Single-AZ"),
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
        
        warnings = []
        
        # Add storage cost note if specified
        storage_gb = resource.get("allocated_storage", 0)
        if storage_gb > 0:
            steps.append(CalculationStep(
                description="Storage cost (not calculated)",
                formula="storage_gb * storage_rate",
                inputs={"storage_gb": storage_gb},
                result=Decimal("0"),
                unit="USD/month"
            ))
            warnings.append("Storage cost not included")
        
        return CostResult(
            monthly_cost=monthly_cost,
            pricing_rule_id=pricing_rule.id,
            unit="USD/month",
            calculation_steps=steps,
            free_tier_applied=FreeTierStatus.NOT_APPLICABLE,
            warnings=warnings,
            resource_id=resource.get("name", "unknown")
        )
