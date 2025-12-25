"""
Async service matcher.
Maps Terraform resources to async pricing adapters.
"""
import logging
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import PricingVersion
from app.pricing.async_adapters.base import AsyncPricingAdapter
from app.pricing.async_adapters.ec2_normalized import AsyncEC2AdapterNormalized
from app.pricing.async_adapters.rds_normalized import AsyncRDSAdapterNormalized
from app.pricing.async_adapters.s3_normalized import AsyncS3AdapterNormalized
from app.pricing.async_adapters.ebs_normalized import AsyncEBSAdapterNormalized
from app.pricing.async_adapters.lambda_normalized import AsyncLambdaAdapterNormalized

logger = logging.getLogger(__name__)


class AsyncServiceMatcher:
    """
    Matches resources to async pricing adapters.
    """
    
    # Map service codes to async adapter classes (ALL NORMALIZED)
    ADAPTER_MAP = {
        "AmazonEC2": AsyncEC2AdapterNormalized,
        "AmazonRDS": AsyncRDSAdapterNormalized,
        "AmazonS3": AsyncS3AdapterNormalized,
        "AmazonEBS": AsyncEBSAdapterNormalized,
        "AWSLambda": AsyncLambdaAdapterNormalized,
    }
    
    def __init__(self, db: AsyncSession, pricing_version: PricingVersion):
        self.db = db
        self.pricing_version = pricing_version
        self.adapter_cache = {}
    
    async def get_adapter(self, service_code: str) -> Optional[AsyncPricingAdapter]:
        """
        Get async pricing adapter for a service.
        
        Args:
            service_code: AWS service code
        
        Returns:
            Async adapter instance or None if unsupported
        """
        if service_code in self.adapter_cache:
            return self.adapter_cache[service_code]
        
        adapter_class = self.ADAPTER_MAP.get(service_code)
        
        if not adapter_class:
            logger.warning(f"No async adapter for service: {service_code}")
            return None
        
        adapter = adapter_class(self.db, self.pricing_version)
        self.adapter_cache[service_code] = adapter
        
        return adapter
    
    async def match_resource_async(self, resource: Dict) -> Optional[AsyncPricingAdapter]:
        """
        Match a normalized resource to its async adapter.
        
        Args:
            resource: Normalized resource
        
        Returns:
            Async adapter instance or None if unsupported
        """
        service_code = resource.get("service")
        
        if not service_code:
            logger.error("Resource missing service code")
            return None
        
        return await self.get_adapter(service_code)
