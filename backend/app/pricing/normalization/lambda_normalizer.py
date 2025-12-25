"""
Lambda pricing normalizer.
Converts raw AWS Lambda pricing JSON into deterministic relational rows.
"""
import logging
from typing import Dict, List, Any
from sqlalchemy import text

from app.pricing.normalization.base import BasePricingNormalizer, NormalizationError

logger = logging.getLogger(__name__)


class LambdaPricingNormalizer(BasePricingNormalizer):
    """Lambda-specific pricing normalizer."""
    
    @property
    def service_code(self) -> str:
        return "AWSLambda"
    
    @property
    def required_attributes(self) -> List[str]:
        return ["group_description", "region"]
    
    async def normalize_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Lambda product."""
        attributes = product.get("attributes", {})
        
        normalized = {
            "sku": product.get("sku"),
            "group_description": attributes.get("groupDescription"),
            "region": self._normalize_region(attributes.get("location"))
        }
        
        self._validate_required_attributes(normalized)
        return normalized
    
    async def store_normalized_data(self, normalized_products: List[Dict[str, Any]]) -> int:
        """Store normalized Lambda pricing."""
        if not normalized_products:
            return 0
        
        insert_sql = """
            INSERT INTO pricing_lambda (
                version_id, sku, group_description, region,
                price_per_unit, unit, currency
            ) VALUES (
                :version_id, :sku, :group_description, :region,
                :price_per_unit, :unit, :currency
            )
            ON CONFLICT (version_id, group_description, region)
            DO UPDATE SET price_per_unit = EXCLUDED.price_per_unit
        """
        
        rows = []
        for product in normalized_products:
            rows.append({
                "version_id": self.version_id,
                "sku": product["sku"],
                "group_description": product["group_description"],
                "region": product["region"],
                "price_per_unit": product["price_per_unit"],
                "unit": product["unit"],
                "currency": product["currency"]
            })
        
        await self.db.execute(text(insert_sql), rows)
        await self.db.commit()
        
        logger.info(f"Inserted {len(rows)} Lambda pricing rows")
        return len(rows)
    
    def _normalize_region(self, location: str) -> str:
        """Convert AWS location to region code."""
        location_map = {
            "US East (N. Virginia)": "us-east-1",
            "US East (Ohio)": "us-east-2",
            "US West (N. California)": "us-west-1",
            "US West (Oregon)": "us-west-2",
            "EU (Ireland)": "eu-west-1",
            "EU (London)": "eu-west-2",
            "EU (Paris)": "eu-west-3",
            "EU (Frankfurt)": "eu-central-1",
            "Asia Pacific (Mumbai)": "ap-south-1",
            "Asia Pacific (Singapore)": "ap-southeast-1",
            "Asia Pacific (Sydney)": "ap-southeast-2",
            "Asia Pacific (Tokyo)": "ap-northeast-1",
            "Asia Pacific (Seoul)": "ap-northeast-2",
            "Canada (Central)": "ca-central-1",
            "South America (São Paulo)": "sa-east-1"
        }
        
        region = location_map.get(location)
        if not region:
            raise NormalizationError(f"Unknown location: {location}")
        return region
