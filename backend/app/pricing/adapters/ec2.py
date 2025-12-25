"""
EC2 pricing adapter.
Calculates costs for EC2 instances.
"""
from typing import Dict
from decimal import Decimal
import logging

from app.pricing.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class EC2Adapter(BaseAdapter):
    """EC2 instance pricing adapter."""
    
    def calculate_cost(self, resource: Dict) -> Dict:
        """
        Calculate monthly cost for an EC2 instance.
        
        Args:
            resource: Normalized resource with attributes:
                - instance_type: EC2 instance type (e.g., 't3.micro')
                - region: AWS region
                - tenancy: Tenancy (default, dedicated, host)
                - operating_system: OS (Linux, Windows, etc.)
        
        Returns:
            Cost calculation result
        """
        warnings = []
        
        # Extract attributes
        instance_type = resource.get("instance_type")
        region = resource.get("region", "us-east-1")
        tenancy = resource.get("tenancy", "Shared")
        operating_system = resource.get("operating_system", "Linux")
        
        if not instance_type:
            return self.format_cost_result(
                Decimal("0"),
                {"error": "Missing instance_type"},
                ["Missing instance_type attribute"]
            )
        
        # Map Terraform values to AWS pricing attributes
        tenancy_map = {
            "default": "Shared",
            "dedicated": "Dedicated",
            "host": "Host"
        }
        tenancy = tenancy_map.get(tenancy, "Shared")
        
        # Query pricing
        pricing = self.query_pricing(
            service_code="AmazonEC2",
            region_code=region,
            filters={
                "instanceType": instance_type,
                "tenancy": tenancy,
                "operatingSystem": operating_system,
                "preInstalledSw": "NA",
                "capacitystatus": "Used"
            }
        )
        
        if not pricing:
            # Try without some filters
            pricing = self.query_pricing(
                service_code="AmazonEC2",
                region_code=region,
                filters={
                    "instanceType": instance_type,
                    "tenancy": tenancy,
                    "operatingSystem": operating_system
                }
            )
        
        if not pricing:
            warnings.append(f"No pricing found for {instance_type} in {region}")
            return self.format_cost_result(
                Decimal("0"),
                {"error": "Pricing not found"},
                warnings
            )
        
        # Calculate monthly cost
        price_per_hour = pricing.price_per_unit
        monthly_cost = price_per_hour * self.hours_per_month()
        
        pricing_details = {
            "instance_type": instance_type,
            "region": region,
            "operating_system": operating_system,
            "tenancy": tenancy,
            "price_per_hour": float(price_per_hour),
            "hours_per_month": float(self.hours_per_month()),
            "sku": pricing.sku,
            "unit": pricing.unit
        }
        
        return self.format_cost_result(monthly_cost, pricing_details, warnings)
