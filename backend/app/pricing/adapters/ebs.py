"""
EBS pricing adapter.
Calculates costs for EBS volumes.
"""
from typing import Dict
from decimal import Decimal
import logging

from app.pricing.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class EBSAdapter(BaseAdapter):
    """EBS volume pricing adapter."""
    
    def calculate_cost(self, resource: Dict) -> Dict:
        """
        Calculate monthly cost for an EBS volume.
        
        Args:
            resource: Normalized resource with attributes:
                - volume_type: Volume type (gp2, gp3, io1, io2, st1, sc1)
                - size: Volume size in GB
                - region: AWS region
                - iops: Provisioned IOPS (for io1/io2)
        
        Returns:
            Cost calculation result
        """
        warnings = []
        
        # Extract attributes
        volume_type = resource.get("volume_type", "gp2")
        size = resource.get("size", 100)
        region = resource.get("region", "us-east-1")
        iops = resource.get("iops", 0)
        
        # Map volume type names
        volume_type_map = {
            "gp2": "General Purpose",
            "gp3": "General Purpose",
            "io1": "Provisioned IOPS",
            "io2": "Provisioned IOPS",
            "st1": "Throughput Optimized HDD",
            "sc1": "Cold HDD",
            "standard": "Magnetic"
        }
        
        volume_api_name = volume_type_map.get(volume_type, "General Purpose")
        
        # Calculate storage cost
        storage_pricing = self.query_pricing(
            service_code="AmazonEC2",
            region_code=region,
            filters={
                "volumeApiName": volume_type,
                "productFamily": "Storage"
            }
        )
        
        if not storage_pricing:
            # Try with volume type name
            storage_pricing = self.query_pricing(
                service_code="AmazonEC2",
                region_code=region,
                filters={
                    "volumeType": volume_api_name,
                    "productFamily": "Storage"
                }
            )
        
        storage_cost = Decimal("0")
        if storage_pricing:
            price_per_gb_month = storage_pricing.price_per_unit
            storage_cost = price_per_gb_month * Decimal(str(size))
        else:
            warnings.append(f"No storage pricing found for {volume_type}")
        
        # Calculate IOPS cost for io1/io2
        iops_cost = Decimal("0")
        if volume_type in ["io1", "io2"] and iops > 0:
            iops_pricing = self.query_pricing(
                service_code="AmazonEC2",
                region_code=region,
                filters={
                    "volumeApiName": volume_type,
                    "group": "EBS IOPS"
                }
            )
            
            if iops_pricing:
                price_per_iops = iops_pricing.price_per_unit
                iops_cost = price_per_iops * Decimal(str(iops))
            else:
                warnings.append(f"No IOPS pricing found for {volume_type}")
        
        # Total cost
        monthly_cost = storage_cost + iops_cost
        
        pricing_details = {
            "volume_type": volume_type,
            "size_gb": size,
            "region": region,
            "storage_cost": float(storage_cost),
            "iops_cost": float(iops_cost),
            "provisioned_iops": iops if volume_type in ["io1", "io2"] else None
        }
        
        return self.format_cost_result(monthly_cost, pricing_details, warnings)
