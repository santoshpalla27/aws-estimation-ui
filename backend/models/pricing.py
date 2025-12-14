"""
Pricing Data Models - Pydantic schemas for pricing data validation
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


class FreeTier(BaseModel):
    """Free tier configuration"""
    gb_seconds: Optional[float] = None
    requests: Optional[int] = None
    storage_gb: Optional[float] = None
    hours: Optional[float] = None
    # Add more free tier types as needed


class RegionPricing(BaseModel):
    """Region-specific pricing rates"""
    # Common pricing fields (services override as needed)
    gb_second: Optional[float] = None
    request: Optional[float] = None
    storage_gb_month: Optional[float] = None
    instance_hour: Optional[float] = None
    vcpu_hour: Optional[float] = None
    memory_gb_hour: Optional[float] = None
    
    # Free tier
    free_tier: Optional[FreeTier] = None
    
    # Allow additional fields for service-specific pricing
    class Config:
        extra = "allow"


class PricingData(BaseModel):
    """Root pricing data model"""
    service: str = Field(..., description="Service ID (e.g., AWSLambda)")
    version: str = Field(..., description="Pricing version (e.g., 2024.12)")
    last_updated: str = Field(..., description="Last update date (YYYY-MM-DD)")
    source: str = Field(..., description="Pricing source URL")
    
    regions: Dict[str, RegionPricing] = Field(..., description="Region-specific pricing")
    
    # Optional multipliers/modifiers
    architecture_multipliers: Optional[Dict[str, float]] = None
    tier_multipliers: Optional[Dict[str, float]] = None
    
    @validator('regions')
    def validate_regions(cls, v):
        """Ensure at least us-east-1 exists"""
        if 'us-east-1' not in v:
            raise ValueError("Pricing data must include us-east-1 region")
        return v
    
    @validator('last_updated')
    def validate_date_format(cls, v):
        """Validate date format"""
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError("last_updated must be in YYYY-MM-DD format")
        return v


class PricingMetadata(BaseModel):
    """Pricing metadata for estimate responses"""
    service: str
    version: str
    last_updated: str
    source: str
    region: str
