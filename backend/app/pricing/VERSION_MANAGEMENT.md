# Pricing Version State Management

## Overview

Guarantees **exactly one ACTIVE pricing version** at any time through database constraints and atomic state transitions.

## State Machine

```
DRAFT → VALIDATED → ACTIVE → ARCHIVED
```

### States

- **DRAFT**: Initial state, data being ingested
- **VALIDATED**: Data validated, ready for activation
- **ACTIVE**: Currently used for cost calculations (ONLY ONE ALLOWED)
- **ARCHIVED**: Historical version, no longer active

## Database Constraints

### Single Active Version

```sql
CREATE UNIQUE INDEX idx_pricing_versions_single_active 
ON pricing_versions (status) 
WHERE status = 'ACTIVE';
```

This **database-level constraint** ensures:
- ❌ Cannot have 2+ ACTIVE versions
- ✅ Enforced by PostgreSQL (not application logic)
- ✅ Prevents race conditions

### State Transition Timestamps

```sql
-- VALIDATED/ACTIVE/ARCHIVED must have validated_at
CHECK (
    (status IN ('VALIDATED', 'ACTIVE', 'ARCHIVED') AND validated_at IS NOT NULL) OR
    (status = 'DRAFT' AND validated_at IS NULL)
)

-- ACTIVE/ARCHIVED must have activated_at
CHECK (
    (status IN ('ACTIVE', 'ARCHIVED') AND activated_at IS NOT NULL) OR
    (status IN ('DRAFT', 'VALIDATED') AND activated_at IS NULL)
)

-- ARCHIVED must have archived_at
CHECK (
    (status = 'ARCHIVED' AND archived_at IS NOT NULL) OR
    (status IN ('DRAFT', 'VALIDATED', 'ACTIVE') AND archived_at IS NULL)
)
```

## API

### Create DRAFT Version

```python
from app.pricing.version_manager import PricingVersionManager

manager = PricingVersionManager(db)

version = manager.create_draft_version(
    version_name="2024-01-01",
    source="AWS Bulk API"
)
# version.status == DRAFT
```

### Validate Version

```python
validated = manager.validate_version(
    version_id=1,
    validated_by="system",
    min_dimensions=100
)
# validated.status == VALIDATED
# validated.validated_at is set
```

Validation checks:
- Minimum pricing dimensions (default: 100)
- At least one service present
- Records errors if validation fails

### Activate Version (Atomic)

```python
active = manager.activate_version(
    version_id=1,
    activated_by="admin"
)
# active.status == ACTIVE
# Previous ACTIVE version is now ARCHIVED
```

**Atomic transaction**:
1. Archive current ACTIVE version (if exists)
2. Activate new version
3. Both in single transaction

### Archive Version

```python
archived = manager.archive_version(
    version_id=1,
    archived_by="admin"
)
# archived.status == ARCHIVED
```

Cannot archive ACTIVE version directly - must activate another first.

### Get Active Version

```python
active = manager.get_active_version()
# Returns the ONE active version or None
```

**CRITICAL**: Cost calculations MUST ONLY use this version.

## State Transitions

### Valid Transitions

```
DRAFT → VALIDATED → ACTIVE → ARCHIVED
  ↓                    ↓
ARCHIVED          ARCHIVED
```

### Invalid Transitions

- ❌ ARCHIVED → ACTIVE
- ❌ ACTIVE → DRAFT
- ❌ Skip VALIDATED (unless force=True)

## Error Handling

```python
from app.pricing.version_manager import (
    VersionTransitionError,      # Invalid state transition
    ValidationIncompleteError,    # Validation failed
    MultipleActiveVersionsError   # DB constraint violated
)

try:
    manager.activate_version(version_id, "admin")
except VersionTransitionError as e:
    print(f"Invalid transition: {e}")
except ValidationIncompleteError as e:
    print(f"Not validated: {e}")
```

## Ingestion Workflow

```python
# 1. Create DRAFT version
version = manager.create_draft_version("2024-01-01", "AWS")

# 2. Ingest pricing data
for service in services:
    # Add PricingDimension records to version
    ...

# 3. Validate
validated = manager.validate_version(version.id, "system")

# 4. Activate (atomic)
active = manager.activate_version(validated.id, "admin")
```

## Cost Calculation Rule

**MANDATORY**: Cost calculations may ONLY use:

```python
active_version = manager.get_active_version()

if not active_version:
    raise Exception("No active pricing version")

# Use active_version.id for all pricing queries
pricing = db.query(PricingDimension).filter(
    PricingDimension.version_id == active_version.id,
    ...
)
```

## Testing

```bash
pytest backend/tests/test_pricing_version_manager.py -v
```

Tests cover:
- ✅ State transitions
- ✅ Validation logic
- ✅ Atomic activation
- ✅ Single active constraint
- ✅ Error cases

## Migration

Run migration to add state management:

```bash
psql -d aws_cost_calculator -f backend/db/migrations/002_pricing_version_states.sql
```

This adds:
- `status` enum column
- Lifecycle timestamp columns
- Unique constraint on ACTIVE status
- Triggers to sync `is_active` with `status`

## Monitoring

### Check Active Version

```sql
SELECT id, version, status, activated_at, activated_by
FROM pricing_versions
WHERE status = 'ACTIVE';
```

Should return exactly 1 row.

### Version History

```sql
SELECT id, version, status, created_at, validated_at, activated_at
FROM pricing_versions
ORDER BY created_at DESC
LIMIT 10;
```

### Detect Anomalies

```sql
-- Should return 0 or 1
SELECT COUNT(*) FROM pricing_versions WHERE status = 'ACTIVE';

-- Should never happen
SELECT COUNT(*) FROM pricing_versions WHERE is_active = true AND status != 'ACTIVE';
```

## Best Practices

1. **Always use version manager** - Don't manipulate status directly
2. **Validate before activate** - Use `force=True` only in emergencies
3. **Atomic activation** - Never manually archive + activate
4. **Check active version** - Always verify before cost calculations
5. **Monitor constraints** - Alert if multiple ACTIVE versions detected
6. **Audit trail** - Record who/when for all transitions

## Summary

- ✅ **One ACTIVE version** - Enforced by database constraint
- ✅ **Atomic transitions** - Archive + Activate in single transaction
- ✅ **DRAFT ingestion** - All new data goes to DRAFT first
- ✅ **Explicit validation** - Must validate before activation
- ✅ **Audit trail** - Track who/when for all state changes
- ✅ **Runtime rule** - Cost calculations ONLY use ACTIVE version
