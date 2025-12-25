"""
Async pricing adapter base class.
All pricing queries are async to eliminate blocking DB calls.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.pricing.adapters.base import (
    PricingAdapter,
    PricingRule,
    CostResult,
    ValidationError,
    PricingMatchError
)
from app.models.models import PricingDimension, PricingVersion


class AsyncPricingAdapter(ABC):
    """
    Async pricing adapter base class.
    
    All database queries are async.
    No blocking calls in API handlers.
    """
    
    def __init__(self, db: AsyncSession, pricing_version: PricingVersion):
        """
        Initialize adapter.
        
        Args:
            db: Async database session
            pricing_version: Active pricing version
        """
        self.db = db
        self.pricing_version = pricing_version
    
    @property
    @abstractmethod
    def required_attributes(self) -> List[str]:
        """Required resource attributes."""
        pass
    
    @property
    @abstractmethod
    def supported_regions(self) -> List[str]:
        """Supported AWS regions."""
        pass
    
    @property
    @abstractmethod
    def service_code(self) -> str:
        """AWS service code."""
        pass
    
    @abstractmethod
    def validate(self, resource: Dict[str, Any]) -> None:
        """
        Validate resource (synchronous validation only).
        
        Args:
            resource: Resource to validate
        
        Raises:
            ValidationError: If validation fails
        """
        pass
    
    @abstractmethod
    async def match_pricing(self, resource: Dict[str, Any]) -> PricingRule:
        """
        Match resource to pricing rule (async database query).
        
        Args:
            resource: Resource to match
        
        Returns:
            PricingRule from database
        
        Raises:
            PricingMatchError: If no pricing rule found
        """
        pass
    
    @abstractmethod
    def calculate(self, resource: Dict[str, Any], pricing_rule: PricingRule) -> CostResult:
        """
        Calculate cost (synchronous calculation).
        
        Args:
            resource: Resource to calculate cost for
            pricing_rule: Matched pricing rule
        
        Returns:
            CostResult with full audit trail
        """
        pass
    
    async def calculate_cost(self, resource: Dict[str, Any]) -> CostResult:
        """
        Complete async cost calculation pipeline.
        
        Args:
            resource: Resource to calculate cost for
        
        Returns:
            CostResult with full audit trail
        
        Raises:
            ValidationError: If validation fails
            PricingMatchError: If no pricing rule found
        """
        # Step 1: Validate (sync)
        self.validate(resource)
        
        # Step 2: Match pricing (async DB query)
        pricing_rule = await self.match_pricing(resource)
        
        # Step 3: Calculate (sync)
        cost_result = self.calculate(resource, pricing_rule)
        
        return cost_result
    
    async def _query_pricing_dimension(
        self,
        service_code: str,
        region_code: str,
        filters: Dict[str, Any]
    ) -> PricingDimension:
        """
        Helper to query pricing dimension asynchronously.
        
        Args:
            service_code: AWS service code
            region_code: AWS region code
            filters: Additional attribute filters
        
        Returns:
            PricingDimension
        
        Raises:
            PricingMatchError: If no match found
        """
        query = select(PricingDimension).where(
            PricingDimension.version_id == self.pricing_version.id,
            PricingDimension.service_code == service_code,
            PricingDimension.region_code == region_code
        )
        
        # Add attribute filters
        for key, value in filters.items():
            query = query.where(
                PricingDimension.attributes[key].astext == str(value)
            )
        
        result = await self.db.execute(query)
        dimension = result.scalar_one_or_none()
        
        if dimension is None:
            raise PricingMatchError(
                f"No pricing found for {service_code} in {region_code} with filters {filters}"
            )
        
        return dimension
