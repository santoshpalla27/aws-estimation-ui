# Strict Pricing Adapter Contract

## Overview

A rigorous pricing adapter contract system that **makes silent miscalculations impossible** through mandatory validation, explicit error handling, and comprehensive audit trails.

## Core Principles

### ❌ NO Silent Failures
- Missing attribute → `ValidationError`
- Unsupported region → `ValidationError`
- No pricing rule → `PricingMatchError`
- Unit mismatch → `UnitMismatchError`
- Invalid calculation → `CalculationError`

### ✅ Explicit Everything
- Every cost must have calculation steps
- Every result must declare free tier status
- Every error must be raised (never return None)
- Every validation must be performed

## Mandatory Interface

```python
class PricingAdapter(ABC):
    @property
    @abstractmethod
    def required_attributes(self) -> List[str]:
        """Attributes that MUST be present."""
        pass
    
    @property
    @abstractmethod
    def supported_regions(self) -> List[str]:
        """Regions that MUST be supported."""
        pass
    
    @abstractmethod
    def validate(resource) -> None:
        """MUST raise ValidationError if invalid."""
        pass
    
    @abstractmethod
    def match_pricing(resource) -> PricingRule:
        """MUST raise PricingMatchError if no match."""
        pass
    
    @abstractmethod
    def calculate(resource, pricing_rule) -> CostResult:
        """MUST return CostResult with calculation steps."""
        pass
```

## CostResult Contract

Every cost calculation MUST return a `CostResult` with:

```python
@dataclass
class CostResult:
    monthly_cost: Decimal           # REQUIRED, >= 0
    pricing_rule_id: int            # REQUIRED, never None
    unit: str                       # REQUIRED, e.g., "USD/month"
    calculation_steps: List[Step]   # REQUIRED, never empty
    free_tier_applied: FreeTierStatus  # REQUIRED, explicit enum
    warnings: List[str]             # Optional
    resource_id: str                # Optional
```

### Validation on Creation

```python
# These all FAIL at CostResult creation:
CostResult(monthly_cost=-10, ...)           # Negative cost
CostResult(pricing_rule_id=None, ...)       # Missing rule ID
CostResult(calculation_steps=[], ...)       # No audit trail
CostResult(free_tier_applied=None, ...)     # Implicit status
```

## Calculation Steps

Every calculation MUST show its work:

```python
@dataclass
class CalculationStep:
    description: str    # Human-readable step
    formula: str        # Mathematical formula
    inputs: Dict        # Input values used
    result: Decimal     # Step result
    unit: str          # Result unit
```

### Example

```python
steps = [
    CalculationStep(
        description="Hourly instance rate",
        formula="price_per_unit",
        inputs={"instance_type": "t3.micro", "region": "us-east-1"},
        result=Decimal("0.0116"),
        unit="USD/hour"
    ),
    CalculationStep(
        description="Hours in month",
        formula="730 hours",
        inputs={},
        result=Decimal("730"),
        unit="hours"
    ),
    CalculationStep(
        description="Monthly cost",
        formula="hourly_rate * hours_per_month",
        inputs={"hourly_rate": 0.0116, "hours_per_month": 730},
        result=Decimal("8.468"),
        unit="USD/month"
    )
]
```

## Error Hierarchy

```python
ValidationError          # Validation failed
├─ Missing attribute
├─ Unsupported region
└─ Invalid attribute value

PricingMatchError       # No pricing rule found

CalculationError        # Calculation failed
├─ Invalid result
└─ Missing required field

UnitMismatchError       # Units incompatible
```

## Example Implementation

```python
class StrictEC2Adapter(PricingAdapter):
    @property
    def required_attributes(self) -> List[str]:
        return ["instance_type", "region"]
    
    @property
    def supported_regions(self) -> List[str]:
        return ["us-east-1", "us-west-2", ...]
    
    def validate(self, resource: Dict) -> None:
        # Check required attributes
        self._validate_required_attributes(resource)
        
        # Check region
        self._validate_region(resource)
        
        # Validate instance_type format
        if "." not in resource["instance_type"]:
            raise ValidationError("Invalid instance_type format")
    
    def match_pricing(self, resource: Dict) -> PricingRule:
        # Query database
        result = self.db.query(...).one_or_none()
        
        # MUST find pricing or error
        if result is None:
            raise PricingMatchError(
                f"No pricing for {resource['instance_type']}"
            )
        
        return PricingRule(...)
    
    def calculate(self, resource: Dict, rule: PricingRule) -> CostResult:
        # Validate units
        self._validate_unit_match("Hrs", rule.unit)
        
        # Calculate with steps
        hourly_rate = rule.price_per_unit
        hours = Decimal("730")
        monthly_cost = hourly_rate * hours
        
        steps = [
            CalculationStep(...),  # Hourly rate
            CalculationStep(...),  # Hours
            CalculationStep(...)   # Monthly cost
        ]
        
        return CostResult(
            monthly_cost=monthly_cost,
            pricing_rule_id=rule.id,
            unit="USD/month",
            calculation_steps=steps,
            free_tier_applied=FreeTierStatus.NOT_APPLICABLE
        )
```

## Usage

```python
# Create adapter
adapter = StrictEC2Adapter(db, pricing_version)

# Calculate cost (full pipeline with validation)
try:
    result = adapter.calculate_cost({
        "instance_type": "t3.micro",
        "region": "us-east-1"
    })
    
    print(f"Cost: ${result.monthly_cost}")
    print(f"Steps: {len(result.calculation_steps)}")
    
except ValidationError as e:
    print(f"Validation failed: {e}")
except PricingMatchError as e:
    print(f"No pricing found: {e}")
except CalculationError as e:
    print(f"Calculation failed: {e}")
```

## Testing

Run comprehensive tests:

```bash
pytest backend/tests/test_pricing_adapter_contract.py -v
```

Tests validate:
- ✅ CostResult validation (negative costs, missing fields)
- ✅ PricingRule validation
- ✅ Adapter validation (missing attributes, unsupported regions)
- ✅ Pricing match failures
- ✅ Unit mismatch detection
- ✅ Contract enforcement (must return CostResult)

## Benefits

### 🛡️ Impossible to Silently Fail
- Every error path is explicit
- No None returns allowed
- No empty results allowed

### 📊 Complete Audit Trail
- Every calculation shows its work
- Every step is traceable
- Every input is documented

### 🔍 Easy Debugging
- Clear error messages
- Detailed calculation steps
- Explicit validation failures

### ✅ Type Safety
- Dataclasses with validation
- Enums for status values
- Decimal for money (no float errors)

## Migration Guide

### Old Adapter (Silent Failures)

```python
def calculate_cost(resource):
    # Silent failures
    if "instance_type" not in resource:
        return {"monthly_cost": 0}  # ❌ Silent zero
    
    pricing = find_pricing(...)
    if not pricing:
        return {"monthly_cost": 0}  # ❌ Silent zero
    
    return {"monthly_cost": 100}  # ❌ No audit trail
```

### New Adapter (Strict Contract)

```python
def calculate_cost(resource):
    # Explicit validation
    self.validate(resource)  # ✅ Raises ValidationError
    
    # Explicit pricing match
    pricing = self.match_pricing(resource)  # ✅ Raises PricingMatchError
    
    # Explicit calculation
    return self.calculate(resource, pricing)  # ✅ Returns CostResult with steps
```

## Best Practices

1. **Always validate first** - Use `_validate_required_attributes()` and `_validate_region()`
2. **Never return None** - Raise errors instead
3. **Show your work** - Include all calculation steps
4. **Be explicit** - Set `free_tier_applied` even if `NOT_APPLICABLE`
5. **Use Decimal** - Never use float for money
6. **Add warnings** - Include helpful context in `warnings` list
7. **Test errors** - Write tests for all error paths

## Summary

The strict pricing adapter contract ensures:
- ❌ **No silent zeros** - Every zero must be justified with calculation steps
- ❌ **No implicit success** - Every result must be explicit
- ❌ **No missing validation** - Every attribute must be checked
- ✅ **Complete audit trail** - Every calculation must show work
- ✅ **Explicit errors** - Every failure must raise an exception
