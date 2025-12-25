"""
Lambda pricing adapter.
Calculates costs for Lambda functions.
"""
from typing import Dict
from decimal import Decimal
import logging

from app.pricing.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class LambdaAdapter(BaseAdapter):
    """Lambda function pricing adapter."""
    
    def calculate_cost(self, resource: Dict) -> Dict:
        """
        Calculate monthly cost for a Lambda function.
        
        Args:
            resource: Normalized resource with attributes:
                - memory_size: Memory in MB (default: 128)
                - region: AWS region
                - estimated_invocations: Estimated invocations per month (default: 100000)
                - estimated_duration_ms: Estimated duration per invocation in ms (default: 1000)
        
        Returns:
            Cost calculation result
        """
        warnings = []
        
        # Extract attributes
        memory_size = resource.get("memory_size", 128)
        region = resource.get("region", "us-east-1")
        estimated_invocations = resource.get("estimated_invocations", 100000)
        estimated_duration_ms = resource.get("estimated_duration_ms", 1000)
        
        # Calculate request cost
        request_pricing = self.query_pricing(
            service_code="AWSLambda",
            region_code=region,
            filters={
                "group": "AWS-Lambda-Requests"
            }
        )
        
        request_cost = Decimal("0")
        if request_pricing:
            # Pricing is per 1M requests
            price_per_million = request_pricing.price_per_unit
            request_cost = (Decimal(str(estimated_invocations)) / Decimal("1000000")) * price_per_million
        else:
            warnings.append("No request pricing found")
        
        # Calculate duration cost (GB-seconds)
        duration_pricing = self.query_pricing(
            service_code="AWSLambda",
            region_code=region,
            filters={
                "group": "AWS-Lambda-Duration"
            }
        )
        
        duration_cost = Decimal("0")
        if duration_pricing:
            # Convert to GB-seconds
            gb = Decimal(str(memory_size)) / Decimal("1024")  # MB to GB
            seconds = Decimal(str(estimated_duration_ms)) / Decimal("1000")  # ms to seconds
            gb_seconds_per_invocation = gb * seconds
            total_gb_seconds = gb_seconds_per_invocation * Decimal(str(estimated_invocations))
            
            # Pricing is per GB-second
            price_per_gb_second = duration_pricing.price_per_unit
            duration_cost = total_gb_seconds * price_per_gb_second
        else:
            warnings.append("No duration pricing found")
        
        # Apply free tier (1M requests and 400,000 GB-seconds per month)
        free_tier_requests = Decimal("1000000")
        free_tier_gb_seconds = Decimal("400000")
        
        # Adjust for free tier
        if estimated_invocations <= free_tier_requests:
            request_cost = Decimal("0")
            warnings.append("Within free tier for requests")
        
        # Total cost
        monthly_cost = request_cost + duration_cost
        
        # Add warning about estimation
        warnings.append(
            f"Lambda cost is estimated based on {estimated_invocations} invocations "
            f"and {estimated_duration_ms}ms average duration"
        )
        
        pricing_details = {
            "memory_size_mb": memory_size,
            "region": region,
            "request_cost": float(request_cost),
            "duration_cost": float(duration_cost),
            "estimated_invocations": estimated_invocations,
            "estimated_duration_ms": estimated_duration_ms
        }
        
        return self.format_cost_result(monthly_cost, pricing_details, warnings)
