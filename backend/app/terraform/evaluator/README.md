# Terraform Semantic Evaluation Engine

## Overview

Static Terraform evaluation engine that converts parsed HCL into fully expanded, deterministic resources **without running `terraform apply` or calling AWS APIs**.

## Architecture

```
terraform/evaluator/
├── errors.py              # Error hierarchy (fail-fast)
├── expression_eval.py     # Expression evaluator
├── count_expander.py      # Count meta-argument expansion
├── foreach_expander.py    # For_each meta-argument expansion
├── conditional_eval.py    # Conditional expression evaluation
└── engine.py             # Orchestration engine
```

## Supported Features

### ✅ Expressions
- Variable references: `var.name`
- Local references: `local.name`
- Arithmetic: `+`, `-`, `*`, `/`, `%`
- Comparisons: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Logical: `&&`, `||`, `!`
- Ternary: `condition ? true_val : false_val`
- String interpolation: `"${var.name}"`
- Functions: `length()`, `min()`, `max()`, `concat()`

### ✅ Meta-Arguments
- `count` - Expands to N resources
- `for_each` - Expands maps and sets
- Conditional creation: `count = var.create ? 1 : 0`

### ✅ References
- `count.index` - Resolved during count expansion
- `each.key` / `each.value` - Resolved during for_each expansion

### ❌ Not Supported (Fail Fast)
- Resource references: `data.*`, `resource.*`
- Dynamic blocks
- Remote modules
- Provider-specific functions
- Any unresolved expression

## Usage

### Basic Evaluation

```python
from pathlib import Path
from app.terraform.evaluator.engine import TerraformEvaluationEngine

# Initialize engine
engine = TerraformEvaluationEngine(
    max_expansion=1000,
    variable_overrides={"environment": "production"}
)

# Evaluate Terraform
expanded_resources = engine.evaluate(Path("./terraform"))

# Access fully resolved resources
for resource in expanded_resources:
    print(f"ID: {resource.logical_id}")
    print(f"Type: {resource.resource_type}")
    print(f"Region: {resource.resolved_region}")
    print(f"Attributes: {resource.resolved_attributes}")
```

### Expression Evaluation

```python
from app.terraform.evaluator.expression_eval import ExpressionEvaluator

evaluator = ExpressionEvaluator(
    variables={"count": 5, "env": "prod"},
    locals_dict={"region": "us-east-1"}
)

# Evaluate expressions
result = evaluator.evaluate("${var.count * 2}")  # 10
result = evaluator.evaluate("${var.env == \"prod\" ? \"large\" : \"small\"}")  # "large"
result = evaluator.evaluate("${local.region}")  # "us-east-1"
```

### Count Expansion

```python
from app.terraform.evaluator.count_expander import CountExpander

expander = CountExpander(evaluator, max_expansion=1000)

resource = {
    "name": "web",
    "type": "aws_instance",
    "attributes": {
        "count": 3,
        "name": "server-${count.index}"
    }
}

expanded = expander.expand(resource)
# Returns 3 resources: web[0], web[1], web[2]
# with names: server-0, server-1, server-2
```

### For_Each Expansion

```python
from app.terraform.evaluator.foreach_expander import ForEachExpander

expander = ForEachExpander(evaluator, max_expansion=1000)

resource = {
    "name": "web",
    "type": "aws_instance",
    "attributes": {
        "for_each": {"prod": "t3.large", "dev": "t3.micro"},
        "instance_type": "${each.value}",
        "name": "${each.key}-server"
    }
}

expanded = expander.expand(resource)
# Returns 2 resources: web["prod"], web["dev"]
# with instance_types: t3.large, t3.micro
```

## Output Contract

Every resource is transformed into an `ExpandedResource`:

```python
class ExpandedResource:
    logical_id: str              # "web[0]" or "db[\"prod\"]"
    resource_type: str           # "aws_instance"
    physical_index: Any          # 0 or "prod"
    resolved_attributes: Dict    # All attributes fully evaluated
    resolved_region: str         # "us-east-1"
```

## Error Handling

All errors are **fatal** - the engine fails fast:

```python
from app.terraform.evaluator.errors import (
    UnresolvedReferenceError,      # Reference cannot be resolved
    InvalidExpressionError,         # Expression is invalid
    ExpansionLimitExceededError,    # Too many resources
    DynamicValueError,              # Dynamic value encountered
    ConditionalEvaluationError      # Conditional cannot be evaluated
)
```

### Example: Unresolved Reference

```python
# This FAILS FAST
evaluator.evaluate("${var.missing}")
# Raises: UnresolvedReferenceError: Unresolved reference: var.missing
```

### Example: Dynamic Value

```python
# This FAILS FAST
evaluator.evaluate("${data.aws_ami.latest.id}")
# Raises: DynamicValueError: Dynamic value of type 'resource reference' cannot be resolved statically
```

## Expansion Limits

Configurable limits prevent resource explosion:

```python
# Default limit: 1000 resources
engine = TerraformEvaluationEngine(max_expansion=1000)

# This FAILS if count > 1000
resource = {"attributes": {"count": 2000}}
# Raises: ExpansionLimitExceededError
```

## Evaluation Pipeline

The engine executes a 6-stage pipeline:

1. **Parse HCL** - Convert .tf files to AST
2. **Resolve Variables** - Apply defaults and overrides
3. **Evaluate Conditionals** - Resolve ternary expressions
4. **Expand Count** - Create N instances
5. **Expand For_Each** - Create keyed instances
6. **Finalize** - Validate and create ExpandedResource objects

## Testing

Run comprehensive unit tests:

```bash
pytest backend/tests/test_terraform_evaluator.py -v
```

Tests cover:
- ✅ Expression evaluation (all operators)
- ✅ Count expansion (0, 1, N)
- ✅ For_each expansion (maps, sets)
- ✅ Conditional evaluation
- ✅ Error cases (unresolved, invalid, limits)
- ✅ Integration scenarios

## Examples

### Example 1: Conditional Count

```hcl
variable "create_db" {
  default = true
}

resource "aws_db_instance" "main" {
  count = var.create_db ? 1 : 0
  instance_class = "db.t3.micro"
}
```

**Result**: 1 resource if `create_db = true`, 0 if `false`

### Example 2: Count with Index

```hcl
variable "server_count" {
  default = 3
}

resource "aws_instance" "web" {
  count = var.server_count
  tags = {
    Name = "server-${count.index}"
  }
}
```

**Result**: 3 resources with tags: `server-0`, `server-1`, `server-2`

### Example 3: For_Each with Map

```hcl
variable "instances" {
  default = {
    prod = "t3.large"
    dev  = "t3.micro"
  }
}

resource "aws_instance" "app" {
  for_each      = var.instances
  instance_type = each.value
  tags = {
    Name = "${each.key}-server"
  }
}
```

**Result**: 2 resources:
- `app["prod"]` with `instance_type = "t3.large"`, `Name = "prod-server"`
- `app["dev"]` with `instance_type = "t3.micro"`, `Name = "dev-server"`

## Integration with Cost Calculator

The evaluation engine integrates with the existing normalizer:

```python
from app.terraform.evaluator.engine import TerraformEvaluationEngine
from app.terraform.normalizer import ResourceNormalizer

# Evaluate Terraform
engine = TerraformEvaluationEngine()
expanded = engine.evaluate(Path("./terraform"))

# Convert to normalized resources for cost calculation
normalizer = ResourceNormalizer()
normalized = []

for resource in expanded:
    normalized_resource = {
        "type": resource.resource_type,
        "name": resource.logical_id,
        "attributes": resource.resolved_attributes,
        "region": resource.resolved_region
    }
    normalized.append(normalizer.normalize_resource(normalized_resource))
```

## Limitations

- **Local modules only** - Remote modules not supported
- **Static values only** - No runtime AWS API calls
- **Basic functions** - Limited function library
- **No dynamic blocks** - Must be statically defined

## Future Enhancements

- [ ] Support for more Terraform functions
- [ ] Module variable passing
- [ ] Depends_on graph validation
- [ ] Lifecycle meta-arguments
- [ ] Provider configuration validation
