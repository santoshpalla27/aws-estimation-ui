"""
Unit Tests for PricingResolver
Tests local-only pricing resolution, caching, and error handling
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from services.pricing_resolver import (
    PricingResolver,
    PricingContext,
    PricingKeyNotFoundError,
    PricingVersionNotFoundError
)


class TestPricingContext:
    """Test PricingContext dataclass"""
    
    def test_pricing_context_attribute_access(self):
        """Test __getattr__ for pricing.key_name access"""
        context = PricingContext(
            version="2024-12",
            service="AWSLambda",
            region="us-east-1",
            rates={"gb_second": Decimal("0.0000166667"), "request": Decimal("0.0000002")},
            free_tier={"gb_seconds": 400000, "requests": 1000000},
            multipliers={"x86_64": Decimal("1.0"), "arm64": Decimal("0.8")},
            source="aws_pricing_api",
            fetched_at=datetime(2024, 12, 1)
        )
        
        assert context.gb_second == Decimal("0.0000166667")
        assert context.request == Decimal("0.0000002")
    
    def test_pricing_context_get_with_default(self):
        """Test get() method with default value"""
        context = PricingContext(
            version="2024-12",
            service="AWSLambda",
            region="us-east-1",
            rates={"gb_second": Decimal("0.0000166667")},
            free_tier={},
            multipliers={},
            source="aws_pricing_api",
            fetched_at=datetime(2024, 12, 1)
        )
        
        assert context.get("gb_second") == Decimal("0.0000166667")
        assert context.get("missing_key", Decimal("0.0")) == Decimal("0.0")
        assert context.get("missing_key") is None


@pytest.mark.asyncio
class TestPricingResolver:
    """Test PricingResolver class"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        redis = AsyncMock()
        redis.hget = AsyncMock(return_value=None)
        redis.hgetall = AsyncMock(return_value={})
        redis.get = AsyncMock(return_value=None)
        redis.hset = AsyncMock()
        redis.setex = AsyncMock()
        redis.expire = AsyncMock()
        return redis
    
    @pytest.fixture
    def resolver(self, mock_redis):
        """Create PricingResolver instance"""
        return PricingResolver(redis_client=mock_redis)
    
    async def test_get_from_cache(self, resolver, mock_redis):
        """Test successful pricing retrieval from Redis cache"""
        mock_redis.hget.return_value = b"0.0000166667"
        
        result = await resolver.get(
            key="gb_second",
            region="us-east-1",
            service="AWSLambda",
            version="2024-12"
        )
        
        assert result == Decimal("0.0000166667")
        mock_redis.hget.assert_called_once()
    
    async def test_get_with_default(self, resolver):
        """Test get() with default value when key not found"""
        with patch('services.pricing_resolver.get_db'):
            result = await resolver.get(
                key="missing_key",
                region="us-east-1",
                service="AWSLambda",
                version="2024-12",
                default=Decimal("0.0")
            )
            
            assert result == Decimal("0.0")
    
    async def test_get_raises_error_without_default(self, resolver):
        """Test get() raises error when key not found and no default"""
        with patch('services.pricing_resolver.get_db'):
            with pytest.raises(PricingKeyNotFoundError) as exc_info:
                await resolver.get(
                    key="missing_key",
                    region="us-east-1",
                    service="AWSLambda",
                    version="2024-12"
                )
            
            assert exc_info.value.key == "missing_key"
            assert exc_info.value.region == "us-east-1"
    
    async def test_get_context_from_cache(self, resolver, mock_redis):
        """Test get_context() from Redis cache"""
        mock_redis.hgetall.return_value = {
            b"gb_second": b"0.0000166667",
            b"request": b"0.0000002"
        }
        mock_redis.get.return_value = b'{"free_tier": {}, "multipliers": {}, "source": "aws_pricing_api", "fetched_at": "2024-12-01T00:00:00"}'
        
        context = await resolver.get_context(
            service="AWSLambda",
            region="us-east-1",
            version="2024-12"
        )
        
        assert context.version == "2024-12"
        assert context.service == "AWSLambda"
        assert context.region == "us-east-1"
        assert "gb_second" in context.rates
        assert context.rates["gb_second"] == Decimal("0.0000166667")
    
    async def test_get_context_empty_returns_empty_context(self, resolver):
        """Test get_context() returns empty context when no data found"""
        with patch('services.pricing_resolver.get_db'):
            context = await resolver.get_context(
                service="UnknownService",
                region="us-east-1",
                version="2024-12"
            )
            
            assert context.rates == {}
            assert context.free_tier == {}
            assert context.multipliers == {}
    
    async def test_cache_fallback_to_db(self, resolver, mock_redis):
        """Test fallback to database when cache misses"""
        mock_redis.hget.return_value = None
        
        with patch('services.pricing_resolver.get_db') as mock_db:
            # Mock database query
            mock_rate = Mock()
            mock_rate.rate = Decimal("0.0000166667")
            
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = mock_rate
            
            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            
            mock_db.return_value = mock_session
            
            result = await resolver.get(
                key="gb_second",
                region="us-east-1",
                service="AWSLambda",
                version="2024-12"
            )
            
            assert result == Decimal("0.0000166667")
            # Should cache the result
            mock_redis.hset.assert_called_once()


@pytest.mark.asyncio
class TestPricingResolverIntegration:
    """Integration tests with real database (requires test DB)"""
    
    @pytest.mark.integration
    async def test_full_pricing_resolution_flow(self):
        """Test complete flow from database to pricing context"""
        # This would require a test database with seeded data
        # Skipped in unit tests, run separately in integration tests
        pass


def test_pricing_key_not_found_error():
    """Test PricingKeyNotFoundError exception"""
    error = PricingKeyNotFoundError("gb_second", "us-east-1", "2024-12")
    
    assert error.key == "gb_second"
    assert error.region == "us-east-1"
    assert error.version == "2024-12"
    assert "gb_second" in str(error)


def test_pricing_version_not_found_error():
    """Test PricingVersionNotFoundError exception"""
    error = PricingVersionNotFoundError("2024-13")
    
    assert error.version == "2024-13"
    assert "2024-13" in str(error)
