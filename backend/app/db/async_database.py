"""
Async-only database access patterns.
Eliminates unsafe DB access with explicit transaction boundaries.
"""
import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import NullPool

from app.config import settings

logger = logging.getLogger(__name__)

# Global async engine (created once at startup)
async_engine: AsyncEngine = None
AsyncSessionLocal: async_sessionmaker = None


async def init_async_db() -> None:
    """
    Initialize async database engine.
    Called once at application startup.
    """
    global async_engine, AsyncSessionLocal
    
    if async_engine is not None:
        logger.warning("Async database already initialized")
        return
    
    # Create async engine
    async_engine = create_async_engine(
        settings.async_database_url,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=10,
        # Use NullPool for background tasks to avoid connection issues
        poolclass=NullPool if settings.app_env == "test" else None
    )
    
    # Create session factory
    AsyncSessionLocal = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    logger.info("Async database initialized")


async def close_async_db() -> None:
    """
    Close async database engine.
    Called at application shutdown.
    """
    global async_engine
    
    if async_engine is None:
        return
    
    await async_engine.dispose()
    logger.info("Async database closed")


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes.
    Provides async session with automatic cleanup.
    
    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_async_session)):
            # Use db here
            pass
    
    Guarantees:
    - No nested sessions
    - Automatic commit/rollback
    - Proper cleanup
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_async_db() first.")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_async_session_context():
    """
    Context manager for async sessions in background tasks.
    
    Usage:
        async with get_async_session_context() as db:
            # Use db here
            await db.commit()
    
    Guarantees:
    - Explicit transaction boundaries
    - No shared sessions
    - Proper cleanup
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_async_db() first.")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class AsyncTransactionContext:
    """
    Explicit transaction boundary context.
    
    Usage:
        async with AsyncTransactionContext(db) as tx:
            # All operations in this block are in one transaction
            await db.execute(...)
            await db.execute(...)
            # Auto-commit on success, rollback on error
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.transaction = None
    
    async def __aenter__(self):
        self.transaction = await self.session.begin()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.transaction.rollback()
            logger.error(f"Transaction rolled back due to {exc_type.__name__}: {exc_val}")
        else:
            await self.transaction.commit()
        
        return False  # Re-raise exception if any


# Read-only session for pricing queries
@asynccontextmanager
async def get_readonly_session():
    """
    Read-only session for pricing queries.
    
    Usage:
        async with get_readonly_session() as db:
            result = await db.execute(select(PricingDimension)...)
    
    Guarantees:
    - No writes allowed
    - Optimized for reads
    - Automatic cleanup
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_async_db() first.")
    
    async with AsyncSessionLocal() as session:
        try:
            # Set session to read-only
            await session.execute("SET TRANSACTION READ ONLY")
            yield session
        finally:
            await session.close()
