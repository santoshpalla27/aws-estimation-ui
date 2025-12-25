"""
Async Lambda adapter using normalized pricing tables.
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


class AsyncLambdaAdapterNormalized(AsyncPricingAdapter):
    """
    Async Lambda adapter using normalized pricing_lambda table.
    Deterministic SKU matching - no JSON filtering.
    """
    
    @property
    def required_attributes(self) -> List[str]:
        return ["region"]
    
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
        return "AWSLambda"
    
    def validate(self, resource: Dict[str, Any]) -> None:
        """Validate Lambda resource."""
        region = resource.get("region")
        if not region:
            raise ValidationError(
                f"Missing required attribute 'region' for {self.service_code}"
            )
        
        if region not in self.supported_regions:
            raise ValidationError(
                f"Region '{region}' not supported for {self.service_code}"
            )
    
    async def match_pricing(self, resource: Dict[str, Any]) -> PricingRule:
        """
        Match Lambda function to pricing using normalized table.
        Deterministic query - no JSON filtering.
        """
        region = resource["region"]
        group_description = "AWS Lambda"  # Standard group
        
        # Query normalized pricing_lambda table for request pricing
        query = text("""
            SELECT id, sku, price_per_unit, unit, 'USD' as currency
            FROM pricing_lambda
            WHERE version_id = :version_id
              AND region = :region
              AND group_description = :group_description
            LIMIT 1
        """)
        
        result = await self.db.execute(query, {
            "version_id": self.pricing_version.id,
            "region": region,
            "group_description": group_description
        })
        
        row = result.fetchone()
        
        if row is None:
            raise PricingMatchError(
                f"No pricing found for Lambda: region={region}"
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
        """Calculate Lambda cost."""
        # Lambda pricing: requests + duration (GB-seconds)
        invocations = Decimal(str(resource.get("estimated_invocations", 100000)))
        duration_ms = Decimal(str(resource.get("estimated_duration_ms", 1000)))
        memory_mb = Decimal(str(resource.get("memory_size", 128)))
        
        # Request cost
        request_rate = pricing_rule.price_per_unit  # Per million requests
        request_cost = (invocations / Decimal("1000000")) * request_rate
        
        # Duration cost (simplified - would need separate pricing query)
        memory_gb = memory_mb / Decimal("1024")
        duration_seconds = duration_ms / Decimal("1000")
        gb_seconds = invocations * memory_gb * duration_seconds
        duration_rate = Decimal("0.0000166667")  # Approximate
        duration_cost = gb_seconds * duration_rate
        
        monthly_cost = request_cost + duration_cost
        
        # Free tier: 1M requests + 400,000 GB-seconds
        free_tier_status = FreeTierStatus.NOT_APPLICABLE
        warnings = []
        
        if invocations <= 1000000 and gb_seconds <= 400000:
            free_tier_status = FreeTierStatus.WITHIN_FREE_TIER
            monthly_cost = Decimal("0")
            warnings.append("Within free tier limits")
        elif invocations > 1000000 or gb_seconds > 400000:
            free_tier_status = FreeTierStatus.EXCEEDED
            warnings.append("Exceeds free tier - using estimated pricing")
        
        steps = [
            CalculationStep(
                description="Lambda request rate from normalized pricing",
                formula="price_per_unit",
                inputs={"sku": pricing_rule.attributes.get("sku")},
                result=request_rate,
                unit="USD/million requests"
            ),
            CalculationStep(
                description="Request cost",
                formula="(invocations / 1M) * request_rate",
                inputs={
                    "invocations": float(invocations),
                    "request_rate": float(request_rate)
                },
                result=request_cost,
                unit="USD/month"
            ),
            CalculationStep(
                description="Duration cost (estimated)",
                formula="gb_seconds * duration_rate",
                inputs={
                    "gb_seconds": float(gb_seconds),
                    "duration_rate": float(duration_rate)
                },
                result=duration_cost,
                unit="USD/month"
            )
        ]
        
        warnings.append("Using estimated invocations and duration")
        
        return CostResult(
            monthly_cost=monthly_cost,
            pricing_rule_id=pricing_rule.id,
            unit="USD/month",
            calculation_steps=steps,
            free_tier_applied=free_tier_status,
            warnings=warnings,
            resource_id=resource.get("name", "unknown")
        )
