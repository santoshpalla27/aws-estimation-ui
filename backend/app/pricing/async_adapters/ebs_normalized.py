"""
Async EBS adapter using normalized pricing tables.
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


class AsyncEBSAdapterNormalized(AsyncPricingAdapter):
    """
    Async EBS adapter using normalized pricing_ebs table.
    Deterministic SKU matching - no JSON filtering.
    """
    
    @property
    def required_attributes(self) -> List[str]:
        return ["volume_type", "region"]
    
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
        return "AmazonEBS"
    
    def validate(self, resource: Dict[str, Any]) -> None:
        """Validate EBS resource."""
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
        Match EBS volume to pricing using normalized table.
        Deterministic query - no JSON filtering.
        """
        volume_type = resource["volume_type"]
        region = resource["region"]
        
        # Query normalized pricing_ebs table
        query = text("""
            SELECT id, sku, price_per_unit, unit, 'USD' as currency
            FROM pricing_ebs
            WHERE version_id = :version_id
              AND volume_type = :volume_type
              AND region = :region
            LIMIT 1
        """)
        
        result = await self.db.execute(query, {
            "version_id": self.pricing_version.id,
            "volume_type": volume_type,
            "region": region
        })
        
        row = result.fetchone()
        
        if row is None:
            raise PricingMatchError(
                f"No pricing found for EBS: volume_type={volume_type}, region={region}"
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
        """Calculate EBS cost."""
        # EBS pricing is per GB-month
        size_gb = Decimal(str(resource.get("size", 100)))
        price_per_gb = pricing_rule.price_per_unit
        monthly_cost = size_gb * price_per_gb
        
        steps = [
            CalculationStep(
                description="EBS storage rate from normalized pricing",
                formula="price_per_unit",
                inputs={
                    "volume_type": resource["volume_type"],
                    "sku": pricing_rule.attributes.get("sku")
                },
                result=price_per_gb,
                unit="USD/GB-month"
            ),
            CalculationStep(
                description="Monthly storage cost",
                formula="size_gb * price_per_gb",
                inputs={
                    "size_gb": float(size_gb),
                    "price_per_gb": float(price_per_gb)
                },
                result=monthly_cost,
                unit="USD/month"
            )
        ]
        
        # Add IOPS cost if applicable
        iops = resource.get("iops", 0)
        if iops > 0 and resource["volume_type"] in ["io1", "io2"]:
            steps.append(CalculationStep(
                description="Provisioned IOPS cost (not calculated)",
                formula="iops * iops_rate",
                inputs={"iops": iops},
                result=Decimal("0"),
                unit="USD/month"
            ))
        
        return CostResult(
            monthly_cost=monthly_cost,
            pricing_rule_id=pricing_rule.id,
            unit="USD/month",
            calculation_steps=steps,
            free_tier_applied=FreeTierStatus.NOT_APPLICABLE,
            warnings=["IOPS cost not included"] if iops > 0 else [],
            resource_id=resource.get("name", "unknown")
        )
