"""
Async S3 adapter using normalized pricing tables.
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


class AsyncS3AdapterNormalized(AsyncPricingAdapter):
    """
    Async S3 adapter using normalized pricing_s3 table.
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
        return "AmazonS3"
    
    def validate(self, resource: Dict[str, Any]) -> None:
        """Validate S3 resource."""
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
        Match S3 storage to pricing using normalized table.
        Deterministic query - no JSON filtering.
        """
        region = resource["region"]
        storage_class = resource.get("storage_class", "STANDARD")
        volume_type = resource.get("volume_type", "Standard")
        
        # Query normalized pricing_s3 table
        query = text("""
            SELECT id, sku, price_per_unit, unit, 'USD' as currency
            FROM pricing_s3
            WHERE version_id = :version_id
              AND region = :region
              AND storage_class = :storage_class
              AND volume_type = :volume_type
            LIMIT 1
        """)
        
        result = await self.db.execute(query, {
            "version_id": self.pricing_version.id,
            "region": region,
            "storage_class": storage_class,
            "volume_type": volume_type
        })
        
        row = result.fetchone()
        
        if row is None:
            raise PricingMatchError(
                f"No pricing found for S3: region={region}, "
                f"storage_class={storage_class}, volume_type={volume_type}"
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
        """Calculate S3 cost."""
        # S3 pricing is per GB-month
        storage_gb = Decimal(str(resource.get("estimated_storage_gb", 100)))
        price_per_gb = pricing_rule.price_per_unit
        monthly_cost = storage_gb * price_per_gb
        
        steps = [
            CalculationStep(
                description="S3 storage rate from normalized pricing",
                formula="price_per_unit",
                inputs={
                    "storage_class": resource.get("storage_class", "STANDARD"),
                    "sku": pricing_rule.attributes.get("sku")
                },
                result=price_per_gb,
                unit="USD/GB-month"
            ),
            CalculationStep(
                description="Monthly storage cost",
                formula="storage_gb * price_per_gb",
                inputs={
                    "storage_gb": float(storage_gb),
                    "price_per_gb": float(price_per_gb)
                },
                result=monthly_cost,
                unit="USD/month"
            )
        ]
        
        warnings = []
        if "estimated_storage_gb" in resource:
            warnings.append("Using estimated storage size - actual may vary")
        
        return CostResult(
            monthly_cost=monthly_cost,
            pricing_rule_id=pricing_rule.id,
            unit="USD/month",
            calculation_steps=steps,
            free_tier_applied=FreeTierStatus.NOT_APPLICABLE,
            warnings=warnings,
            resource_id=resource.get("name", "unknown")
        )
