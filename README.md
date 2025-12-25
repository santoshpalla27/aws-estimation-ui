# AWS Terraform Cost Calculator

## What This Is

A **technically sound** AWS cost estimation tool that:
- Parses Terraform configurations semantically (not regex)
- Evaluates expressions, conditionals, and expansions correctly
- Uses real AWS pricing data with deterministic SKU matching
- Provides full audit trails and calculation transparency
- Enforces explicit usage models (no hardcoded assumptions)

## What This Is NOT

This is **NOT**:
- A billing-grade calculator
- A financial guarantee system
- A replacement for AWS Cost Explorer
- Suitable for contractual cost commitments

## Current Status

### ✅ Production-Grade Features

**Terraform Evaluation**:
- Semantic parsing with `python-hcl2`
- Expression evaluation (conditionals, arithmetic, functions)
- count/for_each expansion with explicit limits
- Fails hard on unresolved variables

**Pricing Determinism**:
- Normalized pricing tables (not JSON blobs)
- Unique constraints prevent duplicate SKUs
- Database-enforced single ACTIVE version
- Explicit status tracking (SUPPORTED/UNSUPPORTED/ERROR)

**Security**:
- Zip Slip protection
- Path traversal prevention
- File validation and size limits

**Auditability**:
- Full calculation steps stored
- Pricing rule IDs tracked
- Coverage percentage calculated
- Warnings and errors surfaced

### ⚠️ Known Limitations

**Usage Modeling**:
- Requires explicit usage pattern specification
- No automatic workload profiling
- Estimates only (not actual usage)

**Service Coverage**:
- EC2, RDS, S3, EBS, Lambda supported
- Other AWS services return UNSUPPORTED status
- Storage costs for RDS not included

**Pricing Accuracy**:
- Based on AWS Bulk Pricing API
- Updated manually (not real-time)
- Regional pricing variations may lag

## Architecture

```
Terraform Files
    ↓
Semantic Evaluator (expressions, conditionals)
    ↓
Resource Normalizer (with explicit usage model)
    ↓
Pricing Adapters (deterministic SQL queries)
    ↓
Cost Aggregator (explicit status)
    ↓
API Response (with coverage %)
```

## Key Design Decisions

### 1. No Defaults
- Usage model is **REQUIRED** (no 730-hour assumption)
- Operating system must be explicit
- Region must be specified

### 2. Fail Loudly
- Unresolved variables → Error
- Expansion limit exceeded → Error
- Missing usage model → Error
- Duplicate SKU → Database constraint violation

### 3. Explicit Status
- Every resource has status: SUPPORTED, UNSUPPORTED, or ERROR
- Aggregation uses explicit status (not cost inference)
- Coverage percentage always calculated

### 4. Database Integrity
- Unique constraints on pricing dimensions
- Single ACTIVE version enforced
- Atomic state transitions

## Usage

### 1. Start Services
```bash
docker-compose up -d
```

### 2. Apply Migrations
```bash
psql $DATABASE_URL -f backend/db/migrations/004_single_active_version_constraint.sql
psql $DATABASE_URL -f backend/db/migrations/005_pricing_unique_constraints.sql
```

### 3. Verify Constraints
```bash
python backend/tests/verify_constraints.py
```

### 4. Upload Terraform
```bash
curl -X POST -F "file=@infrastructure.tf" http://localhost:8000/api/upload
```

### 5. Analyze with Usage Model
```python
from app.models.usage_model import UsageModel

# Specify usage pattern (REQUIRED)
usage_model = UsageModel.business_hours()  # or always_on(), partial(hours), spot()

# Analysis will fail if usage_model not provided
```

## Deployment Checklist

- [ ] Database migrations applied
- [ ] Unique constraints verified
- [ ] Environment variables set
- [ ] Pricing data ingested
- [ ] Single ACTIVE version confirmed
- [ ] Tests passing
- [ ] Coverage warnings displayed in UI

## Testing

```bash
# Run all tests
pytest backend/tests/ -v

# Verify constraints
python backend/tests/verify_constraints.py

# Test Terraform evaluation
pytest backend/tests/test_terraform_evaluator.py -v
```

## Limitations & Disclaimers

1. **Estimates Only**: Costs are estimates based on specified usage patterns
2. **Manual Updates**: Pricing data requires manual ingestion
3. **Limited Services**: Only 5 AWS services currently supported
4. **No Actual Usage**: Cannot profile real workload patterns
5. **Regional Lag**: Some regional pricing may not be current

## Contributing

This is a portfolio/learning project demonstrating:
- Production-grade architecture
- Database integrity constraints
- Semantic parsing
- Explicit error handling
- Full auditability

Not intended for:
- Financial commitments
- Billing accuracy guarantees
- Production cost management

## License

MIT - Use at your own risk. No warranties provided.
