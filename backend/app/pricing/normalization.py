"""
Pricing data normalization module.
Parses AWS pricing JSON and normalizes into database schema.
"""
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session
from app.models.models import (
    PricingVersion, PricingService, PricingRegion,
    PricingDimension, PricingIngestionLog
)

logger = logging.getLogger(__name__)


class PricingNormalizationError(Exception):
    """Raised when pricing normalization fails."""
    pass


class AWSPricingNormalizer:
    """
    Normalizes AWS pricing JSON into database schema.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_pricing_version(self, source: str = "AWS Pricing API") -> PricingVersion:
        """
        Create a new pricing version.
        
        Args:
            source: Source of pricing data
        
        Returns:
            Created pricing version
        """
        # Deactivate current active version
        self.db.query(PricingVersion).filter(
            PricingVersion.is_active == True
        ).update({"is_active": False})
        
        # Create new version
        version = PricingVersion(
            version=datetime.now().strftime("%Y%m%d_%H%M%S"),
            is_active=True,
            source=source,
            metadata={"created_by": "pricing_ingestion"}
        )
        
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        
        logger.info(f"Created pricing version: {version.version}")
        return version
    
    def get_or_create_service(self, service_code: str, service_name: str = None) -> PricingService:
        """
        Get or create a pricing service.
        
        Args:
            service_code: AWS service code
            service_name: Service display name
        
        Returns:
            PricingService instance
        """
        service = self.db.query(PricingService).filter(
            PricingService.service_code == service_code
        ).first()
        
        if not service:
            service = PricingService(
                service_code=service_code,
                service_name=service_name or service_code,
                description=f"AWS {service_name or service_code}"
            )
            self.db.add(service)
            self.db.commit()
            self.db.refresh(service)
            logger.info(f"Created service: {service_code}")
        
        return service
    
    def get_or_create_region(self, region_code: str, region_name: str = None, location: str = None) -> Optional[PricingRegion]:
        """
        Get or create a pricing region.
        
        Args:
            region_code: AWS region code
            region_name: Region display name
            location: Region location
        
        Returns:
            PricingRegion instance or None for global services
        """
        if not region_code or region_code.lower() in ['global', 'any', '']:
            return None
        
        region = self.db.query(PricingRegion).filter(
            PricingRegion.region_code == region_code
        ).first()
        
        if not region:
            region = PricingRegion(
                region_code=region_code,
                region_name=region_name or region_code,
                location=location or region_name or region_code
            )
            self.db.add(region)
            self.db.commit()
            self.db.refresh(region)
            logger.info(f"Created region: {region_code}")
        
        return region
    
    def normalize_pricing_file(
        self,
        pricing_data: Dict,
        service_code: str,
        version: PricingVersion
    ) -> int:
        """
        Normalize a pricing file into database.
        
        Args:
            pricing_data: Parsed pricing JSON
            service_code: AWS service code
            version: Pricing version to associate with
        
        Returns:
            Number of pricing dimensions created
        """
        try:
            # Get or create service
            service_name = pricing_data.get("formatVersion", service_code)
            service = self.get_or_create_service(service_code, service_name)
            
            # Extract products and terms
            products = pricing_data.get("products", {})
            terms = pricing_data.get("terms", {})
            
            # Process On-Demand pricing
            on_demand_terms = terms.get("OnDemand", {})
            
            count = 0
            for sku, product in products.items():
                try:
                    # Extract product attributes
                    attributes = product.get("attributes", {})
                    product_family = product.get("productFamily", "Unknown")
                    
                    # Get region
                    region_code = attributes.get("regionCode") or attributes.get("location")
                    region_name = attributes.get("location")
                    region = self.get_or_create_region(region_code, region_name)
                    
                    # Get pricing terms for this SKU
                    sku_terms = on_demand_terms.get(sku, {})
                    
                    for term_key, term_data in sku_terms.items():
                        price_dimensions = term_data.get("priceDimensions", {})
                        
                        for price_key, price_data in price_dimensions.items():
                            # Extract price
                            price_per_unit_data = price_data.get("pricePerUnit", {})
                            price_usd = price_per_unit_data.get("USD", "0")
                            
                            try:
                                price_decimal = Decimal(price_usd)
                            except:
                                logger.warning(f"Invalid price for SKU {sku}: {price_usd}")
                                continue
                            
                            # Skip zero prices (often metadata entries)
                            if price_decimal == 0:
                                continue
                            
                            # Get unit
                            unit = price_data.get("unit", "Unknown")
                            
                            # Create pricing dimension
                            dimension = PricingDimension(
                                version_id=version.id,
                                service_id=service.id,
                                region_id=region.id if region else None,
                                sku=sku,
                                product_family=product_family,
                                attributes=attributes,
                                unit=unit,
                                price_per_unit=price_decimal,
                                currency="USD",
                                term_type="OnDemand"
                            )
                            
                            self.db.add(dimension)
                            count += 1
                            
                            # Commit in batches
                            if count % 1000 == 0:
                                self.db.commit()
                                logger.info(f"Processed {count} pricing dimensions for {service_code}")
                
                except Exception as e:
                    logger.error(f"Error processing SKU {sku}: {e}")
                    continue
            
            # Final commit
            self.db.commit()
            logger.info(f"Completed normalization for {service_code}: {count} dimensions")
            
            return count
        
        except Exception as e:
            self.db.rollback()
            raise PricingNormalizationError(f"Failed to normalize pricing for {service_code}: {e}")
    
    def log_ingestion(
        self,
        version: PricingVersion,
        service_code: str,
        status: str,
        records_processed: int = None,
        error_message: str = None
    ):
        """
        Log pricing ingestion activity.
        
        Args:
            version: Pricing version
            service_code: Service code
            status: Ingestion status
            records_processed: Number of records processed
            error_message: Error message if failed
        """
        log = PricingIngestionLog(
            version_id=version.id,
            service_code=service_code,
            status=status,
            records_processed=records_processed,
            error_message=error_message,
            completed_at=datetime.now() if status in ['completed', 'failed'] else None
        )
        
        self.db.add(log)
        self.db.commit()


def normalize_pricing_data(
    db: Session,
    pricing_files: Dict[str, Path]
) -> PricingVersion:
    """
    Normalize all pricing files into database.
    
    Args:
        db: Database session
        pricing_files: Dictionary mapping service codes to file paths
    
    Returns:
        Created pricing version
    """
    normalizer = AWSPricingNormalizer(db)
    
    # Create new pricing version
    version = normalizer.create_pricing_version()
    
    # Process each service
    for service_code, file_path in pricing_files.items():
        try:
            logger.info(f"Normalizing {service_code} from {file_path}")
            
            # Load pricing file
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                pricing_data = json.load(f)
            
            # Normalize
            count = normalizer.normalize_pricing_file(pricing_data, service_code, version)
            
            # Log success
            normalizer.log_ingestion(version, service_code, "completed", count)
        
        except Exception as e:
            logger.error(f"Failed to normalize {service_code}: {e}")
            normalizer.log_ingestion(version, service_code, "failed", error_message=str(e))
            continue
    
    return version
