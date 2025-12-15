"""
Pricing Keys Registry - Single Source of Truth for All Pricing References

This registry maps symbolic pricing keys to their actual pricing data paths.
NO NUMERIC LITERALS ALLOWED IN FORMULAS.

Format:
  "ServiceName": {
      "symbolic_key": "aws.service.category.item.region"
  }

Usage in formulas:
  formula: storage_gb * pricing.storage.standard_gb_month
  
  The key "storage.standard_gb_month" is resolved via this registry to:
  aws.s3.storage.standard.{region}
"""

from typing import Dict

# Pricing key naming convention:
# aws.{service}.{category}.{item}.{region}
# 
# Examples:
# - aws.s3.storage.standard.us-east-1
# - aws.ec2.compute.t3.micro.linux.us-east-1
# - aws.lambda.compute.gb_second.us-east-1

PRICING_KEY_REGISTRY: Dict[str, Dict[str, str]] = {
    
    "AmazonS3": {
        # Storage pricing
        "storage.standard_gb_month": "storage.standard",
        "storage.intelligent_tiering_gb_month": "storage.intelligent_tiering",
        "storage.standard_ia_gb_month": "storage.standard_ia",
        "storage.onezone_ia_gb_month": "storage.onezone_ia",
        "storage.glacier_instant_gb_month": "storage.glacier_instant",
        "storage.glacier_flexible_gb_month": "storage.glacier_flexible",
        "storage.glacier_deep_archive_gb_month": "storage.glacier_deep_archive",
        
        # Request pricing
        "requests.put_per_1000": "requests.put_per_1000",
        "requests.get_per_1000": "requests.get_per_1000",
        "requests.lifecycle_per_1000": "requests.lifecycle_per_1000",
        
        # Data transfer pricing
        "transfer.internet_out_tier1_gb": "data_transfer.tier_1_per_gb",
        "transfer.internet_out_tier2_gb": "data_transfer.tier_2_per_gb",
        "transfer.internet_out_tier3_gb": "data_transfer.tier_3_per_gb",
        "transfer.internet_out_tier4_gb": "data_transfer.tier_4_per_gb",
        "transfer.ingress_gb": "data_transfer.ingress_per_gb",
        "transfer.free_tier_gb": "data_transfer.free_tier_gb",
    },
    
    "AmazonEC2": {
        # Instance pricing (per hour)
        "compute.instance.t3_nano": "instances.t3.nano",
        "compute.instance.t3_micro": "instances.t3.micro",
        "compute.instance.t3_small": "instances.t3.small",
        "compute.instance.t3_medium": "instances.t3.medium",
        "compute.instance.t3_large": "instances.t3.large",
        "compute.instance.m5_large": "instances.m5.large",
        "compute.instance.m5_xlarge": "instances.m5.xlarge",
        "compute.instance.m5_2xlarge": "instances.m5.2xlarge",
        "compute.instance.c5_large": "instances.c5.large",
        "compute.instance.r5_large": "instances.r5.large",
        
        # OS multipliers
        "os.linux_multiplier": "operating_system_multiplier.Linux",
        "os.windows_multiplier": "operating_system_multiplier.Windows",
        "os.rhel_multiplier": "operating_system_multiplier.RHEL",
        "os.suse_multiplier": "operating_system_multiplier.SUSE",
        
        # Data transfer
        "transfer.internet_out_tier1_gb": "data_transfer.tier_1_per_gb",
        "transfer.internet_out_tier2_gb": "data_transfer.tier_2_per_gb",
        "transfer.internet_out_tier3_gb": "data_transfer.tier_3_per_gb",
        "transfer.internet_out_tier4_gb": "data_transfer.tier_4_per_gb",
        "transfer.cross_az_gb": "data_transfer.cross_az_per_gb",
        "transfer.free_tier_gb": "data_transfer.free_tier_gb",
        
        # Constants
        "constants.hours_per_month": "constants.hours_per_month",
    },
    
    "AWSLambda": {
        # Compute pricing
        "compute.gb_second": "compute.gb_second",
        
        # Request pricing
        "requests.per_million": "requests.per_million",
        
        # Architecture multipliers
        "arch.x86_64_multiplier": "architecture_multiplier.x86_64",
        "arch.arm64_multiplier": "architecture_multiplier.arm64",
        
        # Ephemeral storage
        "storage.ephemeral_per_gb_second": "ephemeral_storage.per_gb_second",
        
        # Free tier
        "free_tier.compute_gb_seconds": "free_tier.compute_gb_seconds",
        "free_tier.requests": "free_tier.requests",
    },
    
    "AmazonRDS": {
        # Instance pricing
        "compute.instance.db_t3_micro": "instances.db.t3.micro",
        "compute.instance.db_t3_small": "instances.db.t3.small",
        "compute.instance.db_t3_medium": "instances.db.t3.medium",
        "compute.instance.db_m5_large": "instances.db.m5.large",
        "compute.instance.db_r5_large": "instances.db.r5.large",
        
        # Storage pricing
        "storage.gp3_per_gb": "storage.gp3_per_gb",
        "storage.gp2_per_gb": "storage.gp2_per_gb",
        "storage.io1_per_gb": "storage.io1_per_gb",
        "storage.io1_per_iops": "storage.io1_per_iops",
        
        # Backup storage
        "backup.storage_per_gb": "backup_storage_per_gb",
        
        # Multi-AZ
        "multi_az.multiplier": "multi_az_multiplier",
        
        # Data transfer
        "transfer.cross_az_gb": "data_transfer.cross_az_per_gb",
        "transfer.internet_out_gb": "data_transfer.internet_out_per_gb",
        
        # Constants
        "constants.hours_per_month": "constants.hours_per_month",
    },
    
    "AmazonDynamoDB": {
        # On-demand pricing
        "on_demand.write_per_million": "on_demand.write_request_per_million",
        "on_demand.read_per_million": "on_demand.read_request_per_million",
        
        # Provisioned pricing
        "provisioned.wcu_per_hour": "provisioned.write_capacity_unit_per_hour",
        "provisioned.rcu_per_hour": "provisioned.read_capacity_unit_per_hour",
        
        # Storage
        "storage.per_gb_month": "storage.per_gb_month",
        
        # Data transfer
        "transfer.internet_out_gb": "data_transfer.internet_out_per_gb",
        "transfer.cross_region_gb": "data_transfer.cross_region_per_gb",
        
        # Free tier
        "free_tier.storage_gb": "free_tier.storage_gb",
        "free_tier.write_requests": "free_tier.write_requests_per_month",
        "free_tier.read_requests": "free_tier.read_requests_per_month",
    },
    
    # Add remaining 46 services...
    # This is a template - full registry would include all services
}


def get_pricing_key(service: str, symbolic_key: str) -> str:
    """
    Get the actual pricing data path for a symbolic key
    
    Args:
        service: Service name (e.g., "AmazonS3")
        symbolic_key: Symbolic key from formula (e.g., "storage.standard_gb_month")
    
    Returns:
        Pricing data path
    
    Raises:
        KeyError: If service or key not found
    """
    if service not in PRICING_KEY_REGISTRY:
        raise KeyError(f"Service '{service}' not found in pricing key registry")
    
    if symbolic_key not in PRICING_KEY_REGISTRY[service]:
        raise KeyError(
            f"Pricing key '{symbolic_key}' not found for service '{service}'. "
            f"Available keys: {list(PRICING_KEY_REGISTRY[service].keys())}"
        )
    
    return PRICING_KEY_REGISTRY[service][symbolic_key]


def validate_formula_keys(service: str, pricing_keys: list) -> list:
    """
    Validate that all pricing keys in a formula exist in the registry
    
    Args:
        service: Service name
        pricing_keys: List of pricing keys from formula
    
    Returns:
        List of validation errors (empty if all valid)
    """
    errors = []
    
    if service not in PRICING_KEY_REGISTRY:
        errors.append(f"Service '{service}' not in pricing key registry")
        return errors
    
    for key in pricing_keys:
        if key not in PRICING_KEY_REGISTRY[service]:
            errors.append(
                f"Pricing key '{key}' not found for '{service}'. "
                f"Available: {list(PRICING_KEY_REGISTRY[service].keys())}"
            )
    
    return errors
