"""
Terraform expression evaluator.
Evaluates Terraform expressions statically with strict validation.
FAILS FAST on any unresolved reference or dynamic value.
"""
import re
import logging
from typing import Any, Dict, Optional
from decimal import Decimal

from app.terraform.evaluator.errors import (
    UnresolvedReferenceError,
    InvalidExpressionError,
    DynamicValueError
)

logger = logging.getLogger(__name__)


class ExpressionEvaluator:
    """
    Evaluates Terraform expressions statically.
    
    Supports:
    - Variable references: var.name
    - Local references: local.name
    - Arithmetic: +, -, *, /, %
    - Comparisons: ==, !=, <, >, <=, >=
    - Logical: &&, ||, !
    - Ternary: condition ? true_val : false_val
    - String interpolation: "${var.name}"
    - Basic functions: length, min, max, concat
    
    DOES NOT support:
    - Resource references (data.*, resource.*)
    - Dynamic blocks
    - Provider-specific functions
    """
    
    def __init__(self, variables: Dict[str, Any], locals_dict: Dict[str, Any]):
        """
        Initialize evaluator with resolved variables and locals.
        
        Args:
            variables: Fully resolved variable values
            locals_dict: Fully resolved local values
        """
        self.variables = variables or {}
        self.locals = locals_dict or {}
    
    def evaluate(self, expression: Any, context: str = "") -> Any:
        """
        Evaluate an expression to a concrete value.
        
        Args:
            expression: Expression to evaluate
            context: Context for error messages
        
        Returns:
            Evaluated concrete value
        
        Raises:
            UnresolvedReferenceError: If reference cannot be resolved
            InvalidExpressionError: If expression is invalid
            DynamicValueError: If expression contains dynamic values
        """
        # Already a concrete value
        if isinstance(expression, (int, float, bool, type(None))):
            return expression
        
        # List - evaluate each element
        if isinstance(expression, list):
            return [self.evaluate(item, context) for item in expression]
        
        # Dict - evaluate each value
        if isinstance(expression, dict):
            return {k: self.evaluate(v, context) for k, v in expression.items()}
        
        # String - check for interpolation
        if isinstance(expression, str):
            return self._evaluate_string(expression, context)
        
        raise InvalidExpressionError(str(expression), "Unsupported expression type")
    
    def _evaluate_string(self, value: str, context: str) -> Any:
        """Evaluate a string expression."""
        # Check for interpolation: ${...}
        interpolation_pattern = r'\$\{([^}]+)\}'
        matches = list(re.finditer(interpolation_pattern, value))
        
        if not matches:
            # Plain string
            return value
        
        # If entire string is a single interpolation, return the evaluated value
        if len(matches) == 1 and matches[0].group(0) == value:
            expr = matches[0].group(1).strip()
            return self._evaluate_expression(expr, context)
        
        # Multiple interpolations or mixed - build result string
        result = value
        for match in reversed(matches):  # Reverse to maintain positions
            expr = match.group(1).strip()
            evaluated = self._evaluate_expression(expr, context)
            result = result[:match.start()] + str(evaluated) + result[match.end():]
        
        return result
    
    def _evaluate_expression(self, expr: str, context: str) -> Any:
        """Evaluate a Terraform expression."""
        expr = expr.strip()
        
        # Variable reference: var.name
        if expr.startswith("var."):
            var_name = expr[4:]
            if var_name not in self.variables:
                raise UnresolvedReferenceError(expr, context)
            return self.variables[var_name]
        
        # Local reference: local.name
        if expr.startswith("local."):
            local_name = expr[6:]
            if local_name not in self.locals:
                raise UnresolvedReferenceError(expr, context)
            return self.locals[local_name]
        
        # Resource/data references - NOT SUPPORTED
        if expr.startswith(("data.", "resource.", "module.")):
            raise DynamicValueError("resource reference", context)
        
        # Ternary operator: condition ? true_val : false_val
        if "?" in expr and ":" in expr:
            return self._evaluate_ternary(expr, context)
        
        # Logical operators
        if "||" in expr:
            return self._evaluate_logical_or(expr, context)
        if "&&" in expr:
            return self._evaluate_logical_and(expr, context)
        
        # Comparison operators
        for op in ["==", "!=", "<=", ">=", "<", ">"]:
            if op in expr:
                return self._evaluate_comparison(expr, op, context)
        
        # Arithmetic operators
        for op in ["+", "-", "*", "/", "%"]:
            if op in expr and not expr.startswith("-"):  # Avoid negative numbers
                return self._evaluate_arithmetic(expr, op, context)
        
        # Function calls
        if "(" in expr and expr.endswith(")"):
            return self._evaluate_function(expr, context)
        
        # Boolean literals
        if expr == "true":
            return True
        if expr == "false":
            return False
        
        # Null literal
        if expr == "null":
            return None
        
        # Numeric literal
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass
        
        # String literal (quoted)
        if (expr.startswith('"') and expr.endswith('"')) or \
           (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]
        
        raise InvalidExpressionError(expr, "Unknown expression type")
    
    def _evaluate_ternary(self, expr: str, context: str) -> Any:
        """Evaluate ternary: condition ? true_val : false_val"""
        parts = expr.split("?", 1)
        if len(parts) != 2:
            raise InvalidExpressionError(expr, "Invalid ternary syntax")
        
        condition_expr = parts[0].strip()
        value_parts = parts[1].split(":", 1)
        
        if len(value_parts) != 2:
            raise InvalidExpressionError(expr, "Invalid ternary syntax")
        
        true_expr = value_parts[0].strip()
        false_expr = value_parts[1].strip()
        
        condition = self._evaluate_expression(condition_expr, context)
        
        if condition:
            return self._evaluate_expression(true_expr, context)
        else:
            return self._evaluate_expression(false_expr, context)
    
    def _evaluate_logical_or(self, expr: str, context: str) -> bool:
        """Evaluate logical OR."""
        parts = expr.split("||")
        for part in parts:
            if self._evaluate_expression(part.strip(), context):
                return True
        return False
    
    def _evaluate_logical_and(self, expr: str, context: str) -> bool:
        """Evaluate logical AND."""
        parts = expr.split("&&")
        for part in parts:
            if not self._evaluate_expression(part.strip(), context):
                return False
        return True
    
    def _evaluate_comparison(self, expr: str, op: str, context: str) -> bool:
        """Evaluate comparison operator."""
        parts = expr.split(op, 1)
        if len(parts) != 2:
            raise InvalidExpressionError(expr, f"Invalid {op} syntax")
        
        left = self._evaluate_expression(parts[0].strip(), context)
        right = self._evaluate_expression(parts[1].strip(), context)
        
        if op == "==":
            return left == right
        elif op == "!=":
            return left != right
        elif op == "<":
            return left < right
        elif op == ">":
            return left > right
        elif op == "<=":
            return left <= right
        elif op == ">=":
            return left >= right
        
        raise InvalidExpressionError(expr, f"Unknown operator {op}")
    
    def _evaluate_arithmetic(self, expr: str, op: str, context: str) -> float:
        """Evaluate arithmetic operator."""
        # Find rightmost operator to handle left-to-right evaluation
        parts = expr.rsplit(op, 1)
        if len(parts) != 2:
            raise InvalidExpressionError(expr, f"Invalid {op} syntax")
        
        left = self._evaluate_expression(parts[0].strip(), context)
        right = self._evaluate_expression(parts[1].strip(), context)
        
        # Convert to numbers
        try:
            left_num = float(left) if not isinstance(left, (int, float)) else left
            right_num = float(right) if not isinstance(right, (int, float)) else right
        except (ValueError, TypeError):
            raise InvalidExpressionError(expr, "Non-numeric operands")
        
        if op == "+":
            return left_num + right_num
        elif op == "-":
            return left_num - right_num
        elif op == "*":
            return left_num * right_num
        elif op == "/":
            if right_num == 0:
                raise InvalidExpressionError(expr, "Division by zero")
            return left_num / right_num
        elif op == "%":
            return left_num % right_num
        
        raise InvalidExpressionError(expr, f"Unknown operator {op}")
    
    def _evaluate_function(self, expr: str, context: str) -> Any:
        """Evaluate function call."""
        func_match = re.match(r'(\w+)\((.*)\)$', expr)
        if not func_match:
            raise InvalidExpressionError(expr, "Invalid function syntax")
        
        func_name = func_match.group(1)
        args_str = func_match.group(2).strip()
        
        # Parse arguments (simple comma split - doesn't handle nested)
        args = []
        if args_str:
            for arg in args_str.split(","):
                args.append(self._evaluate_expression(arg.strip(), context))
        
        # Supported functions
        if func_name == "length":
            if len(args) != 1:
                raise InvalidExpressionError(expr, "length() requires 1 argument")
            return len(args[0]) if hasattr(args[0], '__len__') else 0
        
        elif func_name == "min":
            if len(args) < 1:
                raise InvalidExpressionError(expr, "min() requires at least 1 argument")
            return min(args)
        
        elif func_name == "max":
            if len(args) < 1:
                raise InvalidExpressionError(expr, "max() requires at least 1 argument")
            return max(args)
        
        elif func_name == "concat":
            result = []
            for arg in args:
                if isinstance(arg, list):
                    result.extend(arg)
                else:
                    result.append(arg)
            return result
        
        else:
            raise InvalidExpressionError(expr, f"Unsupported function: {func_name}")
