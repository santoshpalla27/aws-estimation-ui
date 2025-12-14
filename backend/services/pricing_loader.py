"""
Pricing Loader - Load and cache pricing data separately from formulas
"""

from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import structlog
from models.pricing import PricingData, RegionPricing
from core.config import settings

logger = structlog.get_logger()


class PricingLoader:
    """
    Load and cache pricing data from pricing_data.yaml files
    Supports multi-region pricing and pricing metadata tracking
    """
    
    def __init__(self):
        self.logger = logger.bind(component="pricing_loader")
        self.plugin_path = Path(settings.PLUGIN_STORAGE_PATH)
        self._cache: Dict[str, PricingData] = {}
    
    async def get_pricing(
        self,
        service_id: str,
        region: str = "us-east-1"
    ) -> Dict[str, Any]:
        """
        Get pricing data for service in specific region
        
        Args:
            service_id: Service identifier (e.g., AWSLambda)
            region: AWS region (defaults to us-east-1)
        
        Returns:
            Dict with pricing rates and metadata
        """
        # Load pricing data (cached)
        pricing_data = await self._load_pricing_data(service_id)
        
        if not pricing_data:
            self.logger.warning(
                "pricing_data_not_found",
                service_id=service_id,
                region=region
            )
            return {}
        
        # Get region-specific pricing
        region_pricing = pricing_data.regions.get(region)
        
        if not region_pricing:
            # Fallback to us-east-1
            self.logger.info(
                "region_not_found_fallback",
                service_id=service_id,
                region=region,
                fallback="us-east-1"
            )
            region_pricing = pricing_data.regions.get("us-east-1")
        
        # Convert to dict and add metadata
        pricing_dict = region_pricing.dict(exclude_none=True)
        
        # Add multipliers if present
        if pricing_data.architecture_multipliers:
            pricing_dict['architecture_multipliers'] = pricing_data.architecture_multipliers
        if pricing_data.tier_multipliers:
            pricing_dict['tier_multipliers'] = pricing_data.tier_multipliers
        
        # Add metadata for tracking
        pricing_dict['_metadata'] = {
            'service': pricing_data.service,
            'version': pricing_data.version,
            'last_updated': pricing_data.last_updated,
            'source': pricing_data.source,
            'region': region
        }
        
        return pricing_dict
    
    async def _load_pricing_data(self, service_id: str) -> Optional[PricingData]:
        """
        Load pricing data from pricing_data.yaml file
        Uses cache if available
        """
        # Check cache
        if service_id in self._cache:
            return self._cache[service_id]
        
        # Load from file
        pricing_file = self.plugin_path / service_id / "pricing_data.yaml"
        
        if not pricing_file.exists():
            self.logger.warning(
                "pricing_file_not_found",
                service_id=service_id,
                path=str(pricing_file)
            )
            return None
        
        try:
            with open(pricing_file, 'r') as f:
                pricing_yaml = yaml.safe_load(f)
            
            # Validate with Pydantic
            pricing_data = PricingData(**pricing_yaml)
            
            # Cache it
            self._cache[service_id] = pricing_data
            
            self.logger.info(
                "pricing_data_loaded",
                service_id=service_id,
                version=pricing_data.version,
                regions=list(pricing_data.regions.keys())
            )
            
            return pricing_data
            
        except Exception as e:
            self.logger.error(
                "failed_to_load_pricing_data",
                service_id=service_id,
                error=str(e)
            )
            return None
    
    def clear_cache(self):
        """Clear pricing cache (for hot-reloading)"""
        self._cache.clear()
        self.logger.info("pricing_cache_cleared")
    
    async def get_pricing_metadata(self, service_id: str) -> Optional[Dict[str, str]]:
        """Get pricing metadata without full pricing data"""
        pricing_data = await self._load_pricing_data(service_id)
        
        if not pricing_data:
            return None
        
        return {
            'service': pricing_data.service,
            'version': pricing_data.version,
            'last_updated': pricing_data.last_updated,
            'source': pricing_data.source
        }
