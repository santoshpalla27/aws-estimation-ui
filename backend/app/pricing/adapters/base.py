"""
Base adapter for pricing calculations.
All service-specific adapters inherit from this.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.models import PricingDimension, PricingVersion


class BaseAdapter(ABC):
    """Base class for all pricing adapters."""
    
    def __init__(self, db: Session, pricing_version: PricingVersion):
        self.db = db
        self.pricing_version = pricing_version
    
    @abstractmethod
    def calculate_cost(self, resource: Dict) -> Dict:
        """
        Calculate monthly cost for a resource.
        
        Args:
            resource: Normalized resource dictionary with attributes
        
        Returns:
            Dictionary with:
                - monthly_cost: Decimal
                - pricing_details: Dict with breakdown
                - warnings: List of warning messages
        """
        pass
    
    def query_pricing(
        self,
        service_code: str,
        region_code: Optional[str],
        filters: Dict
    ) -> Optional[PricingDimension]:
        """
        Query pricing database for matching SKU.
        
        Args:
            service_code: AWS service code
            region_code: AWS region code
            filters: Attribute filters
        
        Returns:
            Matching pricing dimension or None
        """
        query = self.db.query(PricingDimension).join(
            PricingDimension.service
        ).filter(
            PricingDimension.version_id == self.pricing_version.id
        )
        
        # Filter by service
        from app.models.models import PricingService
        query = query.filter(PricingService.service_code == service_code)
        
        # Filter by region if provided
        if region_code:
            from app.models.models import PricingRegion
            query = query.join(PricingDimension.region).filter(
                PricingRegion.region_code == region_code
            )
        
        # Apply attribute filters using JSONB containment
        for key, value in filters.items():
            query = query.filter(
                PricingDimension.attributes[key].astext == str(value)
            )
        
        return query.first()
    
    def hours_per_month(self) -> Decimal:
        """Get hours per month (730 hours)."""
        return Decimal("730")
    
    def gb_months(self, gb: Decimal) -> Decimal:
        """Convert GB to GB-months."""
        return gb
    
    def format_cost_result(
        self,
        monthly_cost: Decimal,
        pricing_details: Dict,
        warnings: Optional[List[str]] = None
    ) -> Dict:
        """
        Format cost calculation result.
        
        Args:
            monthly_cost: Calculated monthly cost
            pricing_details: Breakdown of pricing calculation
            warnings: Optional warning messages
        
        Returns:
            Formatted result dictionary
        """
        return {
            "monthly_cost": float(monthly_cost),
            "pricing_details": pricing_details,
            "warnings": warnings or []
        }
