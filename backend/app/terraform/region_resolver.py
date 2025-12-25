"""
Region resolution and enforcement.
Deterministic region resolution with no defaults.
"""
import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class RegionResolutionError(Exception):
    """Raised when region cannot be determined."""
    pass


class RegionResolver:
    """
    Deterministic region resolver.
    
    Resolution priority:
    1. Explicit resource.region
    2. Provider.region
    3. Availability zone (strip suffix)
    4. ERROR (no default)
    
    NO DEFAULTS. NO GUESSING.
    """
    
    # Valid AWS regions
    VALID_REGIONS = {
        "us-east-1", "us-east-2", "us-west-1", "us-west-2",
        "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1", "eu-north-1",
        "ap-south-1", "ap-southeast-1", "ap-southeast-2",
        "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
        "ca-central-1", "sa-east-1",
        "af-south-1", "ap-east-1", "me-south-1"
    }
    
    def __init__(self, provider_config: Optional[Dict[str, Any]] = None):
        """
        Initialize resolver.
        
        Args:
            provider_config: Provider configuration from Terraform
        """
        self.provider_config = provider_config or {}
    
    def resolve_region(self, resource: Dict[str, Any]) -> str:
        """
        Resolve region for resource.
        
        Args:
            resource: Resource dictionary
        
        Returns:
            AWS region code
        
        Raises:
            RegionResolutionError: If region cannot be determined
        """
        resource_type = resource.get("type", "unknown")
        resource_name = resource.get("name", "unknown")
        
        # Priority 1: Explicit resource region
        if "region" in resource:
            region = resource["region"]
            return self.validate_region(region, f"{resource_type}.{resource_name}")
        
        # Priority 2: Provider region
        provider_region = self.provider_config.get("region")
        if provider_region:
            return self.validate_region(provider_region, "provider")
        
        # Priority 3: Availability zone
        if "availability_zone" in resource:
            az = resource["availability_zone"]
            region = self.az_to_region(az)
            if region:
                return region
        
        # FAIL - no default
        raise RegionResolutionError(
            f"Cannot determine region for {resource_type}.{resource_name}. "
            f"No explicit region, provider region, or availability zone found."
        )
    
    def validate_region(self, region: str, context: str) -> str:
        """
        Validate region code.
        
        Args:
            region: Region code to validate
            context: Context for error message
        
        Returns:
            Validated region code
        
        Raises:
            RegionResolutionError: If region invalid
        """
        if not region:
            raise RegionResolutionError(f"Empty region in {context}")
        
        if region not in self.VALID_REGIONS:
            raise RegionResolutionError(
                f"Invalid region '{region}' in {context}. "
                f"Valid regions: {', '.join(sorted(self.VALID_REGIONS))}"
            )
        
        return region
    
    def az_to_region(self, availability_zone: str) -> Optional[str]:
        """
        Convert availability zone to region.
        
        Args:
            availability_zone: AZ code (e.g., "us-east-1a")
        
        Returns:
            Region code or None if invalid
        """
        # AZ format: region + letter (e.g., us-east-1a)
        match = re.match(r'^([a-z]{2}-[a-z]+-\d+)[a-z]$', availability_zone)
        if match:
            region = match.group(1)
            if region in self.VALID_REGIONS:
                return region
        
        logger.warning(f"Could not extract region from AZ: {availability_zone}")
        return None
    
    def get_provider_region(self) -> Optional[str]:
        """
        Get provider default region.
        
        Returns:
            Provider region or None
        """
        return self.provider_config.get("region")
