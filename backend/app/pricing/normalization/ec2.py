"""
EC2 pricing normalizer.
Converts raw AWS EC2 pricing JSON into deterministic relational rows.
"""
import logging
from typing import Dict, List, Any
from decimal import Decimal
from sqlalchemy import text

from app.pricing.normalization.base import BasePricingNormalizer, NormalizationError

logger = logging.getLogger(__name__)


class EC2PricingNormalizer(BasePricingNormalizer):
    """
    EC2-specific pricing normalizer.
    
    Extracts:
    - instance_type (e.g., t3.micro)
    - operating_system (Linux, Windows, RHEL, SUSE)
    - tenancy (Shared, Dedicated, Host)
    - capacity_status (Used, UnusedCapacityReservation)
    - pre_installed_sw (NA, SQL Web, SQL Std, SQL Ent)
    - region
    """
    
    @property
    def service_code(self) -> str:
        return "AmazonEC2"
    
    @property
    def required_attributes(self) -> List[str]:
        return [
            "instance_type",
            "operating_system",
            "tenancy",
            "region"
        ]
    
    async def normalize_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize EC2 product.
        
        Args:
            product: Raw product from AWS pricing
        
        Returns:
            Normalized product dictionary
        
        Raises:
            NormalizationError: If required attributes missing
        """
        attributes = product.get("attributes", {})
        
        # Extract required attributes
        normalized = {
            "sku": product.get("sku"),
            "instance_type": attributes.get("instanceType"),
            "operating_system": attributes.get("operatingSystem"),
            "tenancy": attributes.get("tenancy"),
            "capacity_status": attributes.get("capacitystatus", "Used"),
            "pre_installed_sw": attributes.get("preInstalledSw", "NA"),
            "region": self._normalize_region(attributes.get("location"))
        }
        
        # Validate required attributes
        self._validate_required_attributes(normalized)
        
        return normalized
    
    async def store_normalized_data(self, normalized_products: List[Dict[str, Any]]) -> int:
        """
        Store normalized EC2 pricing in pricing_ec2 table.
        
        Args:
            normalized_products: List of normalized products
        
        Returns:
            Number of rows inserted
        """
        if not normalized_products:
            return 0
        
        # Build bulk insert
        insert_sql = """
            INSERT INTO pricing_ec2 (
                version_id, sku, instance_type, operating_system, tenancy,
                capacity_status, pre_installed_sw, region,
                price_per_unit, unit, currency
            ) VALUES (
                :version_id, :sku, :instance_type, :operating_system, :tenancy,
                :capacity_status, :pre_installed_sw, :region,
                :price_per_unit, :unit, :currency
            )
            ON CONFLICT (version_id, instance_type, operating_system, tenancy, region, capacity_status)
            DO UPDATE SET
                price_per_unit = EXCLUDED.price_per_unit,
                unit = EXCLUDED.unit
        """
        
        # Prepare data
        rows = []
        for product in normalized_products:
            rows.append({
                "version_id": self.version_id,
                "sku": product["sku"],
                "instance_type": product["instance_type"],
                "operating_system": product["operating_system"],
                "tenancy": product["tenancy"],
                "capacity_status": product.get("capacity_status", "Used"),
                "pre_installed_sw": product.get("pre_installed_sw", "NA"),
                "region": product["region"],
                "price_per_unit": product["price_per_unit"],
                "unit": product["unit"],
                "currency": product["currency"]
            })
        
        # Execute bulk insert
        await self.db.execute(text(insert_sql), rows)
        await self.db.commit()
        
        logger.info(f"Inserted {len(rows)} EC2 pricing rows")
        return len(rows)
    
    def _normalize_region(self, location: str) -> str:
        """
        Convert AWS location to region code.
        
        Args:
            location: AWS location string (e.g., "US East (N. Virginia)")
        
        Returns:
            Region code (e.g., "us-east-1")
        """
        # Mapping of location strings to region codes
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
            "Asia Pacific (Osaka)": "ap-northeast-3",
            "Canada (Central)": "ca-central-1",
            "South America (São Paulo)": "sa-east-1"
        }
        
        region = location_map.get(location)
        if not region:
            raise NormalizationError(f"Unknown location: {location}")
        
        return region
