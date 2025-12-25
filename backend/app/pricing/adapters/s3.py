"""
S3 pricing adapter.
Calculates costs for S3 buckets.
"""
from typing import Dict
from decimal import Decimal
import logging

from app.pricing.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class S3Adapter(BaseAdapter):
    """S3 bucket pricing adapter."""
    
    def calculate_cost(self, resource: Dict) -> Dict:
        """
        Calculate monthly cost for an S3 bucket.
        
        Args:
            resource: Normalized resource with attributes:
                - storage_class: Storage class (STANDARD, INTELLIGENT_TIERING, etc.)
                - region: AWS region
                - estimated_storage_gb: Estimated storage in GB (default: 100)
                - estimated_requests: Estimated requests per month (default: 10000)
        
        Returns:
            Cost calculation result
        """
        warnings = []
        
        # Extract attributes
        storage_class = resource.get("storage_class", "STANDARD")
        region = resource.get("region", "us-east-1")
        estimated_storage_gb = resource.get("estimated_storage_gb", 100)
        estimated_requests = resource.get("estimated_requests", 10000)
        
        # Map storage class names
        storage_class_map = {
            "STANDARD": "General Purpose",
            "STANDARD_IA": "Infrequent Access",
            "ONEZONE_IA": "One Zone - Infrequent Access",
            "GLACIER": "Archive",
            "DEEP_ARCHIVE": "Deep Archive",
            "INTELLIGENT_TIERING": "Intelligent-Tiering"
        }
        
        storage_class_name = storage_class_map.get(storage_class, "General Purpose")
        
        # Calculate storage cost
        storage_pricing = self.query_pricing(
            service_code="AmazonS3",
            region_code=region,
            filters={
                "storageClass": storage_class_name,
                "volumeType": "Standard"
            }
        )
        
        storage_cost = Decimal("0")
        if storage_pricing:
            price_per_gb = storage_pricing.price_per_unit
            storage_cost = price_per_gb * Decimal(str(estimated_storage_gb))
        else:
            warnings.append(f"No storage pricing found for {storage_class}")
        
        # Calculate request cost (PUT/POST/LIST requests)
        request_pricing = self.query_pricing(
            service_code="AmazonS3",
            region_code=region,
            filters={
                "group": "S3-API-Tier1"  # PUT, COPY, POST, LIST requests
            }
        )
        
        request_cost = Decimal("0")
        if request_pricing:
            # Pricing is typically per 1000 requests
            price_per_1000 = request_pricing.price_per_unit
            request_cost = (Decimal(str(estimated_requests)) / Decimal("1000")) * price_per_1000
        else:
            warnings.append("No request pricing found")
        
        # Total cost
        monthly_cost = storage_cost + request_cost
        
        # Add warning about estimation
        warnings.append(
            f"S3 cost is estimated based on {estimated_storage_gb}GB storage "
            f"and {estimated_requests} requests per month"
        )
        
        pricing_details = {
            "storage_class": storage_class,
            "region": region,
            "storage_cost": float(storage_cost),
            "request_cost": float(request_cost),
            "estimated_storage_gb": estimated_storage_gb,
            "estimated_requests": estimated_requests
        }
        
        return self.format_cost_result(monthly_cost, pricing_details, warnings)
