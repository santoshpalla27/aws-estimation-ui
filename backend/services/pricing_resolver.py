"""
Pricing Resolver - Local-only pricing resolution (NO AWS API CALLS)
Implements the PricingResolver interface from hybrid architecture
"""

from typing import Dict, Any, Optional, Protocol
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from models.pricing_models import PricingRate, PricingVersion

logger = structlog.get_logger()


class PricingKeyNotFoundError(Exception):
    """Raised when pricing key doesn't exist"""
    def __init__(self, key: str, region: str, version: str):
        self.key = key
        self.region = region
        self.version = version
        super().__init__(f"Pricing key '{key}' not found for region '{region}' version '{version}'")


class PricingVersionNotFoundError(Exception):
    """Raised when pricing version doesn't exist"""
    def __init__(self, version: str):
        self.version = version
        super().__init__(f"Pricing version '{version}' not found")


@dataclass
class PricingContext:
    """
    Pricing context injected into formulas
    Provides dict-like access to pricing rates
    """
    version: str
    service: str
    region: str
    rates: Dict[str, Decimal]
    free_tier: Dict[str, Any]
    multipliers: Dict[str, Decimal]
    source: str
    fetched_at: datetime
    
    def __getattr__(self, key: str) -> Decimal:
        """Allow pricing.key_name access in formulas"""
        # Try rates first
        if key in self.rates:
            return self.rates[key]
        
        # Try free_tier
        if 'free_tier' in self.__dict__ and key in self.free_tier:
            return Decimal(str(self.free_tier[key]))
        
        # Try multipliers
        if 'multipliers' in self.__dict__ and key in self.multipliers:
            return self.multipliers[key]
        
        raise AttributeError(f"Pricing key not found: {key}")
    
    def get(self, key: str, default: Optional[Decimal] = None) -> Optional[Decimal]:
        """Dict-like get with default"""
        try:
            return self.__getattr__(key)
        except AttributeError:
            return default


class PricingResolver:
    """
    Production-grade pricing resolver
    NEVER calls external APIs - all data resolved locally from cache/DB
    """
    
    def __init__(self, redis_client=None):
        self.logger = logger.bind(component="pricing_resolver")
        self.redis = redis_client
        self._active_version_cache: Optional[str] = None
    
    async def get(
        self,
        key: str,
        region: str,
        service: str,
        version: Optional[str] = None,
        default: Optional[Decimal] = None
    ) -> Decimal:
        """
        Resolve pricing key to value (LOCAL ONLY)
        
        Args:
            key: Pricing key (e.g., "compute.gb_second")
            region: AWS region
            service: Service name
            version: Pricing version (defaults to latest active)
            default: Fallback value if key not found
        
        Returns:
            Decimal pricing value
        
        Raises:
            PricingKeyNotFoundError: If key missing and no default
            PricingVersionNotFoundError: If version doesn't exist
        """
        # Resolve version
        resolved_version = version or await self._get_active_version()
        
        # Try cache first
        cache_key = f"pricing:{resolved_version}:{service}:{region}"
        if self.redis:
            try:
                cached_data = await self.redis.hget(cache_key, key)
                if cached_data:
                    self.logger.debug("pricing_cache_hit", key=key, version=resolved_version)
                    return Decimal(cached_data.decode())
            except Exception as e:
                self.logger.warning("pricing_cache_error", error=str(e))
        
        # Fallback to database
        async with get_db() as db:
            stmt = select(PricingRate).where(
                PricingRate.version == resolved_version,
                PricingRate.service == service,
                PricingRate.region == region,
                PricingRate.pricing_key == key
            )
            result = await db.execute(stmt)
            pricing_rate = result.scalar_one_or_none()
            
            if pricing_rate:
                # Cache for next time
                if self.redis:
                    await self.redis.hset(cache_key, key, str(pricing_rate.rate))
                    await self.redis.expire(cache_key, 86400)  # 24 hours
                
                return pricing_rate.rate
        
        # Not found - use default or raise
        if default is not None:
            self.logger.warning(
                "pricing_key_not_found_using_default",
                key=key,
                region=region,
                version=resolved_version,
                default=default
            )
            return default
        
        raise PricingKeyNotFoundError(key, region, resolved_version)
    
    async def get_context(
        self,
        service: str,
        region: str,
        version: Optional[str] = None
    ) -> PricingContext:
        """
        Get full pricing context for service/region
        Returns PricingContext object for formula access
        """
        resolved_version = version or await self._get_active_version()
        
        # Try cache first
        cache_key = f"pricing:{resolved_version}:{service}:{region}"
        if self.redis:
            try:
                cached_rates = await self.redis.hgetall(cache_key)
                if cached_rates:
                    rates = {k.decode(): Decimal(v.decode()) for k, v in cached_rates.items()}
                    
                    # Get metadata from separate cache key
                    meta_key = f"pricing:meta:{resolved_version}:{service}:{region}"
                    meta_data = await self.redis.get(meta_key)
                    
                    if meta_data:
                        import json
                        meta = json.loads(meta_data.decode())
                        
                        return PricingContext(
                            version=resolved_version,
                            service=service,
                            region=region,
                            rates=rates,
                            free_tier=meta.get('free_tier', {}),
                            multipliers=meta.get('multipliers', {}),
                            source=meta.get('source', 'unknown'),
                            fetched_at=datetime.fromisoformat(meta['fetched_at'])
                        )
            except Exception as e:
                self.logger.warning("pricing_context_cache_error", error=str(e))
        
        # Fallback to database
        async with get_db() as db:
            # Get all rates for service/region
            stmt = select(PricingRate).where(
                PricingRate.version == resolved_version,
                PricingRate.service == service,
                PricingRate.region == region
            )
            result = await db.execute(stmt)
            pricing_rates = result.scalars().all()
            
            if not pricing_rates:
                self.logger.error(
                    "no_pricing_data_found",
                    service=service,
                    region=region,
                    version=resolved_version
                )
                # Return empty context rather than fail
                return PricingContext(
                    version=resolved_version,
                    service=service,
                    region=region,
                    rates={},
                    free_tier={},
                    multipliers={},
                    source='unknown',
                    fetched_at=datetime.now()
                )
            
            # Build rates dict
            rates = {pr.pricing_key: pr.rate for pr in pricing_rates}
            
            # Extract metadata from first rate
            first_rate = pricing_rates[0]
            
            # Cache for next time
            if self.redis:
                # Cache rates
                for key, value in rates.items():
                    await self.redis.hset(cache_key, key, str(value))
                await self.redis.expire(cache_key, 86400)
            
            return PricingContext(
                version=resolved_version,
                service=service,
                region=region,
                rates=rates,
                free_tier={},  # TODO: Load from pricing_metadata table
                multipliers={},  # TODO: Load from pricing_metadata table
                source='aws_pricing_api',
                fetched_at=first_rate.fetched_at
            )
    
    async def _get_active_version(self) -> str:
        """Get currently active pricing version"""
        # Check cache
        if self._active_version_cache:
            return self._active_version_cache
        
        # Check Redis
        if self.redis:
            try:
                cached_version = await self.redis.get("pricing:active_version")
                if cached_version:
                    version = cached_version.decode()
                    self._active_version_cache = version
                    return version
            except Exception as e:
                self.logger.warning("active_version_cache_error", error=str(e))
        
        # Fallback to database
        async with get_db() as db:
            stmt = select(PricingVersion).where(
                PricingVersion.is_active == True
            ).order_by(PricingVersion.created_at.desc())
            
            result = await db.execute(stmt)
            active_version = result.scalar_one_or_none()
            
            if not active_version:
                raise PricingVersionNotFoundError("No active pricing version found")
            
            # Cache for 5 minutes
            if self.redis:
                await self.redis.setex("pricing:active_version", 300, active_version.version)
            
            self._active_version_cache = active_version.version
            return active_version.version
    
    async def get_metadata(
        self,
        service: str,
        region: str,
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get pricing metadata (version, source, fetched_at)"""
        resolved_version = version or await self._get_active_version()
        
        async with get_db() as db:
            stmt = select(PricingRate).where(
                PricingRate.version == resolved_version,
                PricingRate.service == service,
                PricingRate.region == region
            ).limit(1)
            
            result = await db.execute(stmt)
            rate = result.scalar_one_or_none()
            
            if not rate:
                return {
                    'version': resolved_version,
                    'source': 'unknown',
                    'fetched_at': None
                }
            
            return {
                'version': resolved_version,
                'source': 'aws_pricing_api',
                'fetched_at': rate.fetched_at.isoformat(),
                'age_days': (datetime.now() - rate.fetched_at).days
            }
