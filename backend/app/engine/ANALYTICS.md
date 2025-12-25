# Cost Analytics with Explicit Resource Status

## Overview

Accurate cost aggregation with **explicit resource status** - no inference from `monthly_cost == 0`.

## Resource Status

Every resource MUST have explicit status:

```python
class ResourceStatus(Enum):
    SUPPORTED = "SUPPORTED"      # Successfully calculated
    UNSUPPORTED = "UNSUPPORTED"  # Resource type not supported
    ERROR = "ERROR"              # Calculation failed
```

## Aggregation Rules

| Status | Included in Totals | Reported |
|--------|-------------------|----------|
| **SUPPORTED** | ✅ Yes | In main results |
| **UNSUPPORTED** | ❌ No | Separate list with reasons |
| **ERROR** | ❌ No | Separate list with errors |

## ResourceCostResult

```python
@dataclass
class ResourceCostResult:
    resource_id: str
    resource_type: str
    resource_name: str
    status: ResourceStatus  # REQUIRED
    
    # Valid only if status == SUPPORTED
    monthly_cost: Decimal = Decimal("0")
    pricing_rule_id: Optional[int] = None
    calculation_steps: List[Dict] = []
    
    # Status details
    error_message: Optional[str] = None          # Required if ERROR
    unsupported_reason: Optional[str] = None     # Required if UNSUPPORTED
```

### Validation Rules

**SUPPORTED** resources MUST have:
- `pricing_rule_id` (not None)
- `calculation_steps` (not empty)

**UNSUPPORTED** resources MUST have:
- `unsupported_reason` (explaining why)

**ERROR** resources MUST have:
- `error_message` (explaining what failed)

## Usage

### Creating Results

```python
from app.engine.analytics import ResourceCostResult, ResourceStatus

# Supported resource
supported = ResourceCostResult(
    resource_id="ec2-1",
    resource_type="aws_instance",
    resource_name="web-server",
    status=ResourceStatus.SUPPORTED,
    monthly_cost=Decimal("100.50"),
    pricing_rule_id=123,
    calculation_steps=[{"step": "hourly * 730"}],
    service_code="AmazonEC2",
    region="us-east-1"
)

# Unsupported resource
unsupported = ResourceCostResult(
    resource_id="vpc-1",
    resource_type="aws_vpc",
    resource_name="main-vpc",
    status=ResourceStatus.UNSUPPORTED,
    unsupported_reason="VPC resources have no direct cost",
    service_code="AmazonVPC"
)

# Error resource
error = ResourceCostResult(
    resource_id="db-1",
    resource_type="aws_db_instance",
    resource_name="database",
    status=ResourceStatus.ERROR,
    error_message="PricingMatchError: No pricing for db.t3.xlarge in eu-north-1",
    service_code="AmazonRDS"
)
```

### Aggregating Results

```python
from app.engine.analytics import CostAggregator

results = [supported, unsupported, error]
aggregator = CostAggregator(results)
analytics = aggregator.aggregate()

# Access totals (SUPPORTED only)
print(f"Total: ${analytics.total_monthly_cost}")
print(f"Supported: {analytics.total_supported_resources}")
print(f"Coverage: {analytics.coverage_percentage}%")

# Access breakdowns (SUPPORTED only)
print(analytics.cost_by_service)
print(analytics.cost_by_region)

# Access unsupported resources
for r in analytics.unsupported_resources:
    print(f"{r.resource_name}: {r.unsupported_reason}")

# Access error resources
for r in analytics.error_resources:
    print(f"{r.resource_name}: {r.error_message}")
```

## API Response Format

```json
{
  "summary": {
    "total_monthly_cost": 250.50,
    "total_resources": 10,
    "supported_resources": 7,
    "unsupported_resources": 2,
    "error_resources": 1,
    "coverage_percentage": 70.0
  },
  "breakdowns": {
    "by_service": {
      "AmazonEC2": 150.00,
      "AmazonS3": 50.50,
      "AmazonRDS": 50.00
    },
    "by_region": {
      "us-east-1": 200.00,
      "us-west-2": 50.50
    },
    "by_resource_type": {
      "aws_instance": 150.00,
      "aws_s3_bucket": 50.50,
      "aws_db_instance": 50.00
    }
  },
  "supported_resources": [
    {
      "resource_id": "ec2-1",
      "resource_type": "aws_instance",
      "resource_name": "web-server",
      "status": "SUPPORTED",
      "monthly_cost": 100.50,
      "pricing_rule_id": 123,
      "calculation_steps": [...],
      "service_code": "AmazonEC2",
      "region": "us-east-1"
    }
  ],
  "unsupported_resources": [
    {
      "resource_id": "vpc-1",
      "resource_type": "aws_vpc",
      "resource_name": "main-vpc",
      "reason": "VPC resources have no direct cost",
      "service_code": "AmazonVPC"
    }
  ],
  "error_resources": [
    {
      "resource_id": "db-1",
      "resource_type": "aws_db_instance",
      "resource_name": "database",
      "error": "PricingMatchError: No pricing found",
      "service_code": "AmazonRDS"
    }
  ],
  "warnings": [
    "2 resource(s) not supported by pricing engine",
    "1 resource(s) failed cost calculation",
    "Pricing coverage: 70.0% - some resources excluded from totals"
  ]
}
```

## UI Requirements

### Display Sections

**1. Cost Summary**
- Total monthly cost (SUPPORTED only)
- Resource counts by status
- Coverage percentage

**2. Cost Breakdowns**
- By service (chart)
- By region (chart)
- By resource type (table)

**3. Unsupported Resources**
- List with reasons
- Grouped by reason
- Service code shown

**4. Error Resources**
- List with error messages
- Grouped by error type
- Service code shown

**5. Missing Coverage**
- Services with unsupported resources
- Count per service

## Helper Functions

### Unsupported Summary

```python
summary = aggregator.get_unsupported_summary()
# {
#   "VPC resources have no direct cost": ["aws_vpc.main", "aws_vpc.backup"],
#   "Custom resource type": ["custom_resource.app"]
# }
```

### Error Summary

```python
summary = aggregator.get_error_summary()
# {
#   "PricingMatchError": ["aws_db_instance.db1", "aws_db_instance.db2"],
#   "ValidationError": ["aws_instance.web"]
# }
```

### Missing Coverage

```python
coverage = aggregator.get_missing_coverage()
# {
#   "AmazonVPC": 2,
#   "AmazonCloudFront": 1
# }
```

## Critical Rules

### ❌ NO Inference from Zero Cost

```python
# WRONG: Inferring status from cost
if monthly_cost == 0:
    status = UNSUPPORTED  # ❌ NEVER DO THIS

# RIGHT: Explicit status
status = ResourceStatus.SUPPORTED  # Even if cost is 0 (free tier)
monthly_cost = Decimal("0")
```

### ✅ Explicit Status Always

```python
# Every resource MUST have explicit status
result = ResourceCostResult(
    ...,
    status=ResourceStatus.SUPPORTED,  # REQUIRED
    ...
)
```

### ✅ Status-Specific Requirements

```python
# SUPPORTED requires pricing_rule_id and calculation_steps
if status == SUPPORTED:
    assert pricing_rule_id is not None
    assert len(calculation_steps) > 0

# UNSUPPORTED requires reason
if status == UNSUPPORTED:
    assert unsupported_reason is not None

# ERROR requires message
if status == ERROR:
    assert error_message is not None
```

## Testing

```bash
pytest backend/tests/test_cost_analytics.py -v
```

Tests cover:
- ✅ Resource status validation
- ✅ Aggregation rules (include/exclude)
- ✅ Zero-cost SUPPORTED resources
- ✅ Breakdown calculations
- ✅ Summary functions

## Benefits

- ✅ **No ambiguity** - Status is always explicit
- ✅ **Accurate totals** - Only SUPPORTED resources counted
- ✅ **Clear reporting** - Unsupported and errors shown separately
- ✅ **Coverage metrics** - Know exactly what's missing
- ✅ **No inference** - Zero cost doesn't mean unsupported
