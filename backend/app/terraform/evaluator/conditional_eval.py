"""
Conditional expression evaluator for Terraform.
Handles conditional resource creation and attribute assignment.
"""
import logging
from typing import Dict, List, Any, Optional
from copy import deepcopy

from app.terraform.evaluator.expression_eval import ExpressionEvaluator
from app.terraform.evaluator.errors import ConditionalEvaluationError

logger = logging.getLogger(__name__)


class ConditionalEvaluator:
    """
    Evaluates conditional expressions in Terraform.
    
    Handles:
    - Conditional resource creation: count = var.create ? 1 : 0
    - Conditional attributes: value = var.enabled ? "yes" : "no"
    - Nested conditionals
    """
    
    def __init__(self, evaluator: ExpressionEvaluator):
        """
        Initialize conditional evaluator.
        
        Args:
            evaluator: Expression evaluator for resolving conditions
        """
        self.evaluator = evaluator
    
    def evaluate_resource_condition(self, resource: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate if a resource should be created based on conditional count.
        
        Common pattern:
            count = var.create_resource ? 1 : 0
        
        Args:
            resource: Resource dictionary
        
        Returns:
            Resource if it should be created, None otherwise
        
        Raises:
            ConditionalEvaluationError: If condition cannot be evaluated
        """
        attributes = resource.get("attributes", {})
        count_expr = attributes.get("count")
        
        # No conditional count
        if count_expr is None:
            return resource
        
        # Evaluate count
        resource_name = resource.get("name", "unknown")
        context = f"resource {resource.get('type', 'unknown')}.{resource_name}"
        
        try:
            count_value = self.evaluator.evaluate(count_expr, context)
        except Exception as e:
            raise ConditionalEvaluationError(
                str(count_expr),
                f"Failed to evaluate in {context}: {e}"
            )
        
        # If count evaluates to 0 or false, skip resource
        if count_value == 0 or count_value is False:
            logger.info(f"Resource {context} skipped due to conditional count={count_value}")
            return None
        
        return resource
    
    def evaluate_attribute_conditionals(self, attributes: Dict[str, Any], context: str = "") -> Dict[str, Any]:
        """
        Evaluate conditional expressions in resource attributes.
        
        Args:
            attributes: Resource attributes
            context: Context for error messages
        
        Returns:
            Attributes with conditionals resolved
        
        Raises:
            ConditionalEvaluationError: If condition cannot be evaluated
        """
        resolved = {}
        
        for key, value in attributes.items():
            try:
                # Recursively evaluate nested structures
                if isinstance(value, dict):
                    resolved[key] = self.evaluate_attribute_conditionals(value, f"{context}.{key}")
                elif isinstance(value, list):
                    resolved[key] = [
                        self.evaluate_attribute_conditionals(item, f"{context}.{key}[{i}]")
                        if isinstance(item, dict)
                        else self.evaluator.evaluate(item, f"{context}.{key}[{i}]")
                        for i, item in enumerate(value)
                    ]
                else:
                    # Evaluate the value (handles conditionals, references, etc.)
                    resolved[key] = self.evaluator.evaluate(value, f"{context}.{key}")
            
            except Exception as e:
                raise ConditionalEvaluationError(
                    str(value),
                    f"Failed to evaluate attribute '{key}' in {context}: {e}"
                )
        
        return resolved
    
    def filter_conditional_resources(self, resources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out resources that should not be created due to conditionals.
        
        Args:
            resources: List of resources
        
        Returns:
            Filtered list of resources
        """
        filtered = []
        
        for resource in resources:
            evaluated = self.evaluate_resource_condition(resource)
            if evaluated is not None:
                filtered.append(evaluated)
        
        logger.info(f"Filtered {len(resources)} resources to {len(filtered)} after conditional evaluation")
        return filtered
    
    def resolve_all_conditionals(self, resources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Resolve all conditional expressions in resources.
        
        Args:
            resources: List of resources
        
        Returns:
            Resources with all conditionals resolved
        """
        resolved_resources = []
        
        for resource in resources:
            # First check if resource should exist
            if self.evaluate_resource_condition(resource) is None:
                continue
            
            # Resolve attribute conditionals
            resolved_resource = deepcopy(resource)
            context = f"{resource.get('type', 'unknown')}.{resource.get('name', 'unknown')}"
            
            resolved_resource["attributes"] = self.evaluate_attribute_conditionals(
                resource.get("attributes", {}),
                context
            )
            
            resolved_resources.append(resolved_resource)
        
        return resolved_resources
