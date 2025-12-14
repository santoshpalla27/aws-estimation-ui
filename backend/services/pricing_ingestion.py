"""
AWS Pricing API Ingestion Pipeline
Offline service that fetches pricing from AWS Pricing API
Runs on schedule (daily) - NEVER called during estimation
"""

import asyncio
import boto3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import structlog
from models.pricing_models import PricingVersion, PricingRate, PricingMetadata, PricingChange

logger = structlog.get_logger()


class AWSPricingAPIClient:
    """AWS Pricing API client with pagination and retry"""
    
    def __init__(self):
        self.client = boto3.client('pricing', region_name='us-east-1')
        self.logger = logger.bind(component="aws_pricing_client")
    
    def fetch_service_pricing(
        self,
        service_code: str,
        region: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch pricing for service in region
        Uses AWS Price List API with pagination
        """
        location = self._region_to_location(region)
        
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'ServiceCode', 'Value': service_code},
            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
            {'Type': 'TERM_MATCH', 'Field': 'termType', 'Value': 'OnDemand'}
        ]
        
        paginator = self.client.get_paginator('get_products')
        
        skus = []
        try:
            for page in paginator.paginate(ServiceCode=service_code, Filters=filters):
                for price_item in page.get('PriceList', []):
                    sku = json.loads(price_item)
                    skus.append(sku)
            
            self.logger.info("fetched_pricing", service=service_code, region=region, skus=len(skus))
        except Exception as e:
            self.logger.error("fetch_failed", service=service_code, region=region, error=str(e))
        
        return skus
    
    def _region_to_location(self, region: str) -> str:
        """Map AWS region to location name"""
        REGION_LOCATION_MAP = {
            'us-east-1': 'US East (N. Virginia)',
            'us-west-2': 'US West (Oregon)',
            'eu-west-1': 'EU (Ireland)',
            'ap-south-1': 'Asia Pacific (Mumbai)',
            'ap-southeast-1': 'Asia Pacific (Singapore)',
        }
        return REGION_LOCATION_MAP.get(region, region)


class SKUNormalizer:
    """
    Normalize AWS SKUs to internal pricing keys
    Service-specific normalization logic
    """
    
    NORMALIZATION_RULES = {
        "AWSLambda": {
            "usagetype_patterns": {
                "Lambda-GB-Second": "compute.gb_second",
                "Lambda-GB-Second-ARM": "compute.gb_second_arm",
                "Request": "request",
                "Request-ARM": "request_arm"
            }
        },
        "AmazonEC2": {
            "instance_type_pattern": "instance.{instance_type}.hour"
        },
        "AmazonS3": {
            "usagetype_patterns": {
                "TimedStorage-ByteHrs": "storage_standard_gb_month",
                "Requests-Tier1": "put_request_per_1000",
                "Requests-Tier2": "get_request_per_1000"
            }
        }
    }
    
    def normalize(self, sku: Dict[str, Any], service_code: str) -> Optional[Dict[str, Any]]:
        """Convert AWS SKU to internal pricing rate"""
        try:
            product = sku.get('product', {})
            attributes = product.get('attributes', {})
            terms = sku.get('terms', {}).get('OnDemand', {})
            
            # Extract price
            price = self._extract_price(terms)
            if not price:
                return None
            
            # Normalize based on service
            pricing_key = self._get_pricing_key(service_code, attributes)
            if not pricing_key:
                return None
            
            return {
                'pricing_key': pricing_key,
                'rate': Decimal(str(price)),
                'unit': attributes.get('unit', ''),
                'source_sku': sku.get('product', {}).get('sku', '')
            }
        except Exception as e:
            logger.error("normalization_failed", error=str(e))
            return None
    
    def _extract_price(self, terms: Dict) -> Optional[float]:
        """Extract price from OnDemand terms"""
        for term_data in terms.values():
            price_dimensions = term_data.get('priceDimensions', {})
            for dimension in price_dimensions.values():
                price_per_unit = dimension.get('pricePerUnit', {}).get('USD')
                if price_per_unit:
                    return float(price_per_unit)
        return None
    
    def _get_pricing_key(self, service_code: str, attributes: Dict) -> Optional[str]:
        """Get internal pricing key from AWS attributes"""
        rules = self.NORMALIZATION_RULES.get(service_code, {})
        
        if 'usagetype_patterns' in rules:
            usage_type = attributes.get('usagetype', '')
            for pattern, key in rules['usagetype_patterns'].items():
                if pattern in usage_type:
                    return key
        
        return None


class PricingChangeDetector:
    """Detect pricing changes between versions"""
    
    async def detect_changes(
        self,
        session: AsyncSession,
        old_version: str,
        new_version: str
    ) -> List[PricingChange]:
        """Compare two pricing versions and detect changes"""
        changes = []
        
        # Load old rates
        stmt = select(PricingRate).where(PricingRate.version == old_version)
        result = await session.execute(stmt)
        old_rates = {(r.service, r.region, r.pricing_key): r.rate for r in result.scalars()}
        
        # Load new rates
        stmt = select(PricingRate).where(PricingRate.version == new_version)
        result = await session.execute(stmt)
        new_rates_list = result.scalars().all()
        
        for new_rate in new_rates_list:
            key = (new_rate.service, new_rate.region, new_rate.pricing_key)
            old_rate = old_rates.get(key)
            
            if old_rate and old_rate != new_rate.rate:
                change_percent = ((new_rate.rate - old_rate) / old_rate) * 100
                
                change = PricingChange(
                    old_version=old_version,
                    new_version=new_version,
                    service=new_rate.service,
                    region=new_rate.region,
                    pricing_key=new_rate.pricing_key,
                    old_rate=old_rate,
                    new_rate=new_rate.rate,
                    change_percent=change_percent,
                    detected_at=datetime.utcnow()
                )
                changes.append(change)
        
        return changes


class PricingIngestionPipeline:
    """
    Main ingestion pipeline
    Runs offline on schedule - NEVER during estimation
    """
    
    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url)
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self.aws_client = AWSPricingAPIClient()
        self.normalizer = SKUNormalizer()
        self.change_detector = PricingChangeDetector()
        self.logger = logger.bind(component="pricing_ingestion")
    
    async def run(self, services: List[str], regions: List[str]):
        """Main pipeline execution"""
        version = datetime.utcnow().strftime("%Y-%m")
        
        self.logger.info("pipeline_started", version=version, services=len(services), regions=len(regions))
        
        try:
            # 1. Fetch from AWS Pricing API
            raw_pricing = await self._fetch_all_pricing(services, regions)
            
            # 2. Normalize SKUs
            normalized = self._normalize_pricing(raw_pricing)
            
            # 3. Store new version
            async with self.async_session() as session:
                await self._store_pricing(session, version, normalized)
                
                # 4. Detect changes
                changes = await self.change_detector.detect_changes(
                    session,
                    old_version=self._get_previous_version(version),
                    new_version=version
                )
                
                # 5. Store changes
                for change in changes:
                    session.add(change)
                
                await session.commit()
                
                self.logger.info("pipeline_complete", version=version, changes=len(changes))
        
        except Exception as e:
            self.logger.error("pipeline_failed", error=str(e))
            raise
    
    async def _fetch_all_pricing(self, services: List[str], regions: List[str]) -> Dict:
        """Fetch pricing for all services and regions"""
        pricing_data = {}
        
        for service in services:
            pricing_data[service] = {}
            for region in regions:
                skus = self.aws_client.fetch_service_pricing(service, region)
                pricing_data[service][region] = skus
        
        return pricing_data
    
    def _normalize_pricing(self, raw_pricing: Dict) -> List[Dict]:
        """Normalize all SKUs"""
        normalized = []
        
        for service, regions in raw_pricing.items():
            for region, skus in regions.items():
                for sku in skus:
                    normalized_rate = self.normalizer.normalize(sku, service)
                    if normalized_rate:
                        normalized_rate['service'] = service
                        normalized_rate['region'] = region
                        normalized.append(normalized_rate)
        
        return normalized
    
    async def _store_pricing(self, session: AsyncSession, version: str, rates: List[Dict]):
        """Store pricing in database"""
        # Create version
        pricing_version = PricingVersion(
            version=version,
            created_at=datetime.utcnow(),
            source_type="aws_pricing_api",
            is_active=True
        )
        session.add(pricing_version)
        
        # Store rates
        for rate_data in rates:
            rate = PricingRate(
                version=version,
                service=rate_data['service'],
                region=rate_data['region'],
                pricing_key=rate_data['pricing_key'],
                rate=rate_data['rate'],
                unit=rate_data.get('unit'),
                source_sku=rate_data.get('source_sku'),
                fetched_at=datetime.utcnow()
            )
            session.add(rate)
    
    def _get_previous_version(self, current_version: str) -> str:
        """Get previous month's version"""
        year, month = current_version.split('-')
        prev_month = int(month) - 1
        if prev_month == 0:
            prev_month = 12
            year = str(int(year) - 1)
        return f"{year}-{prev_month:02d}"


async def main():
    """Run pricing ingestion pipeline"""
    DATABASE_URL = "postgresql+asyncpg://user:password@localhost/aws_cost_estimation"
    
    pipeline = PricingIngestionPipeline(DATABASE_URL)
    
    services = ["AWSLambda", "AmazonEC2", "AmazonS3", "AmazonRDS", "AmazonDynamoDB"]
    regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-south-1", "ap-southeast-1"]
    
    await pipeline.run(services, regions)


if __name__ == "__main__":
    asyncio.run(main())
