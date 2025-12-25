"""
Service matcher.
Maps Terraform resources to pricing adapters.
"""
import logging
from typing import Dict, Optional, Type

from sqlalchemy.orm import Session
from app.models.models import PricingVersion
from app.pricing.adapters.base import BaseAdapter
from app.pricing.adapters.ec2 import EC2Adapter
from app.pricing.adapters.rds import RDSAdapter
from app.pricing.adapters.s3 import S3Adapter
from app.pricing.adapters.ebs import EBSAdapter
from app.pricing.adapters.lambda_adapter import LambdaAdapter

logger = logging.getLogger(__name__)


class ServiceMatcher:
    """
    Matches resources to pricing adapters.
    """
    
    # Map service codes to adapter classes
    ADAPTER_MAP = {
        "AmazonEC2": EC2Adapter,
        "AmazonRDS": RDSAdapter,
        "AmazonS3": S3Adapter,
        "AmazonEBS": EBSAdapter,
        "AWSLambda": LambdaAdapter,
    }
    
    def __init__(self, db: Session, pricing_version: PricingVersion):
        self.db = db
        self.pricing_version = pricing_version
        self.adapter_cache = {}
    
    def get_adapter(self, service_code: str) -> Optional[BaseAdapter]:
        """
        Get pricing adapter for a service.
        
        Args:
            service_code: AWS service code
        
        Returns:
            Adapter instance or None if unsupported
        """
        if service_code in self.adapter_cache:
            return self.adapter_cache[service_code]
        
        adapter_class = self.ADAPTER_MAP.get(service_code)
        
        if not adapter_class:
            logger.warning(f"No adapter for service: {service_code}")
            return None
        
        adapter = adapter_class(self.db, self.pricing_version)
        self.adapter_cache[service_code] = adapter
        
        return adapter
    
    def match_resource(self, resource: Dict) -> Optional[BaseAdapter]:
        """
        Match a normalized resource to its adapter.
        
        Args:
            resource: Normalized resource
        
        Returns:
            Adapter instance or None if unsupported
        """
        service_code = resource.get("service")
        
        if not service_code:
            logger.error("Resource missing service code")
            return None
        
        return self.get_adapter(service_code)
