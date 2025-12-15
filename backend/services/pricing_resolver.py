"""
Pricing Resolver - Hard-Fail on Missing Pricing

This module resolves pricing keys to actual values with STRICT enforcement.

CRITICAL RULES:
- NO DEFAULTS
- NO FALLBACKS  
- NO SILENT FAILURES
- FAIL LOUDLY ON MISSING KEYS

If pricing cannot be resolved, estimation MUST abort.
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
import structlog

from exceptions.pricing_errors import PricingResolutionError

logger = structlog.get_logger()


class PricingResolutionLog:
    """Log entry for a single pricing resolution"""
    
    def __init__(self, key: str, value: Any, path: List[str]):
        self.key = key
        self.value = value
        self.path = path
        self.resolved = True
    
    def to_dict(self) -> dict:
        return {
            'key': self.key,
            'value': float(self.value) if isinstance(self.value, (int, float, Decimal)) else self.value,
            'path': '.'.join(self.path),
            'resolved': self.resolved
        }


class PricingResolver:
    """
    Resolves pricing keys to actual values
    
    STRICT MODE ONLY:
    - Missing key → PricingResolutionError
    - Invalid path → PricingResolutionError
    - No fallback values
    - No default values
    
    Usage:
        resolver = PricingResolver(pricing_data, "AmazonS3", "us-east-1")
        price = resolver.resolve("storage.standard")  # Returns 0.023 or raises
    """
    
    def __init__(self, pricing_data: Dict[str, Any], service: str, region: str):
        """
        Initialize pricing resolver
        
        Args:
            pricing_data: Pricing data dictionary (from pricing_data.yaml)
            service: Service name (e.g., "AmazonS3")
            region: AWS region (e.g., "us-east-1")
        """
        self.pricing_data = pricing_data
        self.service = service
        self.region = region
        self.resolution_log: List[PricingResolutionLog] = []
        
        logger.info(
            "pricing_resolver_initialized",
            service=service,
            region=region,
            has_pricing_data=bool(pricing_data)
        )
    
    def resolve(self, key: str) -> Decimal:
        """
        Resolve a pricing key to its value
        
        Args:
            key: Pricing key (e.g., "storage.standard" or "instances.t3.micro")
        
        Returns:
            Pricing value as Decimal for precision
        
        Raises:
            PricingResolutionError: If key cannot be resolved (NO FALLBACK)
        
        Example:
            >>> resolver.resolve("storage.standard")
            Decimal('0.023')
        """
        # Navigate nested dictionary
        parts = key.split('.')
        current = self.pricing_data
        path = []
        
        for i, part in enumerate(parts):
            path.append(part)
            
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    # HARD FAIL - Key not found
                    available_keys = list(current.keys()) if isinstance(current, dict) else []
                    
                    logger.error(
                        "pricing_resolution_failed",
                        service=self.service,
                        region=self.region,
                        key=key,
                        failed_at_part=part,
                        path='.'.join(path[:-1]),
                        available_keys=available_keys[:20]  # Limit for logging
                    )
                    
                    raise PricingResolutionError(
                        service=self.service,
                        key=key,
                        region=self.region,
                        available_keys=available_keys
                    )
            else:
                # Tried to navigate into non-dict
                logger.error(
                    "pricing_resolution_invalid_path",
                    service=self.service,
                    region=self.region,
                    key=key,
                    failed_at_part=part,
                    current_type=type(current).__name__
                )
                
                raise PricingResolutionError(
                    service=self.service,
                    key=key,
                    region=self.region
                )
        
        # Convert to Decimal for financial precision
        try:
            value = Decimal(str(current))
        except (ValueError, TypeError) as e:
            logger.error(
                "pricing_value_not_numeric",
                service=self.service,
                region=self.region,
                key=key,
                value=current,
                value_type=type(current).__name__,
                error=str(e)
            )
            
            raise PricingResolutionError(
                service=self.service,
                key=key,
                region=self.region
            )
        
        # Log successful resolution
        log_entry = PricingResolutionLog(key, value, path)
        self.resolution_log.append(log_entry)
        
        logger.debug(
            "pricing_resolved",
            service=self.service,
            region=self.region,
            key=key,
            value=float(value)
        )
        
        return value
    
    def resolve_dict(self, key: str) -> Dict[str, Any]:
        """
        Resolve a pricing key to a dictionary (for nested structures)
        
        Args:
            key: Pricing key
        
        Returns:
            Dictionary value
        
        Raises:
            PricingResolutionError: If key cannot be resolved or is not a dict
        """
        parts = key.split('.')
        current = self.pricing_data
        path = []
        
        for part in parts:
            path.append(part)
            
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                available_keys = list(current.keys()) if isinstance(current, dict) else []
                raise PricingResolutionError(
                    service=self.service,
                    key=key,
                    region=self.region,
                    available_keys=available_keys
                )
        
        if not isinstance(current, dict):
            raise PricingResolutionError(
                service=self.service,
                key=key,
                region=self.region
            )
        
        # Log resolution
        log_entry = PricingResolutionLog(key, f"<dict with {len(current)} keys>", path)
        self.resolution_log.append(log_entry)
        
        return current
    
    def get_resolution_log(self) -> List[Dict[str, Any]]:
        """
        Get log of all pricing resolutions for audit trail
        
        Returns:
            List of resolution log entries
        """
        return [entry.to_dict() for entry in self.resolution_log]
    
    def get_resolution_summary(self) -> Dict[str, Any]:
        """
        Get summary of pricing resolutions
        
        Returns:
            Summary dictionary with counts and keys
        """
        return {
            'service': self.service,
            'region': self.region,
            'total_resolutions': len(self.resolution_log),
            'keys_resolved': [entry.key for entry in self.resolution_log],
            'all_successful': all(entry.resolved for entry in self.resolution_log)
        }
