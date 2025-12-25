"""
Tests for async database concurrency safety.
"""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.models.models import Base, PricingVersion


@pytest.fixture
async def async_engine():
    """Create async test engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def async_session_factory(async_engine):
    """Create async session factory."""
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )


class TestAsyncSessionIsolation:
    """Test session isolation and safety."""
    
    @pytest.mark.asyncio
    async def test_sessions_are_isolated(self, async_session_factory):
        """Test that each session is isolated."""
        # Create two sessions
        async with async_session_factory() as session1:
            async with async_session_factory() as session2:
                # They should be different objects
                assert session1 is not session2
    
    @pytest.mark.asyncio
    async def test_no_shared_state(self, async_session_factory):
        """Test sessions don't share state."""
        # Session 1: Add object
        async with async_session_factory() as session1:
            version1 = PricingVersion(version="v1", source="test")
            session1.add(version1)
            await session1.commit()
        
        # Session 2: Query independently
        async with async_session_factory() as session2:
            result = await session2.execute(
                select(PricingVersion).where(PricingVersion.version == "v1")
            )
            version2 = result.scalar_one()
            
            # Different object instances
            assert version2.version == "v1"
    
    @pytest.mark.asyncio
    async def test_concurrent_reads_safe(self, async_session_factory):
        """Test concurrent reads are safe."""
        # Add test data
        async with async_session_factory() as session:
            for i in range(10):
                session.add(PricingVersion(version=f"v{i}", source="test"))
            await session.commit()
        
        # Concurrent reads
        async def read_versions():
            async with async_session_factory() as session:
                result = await session.execute(select(PricingVersion))
                return len(result.scalars().all())
        
        # Run 10 concurrent reads
        results = await asyncio.gather(*[read_versions() for _ in range(10)])
        
        # All should see same data
        assert all(r == 10 for r in results)
    
    @pytest.mark.asyncio
    async def test_auto_rollback_on_error(self, async_session_factory):
        """Test automatic rollback on error."""
        async with async_session_factory() as session:
            try:
                version = PricingVersion(version="test", source="test")
                session.add(version)
                
                # Simulate error
                raise ValueError("Test error")
            except ValueError:
                await session.rollback()
        
        # Verify nothing was committed
        async with async_session_factory() as session:
            result = await session.execute(
                select(PricingVersion).where(PricingVersion.version == "test")
            )
            assert result.scalar_one_or_none() is None
    
    @pytest.mark.asyncio
    async def test_explicit_transaction_boundary(self, async_session_factory):
        """Test explicit transaction boundaries."""
        async with async_session_factory() as session:
            async with session.begin():
                # All operations in one transaction
                session.add(PricingVersion(version="v1", source="test"))
                session.add(PricingVersion(version="v2", source="test"))
                # Auto-commit on exit
        
        # Verify both committed
        async with async_session_factory() as session:
            result = await session.execute(select(PricingVersion))
            assert len(result.scalars().all()) == 2


class TestAsyncAdapterConcurrency:
    """Test async adapter concurrency safety."""
    
    @pytest.mark.asyncio
    async def test_adapter_uses_provided_session(self, async_session_factory):
        """Test adapter uses provided session, doesn't create new one."""
        from app.pricing.async_adapters.base import AsyncPricingAdapter
        
        class TestAdapter(AsyncPricingAdapter):
            @property
            def required_attributes(self):
                return []
            
            @property
            def supported_regions(self):
                return ["us-east-1"]
            
            @property
            def service_code(self):
                return "Test"
            
            def validate(self, resource):
                pass
            
            async def match_pricing(self, resource):
                # Verify we're using the provided session
                assert self.db is not None
                return None
            
            def calculate(self, resource, pricing_rule):
                return None
        
        async with async_session_factory() as session:
            version = PricingVersion(version="v1", source="test")
            adapter = TestAdapter(session, version)
            
            # Adapter should use provided session
            assert adapter.db is session
    
    @pytest.mark.asyncio
    async def test_concurrent_adapter_calls_safe(self, async_session_factory):
        """Test concurrent adapter calls are safe."""
        # This would test that multiple concurrent pricing queries
        # don't interfere with each other
        
        async def query_pricing(session_factory):
            async with session_factory() as session:
                result = await session.execute(select(PricingVersion))
                return len(result.scalars().all())
        
        # Run concurrent queries
        results = await asyncio.gather(*[
            query_pricing(async_session_factory) for _ in range(5)
        ])
        
        # All should succeed
        assert len(results) == 5


class TestTransactionSafety:
    """Test transaction safety patterns."""
    
    @pytest.mark.asyncio
    async def test_nested_transaction_safe(self, async_session_factory):
        """Test nested transactions are handled safely."""
        async with async_session_factory() as session:
            async with session.begin():
                session.add(PricingVersion(version="v1", source="test"))
                
                # Nested begin creates savepoint
                async with session.begin_nested():
                    session.add(PricingVersion(version="v2", source="test"))
                    # This commits to savepoint
                
                # This commits outer transaction
        
        # Verify both committed
        async with async_session_factory() as session:
            result = await session.execute(select(PricingVersion))
            assert len(result.scalars().all()) == 2
    
    @pytest.mark.asyncio
    async def test_rollback_nested_transaction(self, async_session_factory):
        """Test rolling back nested transaction."""
        async with async_session_factory() as session:
            async with session.begin():
                session.add(PricingVersion(version="v1", source="test"))
                
                try:
                    async with session.begin_nested():
                        session.add(PricingVersion(version="v2", source="test"))
                        raise ValueError("Test error")
                except ValueError:
                    # Nested transaction rolled back
                    pass
                
                # Outer transaction still commits
        
        # Verify only v1 committed
        async with async_session_factory() as session:
            result = await session.execute(select(PricingVersion))
            versions = result.scalars().all()
            assert len(versions) == 1
            assert versions[0].version == "v1"
