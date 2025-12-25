"""
Base pricing normalizer.
Defines interface for service-specific normalizers.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

import logging

logger = logging.getLogger(__name__)


class NormalizationError(Exception):
    """Raised when pricing normalization fails."""
    pass


class BasePricingNormalizer(ABC):
    """
    Base class for service-specific pricing normalizers.
    
    Each service (EC2, RDS, S3, etc.) must implement a normalizer
    that converts raw AWS pricing JSON into deterministic relational rows.
    
    Rules:
    - One row = one billable SKU
    - No ambiguous pricing
    - All required attributes extracted
    - Normalization failures are fatal
    """
    
    def __init__(self, db: AsyncSession, version_id: int):
        """
        Initialize normalizer.
        
        Args:
            db: Database session
            version_id: Pricing version ID
        """
        self.db = db
        self.version_id = version_id
    
    @property
    @abstractmethod
    def service_code(self) -> str:
        """AWS service code (e.g., 'AmazonEC2')."""
        pass
    
    @property
    @abstractmethod
    def required_attributes(self) -> List[str]:
        """
        Required attributes that must be extracted from pricing data.
        
        Returns:
            List of attribute names
        """
        pass
    
    @abstractmethod
    async def normalize_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a single product from AWS pricing JSON.
        
        Args:
            product: Raw product data from AWS
        
        Returns:
            Normalized product dictionary with:
            - sku
            - region
            - All service-specific attributes
            - price_per_unit
            - unit
            - currency
        
        Raises:
            NormalizationError: If normalization fails
        """
        pass
    
    @abstractmethod
    async def store_normalized_data(self, normalized_products: List[Dict[str, Any]]) -> int:
        """
        Store normalized products in service-specific table.
        
        Args:
            normalized_products: List of normalized product dictionaries
        
        Returns:
            Number of rows inserted
        
        Raises:
            NormalizationError: If storage fails
        """
        pass
    
    async def normalize_and_store(self, pricing_data: Dict[str, Any]) -> int:
        """
        Complete normalization pipeline.
        
        Args:
            pricing_data: Raw AWS pricing JSON
        
        Returns:
            Number of products normalized
        
        Raises:
            NormalizationError: If normalization fails
        """
        products = pricing_data.get("products", {})
        terms = pricing_data.get("terms", {})
        
        if not products:
            raise NormalizationError(f"No products found for {self.service_code}")
        
        normalized = []
        errors = []
        
        for sku, product_data in products.items():
            try:
                # Extract product attributes
                normalized_product = await self.normalize_product(product_data)
                
                # Extract pricing from terms
                pricing = self._extract_pricing(sku, terms)
                if pricing:
                    normalized_product.update(pricing)
                    normalized.append(normalized_product)
            
            except Exception as e:
                errors.append(f"SKU {sku}: {str(e)}")
                logger.warning(f"Failed to normalize SKU {sku}: {e}")
        
        if not normalized:
            raise NormalizationError(
                f"No products normalized for {self.service_code}. Errors: {errors[:5]}"
            )
        
        # Store in database
        count = await self.store_normalized_data(normalized)
        
        logger.info(
            f"Normalized {count} products for {self.service_code} "
            f"({len(errors)} errors)"
        )
        
        return count
    
    def _extract_pricing(self, sku: str, terms: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract pricing from terms section.
        
        Args:
            sku: Product SKU
            terms: Terms section from pricing JSON
        
        Returns:
            Dictionary with price_per_unit, unit, currency
        """
        # Get OnDemand pricing
        on_demand = terms.get("OnDemand", {})
        sku_terms = on_demand.get(sku, {})
        
        for term_code, term_data in sku_terms.items():
            price_dimensions = term_data.get("priceDimensions", {})
            
            for dimension_code, dimension in price_dimensions.items():
                price_per_unit = dimension.get("pricePerUnit", {}).get("USD")
                
                if price_per_unit is not None:
                    return {
                        "price_per_unit": Decimal(str(price_per_unit)),
                        "unit": dimension.get("unit", ""),
                        "currency": "USD"
                    }
        
        return {}
    
    def _validate_required_attributes(self, attributes: Dict[str, Any]) -> None:
        """
        Validate that all required attributes are present.
        
        Args:
            attributes: Extracted attributes
        
        Raises:
            NormalizationError: If required attributes missing
        """
        missing = []
        for attr in self.required_attributes:
            if attr not in attributes or attributes[attr] is None:
                missing.append(attr)
        
        if missing:
            raise NormalizationError(
                f"Missing required attributes: {', '.join(missing)}"
            )
