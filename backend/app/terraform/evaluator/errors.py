"""
Terraform evaluation errors.
All errors are fatal - we fail fast on any unresolved expression.
"""


class TerraformEvaluationError(Exception):
    """Base class for all Terraform evaluation errors."""
    pass


class UnresolvedReferenceError(TerraformEvaluationError):
    """Raised when a reference cannot be resolved."""
    
    def __init__(self, reference: str, context: str = ""):
        self.reference = reference
        self.context = context
        super().__init__(f"Unresolved reference: {reference}" + (f" in {context}" if context else ""))


class InvalidExpressionError(TerraformEvaluationError):
    """Raised when an expression is invalid or cannot be evaluated."""
    
    def __init__(self, expression: str, reason: str):
        self.expression = expression
        self.reason = reason
        super().__init__(f"Invalid expression '{expression}': {reason}")


class ExpansionLimitExceededError(TerraformEvaluationError):
    """Raised when resource expansion exceeds configured limit."""
    
    def __init__(self, resource_name: str, count: int, limit: int):
        self.resource_name = resource_name
        self.count = count
        self.limit = limit
        super().__init__(
            f"Resource '{resource_name}' expansion count {count} exceeds limit {limit}"
        )


class DynamicValueError(TerraformEvaluationError):
    """Raised when a dynamic value is encountered that cannot be resolved statically."""
    
    def __init__(self, value_type: str, context: str = ""):
        self.value_type = value_type
        self.context = context
        super().__init__(
            f"Dynamic value of type '{value_type}' cannot be resolved statically" +
            (f" in {context}" if context else "")
        )


class ConditionalEvaluationError(TerraformEvaluationError):
    """Raised when a conditional expression cannot be evaluated."""
    
    def __init__(self, condition: str, reason: str):
        self.condition = condition
        self.reason = reason
        super().__init__(f"Cannot evaluate conditional '{condition}': {reason}")


class ModuleExpansionError(TerraformEvaluationError):
    """Raised when module expansion fails."""
    
    def __init__(self, module_name: str, reason: str):
        self.module_name = module_name
        self.reason = reason
        super().__init__(f"Module '{module_name}' expansion failed: {reason}")
