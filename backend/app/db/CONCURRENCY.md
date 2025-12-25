# Database Concurrency Safety

## Strategy: Option B - All Async

All database access is **async-only** to eliminate unsafe patterns.

## Core Principles

### ✅ Safe Patterns

- **All pricing reads are async**
- **No sync DB calls in API handlers**
- **Explicit transaction boundaries**
- **No nested sessions**
- **No shared sessions across threads**

### ❌ Unsafe Patterns (Eliminated)

```python
# ❌ NEVER: Sync DB call in async handler
@app.get("/endpoint")
async def handler():
    with sync_session() as db:  # WRONG!
        result = db.query(...)

# ❌ NEVER: Shared session
session = SessionLocal()  # WRONG!
@app.get("/endpoint1")
async def handler1():
    session.query(...)  # Shared across requests!

# ❌ NEVER: Nested sessions
async with get_session() as db1:
    async with get_session() as db2:  # WRONG!
        ...
```

## Database Initialization

```python
from app.db.async_database import init_async_db, close_async_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_async_db()
    yield
    # Shutdown
    await close_async_db()

app = FastAPI(lifespan=lifespan)
```

## Usage Patterns

### 1. API Handler (Dependency Injection)

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.async_database import get_async_session

@app.get("/resources")
async def get_resources(db: AsyncSession = Depends(get_async_session)):
    # Session automatically managed
    result = await db.execute(select(Resource))
    resources = result.scalars().all()
    return resources
    # Auto-commit on success, rollback on error
```

**Guarantees**:
- ✅ New session per request
- ✅ Auto-commit/rollback
- ✅ Automatic cleanup
- ✅ No nested sessions

### 2. Background Task (Context Manager)

```python
from app.db.async_database import get_async_session_context

async def background_task():
    async with get_async_session_context() as db:
        # Explicit transaction
        result = await db.execute(select(Data))
        await db.commit()
    # Session closed automatically
```

**Guarantees**:
- ✅ Isolated session
- ✅ Explicit commit
- ✅ Proper cleanup

### 3. Explicit Transaction Boundary

```python
from app.db.async_database import AsyncTransactionContext

async def complex_operation(db: AsyncSession):
    async with AsyncTransactionContext(db) as tx:
        # All operations in one transaction
        await db.execute(insert(Table1).values(...))
        await db.execute(update(Table2).values(...))
        # Auto-commit on success, rollback on error
```

**Guarantees**:
- ✅ Atomic operations
- ✅ Explicit boundary
- ✅ Auto-rollback on error

### 4. Read-Only Session (Pricing Queries)

```python
from app.db.async_database import get_readonly_session

async def get_pricing():
    async with get_readonly_session() as db:
        result = await db.execute(
            select(PricingDimension).where(...)
        )
        return result.scalars().all()
```

**Guarantees**:
- ✅ Read-only transaction
- ✅ Optimized for reads
- ✅ No accidental writes

## Async Pricing Adapters

```python
from app.pricing.async_adapters.base import AsyncPricingAdapter

class AsyncEC2Adapter(AsyncPricingAdapter):
    def validate(self, resource):
        # Sync validation (no DB)
        pass
    
    async def match_pricing(self, resource):
        # Async DB query
        dimension = await self._query_pricing_dimension(...)
        return PricingRule(...)
    
    def calculate(self, resource, pricing_rule):
        # Sync calculation (no DB)
        return CostResult(...)

# Usage in API handler
@app.post("/calculate")
async def calculate(
    resource: dict,
    db: AsyncSession = Depends(get_async_session)
):
    adapter = AsyncEC2Adapter(db, pricing_version)
    result = await adapter.calculate_cost(resource)
    return result
```

## Session Lifecycle

### API Request Flow

```
Request → get_async_session()
       → New AsyncSession created
       → Handler executes
       → Success: commit()
       → Error: rollback()
       → Finally: close()
```

### Background Task Flow

```
Task → get_async_session_context()
    → New AsyncSession created
    → Task executes
    → Explicit commit()
    → Finally: close()
```

## Transaction Boundaries

### Implicit (API Handlers)

```python
@app.post("/create")
async def create(db: AsyncSession = Depends(get_async_session)):
    # Transaction starts automatically
    db.add(Resource(...))
    # Transaction commits automatically on return
```

### Explicit (Complex Operations)

```python
async def multi_step_operation(db: AsyncSession):
    async with AsyncTransactionContext(db):
        # Step 1
        await db.execute(...)
        
        # Step 2
        await db.execute(...)
        
        # All committed together
```

## Error Handling

```python
@app.post("/endpoint")
async def handler(db: AsyncSession = Depends(get_async_session)):
    try:
        result = await db.execute(...)
        # Success: auto-commit
        return result
    except Exception as e:
        # Error: auto-rollback
        raise HTTPException(status_code=500, detail=str(e))
```

## Testing

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def async_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with AsyncSession(engine) as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_query(async_db):
    result = await async_db.execute(select(Model))
    assert result is not None
```

## Configuration

```python
# config.py
class Settings(BaseSettings):
    @property
    def async_database_url(self) -> str:
        """Async database URL."""
        return self.database_url.replace(
            "postgresql://",
            "postgresql+asyncpg://"
        )
```

## Migration from Sync

### Before (Unsafe)

```python
from app.db.database import get_sync_session

@app.get("/data")
async def get_data():
    with next(get_sync_session()) as db:  # ❌ Blocking!
        result = db.query(Model).all()
        return result
```

### After (Safe)

```python
from app.db.async_database import get_async_session

@app.get("/data")
async def get_data(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(Model))
    return result.scalars().all()
```

## Best Practices

1. **Always use dependency injection** for API handlers
2. **Always use context managers** for background tasks
3. **Never share sessions** across requests/tasks
4. **Never nest sessions** - one session per operation
5. **Use read-only sessions** for pricing queries
6. **Explicit transactions** for multi-step operations
7. **Async all the way** - no sync DB calls in async code

## Monitoring

### Check for Unsafe Patterns

```python
# ❌ Look for these in code reviews
- SessionLocal() outside dependency
- sync_session in async functions
- Shared session variables
- Nested session contexts
```

### Connection Pool Monitoring

```python
# Log pool stats
logger.info(f"Pool size: {engine.pool.size()}")
logger.info(f"Checked out: {engine.pool.checkedout()}")
```

## Summary

- ✅ **All async** - No sync DB calls in API handlers
- ✅ **Dependency injection** - Sessions managed automatically
- ✅ **Context managers** - Explicit lifecycle for background tasks
- ✅ **Transaction boundaries** - Explicit when needed
- ✅ **No nested sessions** - One session per operation
- ✅ **No shared sessions** - Isolated per request/task
- ✅ **Read-only sessions** - Optimized pricing queries
