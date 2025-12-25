"""
For_each expander for Terraform resources.
Expands resources with for_each meta-argument into concrete instances.
"""
import logging
from typing import Dict, List, Any, Union
from copy import deepcopy

from app.terraform.evaluator.expression_eval import ExpressionEvaluator
from app.terraform.evaluator.errors import (
    ExpansionLimitExceededError,
    InvalidExpressionError,
    UnresolvedReferenceError
)

logger = logging.getLogger(__name__)


class ForEachExpander:
    """
    Expands Terraform resources with for_each meta-argument.
    
    Supports:
    - Map: for_each = { key1 = val1, key2 = val2 }
    - Set: for_each = ["item1", "item2"]
    
    Converts:
        resource "aws_instance" "web" {
            for_each = { prod = "t3.large", dev = "t3.micro" }
            instance_type = each.value
            ...
        }
    
    Into 2 concrete resources:
        web["prod"], web["dev"]
    """
    
    def __init__(self, evaluator: ExpressionEvaluator, max_expansion: int = 1000):
        """
        Initialize for_each expander.
        
        Args:
            evaluator: Expression evaluator for resolving for_each values
            max_expansion: Maximum allowed expansion count
        """
        self.evaluator = evaluator
        self.max_expansion = max_expansion
    
    def expand(self, resource: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Expand a resource with for_each.
        
        Args:
            resource: Resource dictionary with potential for_each attribute
        
        Returns:
            List of expanded resources (1 if no for_each, N if for_each has N items)
        
        Raises:
            ExpansionLimitExceededError: If for_each size exceeds max_expansion
            UnresolvedReferenceError: If for_each expression cannot be resolved
            InvalidExpressionError: If for_each is invalid
        """
        attributes = resource.get("attributes", {})
        for_each_expr = attributes.get("for_each")
        
        # No for_each - return single resource
        if for_each_expr is None:
            return [resource]
        
        # Evaluate for_each expression
        resource_name = resource.get("name", "unknown")
        context = f"resource {resource.get('type', 'unknown')}.{resource_name}"
        
        try:
            for_each_value = self.evaluator.evaluate(for_each_expr, context)
        except Exception as e:
            logger.error(f"Failed to evaluate for_each for {context}: {e}")
            raise
        
        # Convert to items list
        items = self._extract_items(for_each_value, context)
        
        # Check expansion limit
        if len(items) > self.max_expansion:
            raise ExpansionLimitExceededError(resource_name, len(items), self.max_expansion)
        
        # for_each with empty collection means no resources
        if len(items) == 0:
            logger.info(f"Resource {context} has empty for_each, skipping")
            return []
        
        # Expand into N resources
        expanded = []
        for key, value in items:
            expanded_resource = deepcopy(resource)
            
            # Set logical ID with key
            expanded_resource["logical_id"] = f"{resource_name}[\"{key}\"]"
            expanded_resource["physical_index"] = key
            expanded_resource["for_each_key"] = key
            expanded_resource["for_each_value"] = value
            
            # Remove for_each from attributes (it's been processed)
            if "for_each" in expanded_resource.get("attributes", {}):
                del expanded_resource["attributes"]["for_each"]
            
            # Resolve each.key and each.value references in attributes
            expanded_resource["attributes"] = self._resolve_each_references(
                expanded_resource["attributes"],
                key,
                value
            )
            
            expanded.append(expanded_resource)
        
        logger.info(f"Expanded {context} with for_each into {len(expanded)} resources")
        return expanded
    
    def _extract_items(
        self,
        for_each_value: Union[Dict, List, set],
        context: str
    ) -> List[tuple]:
        """
        Extract key-value pairs from for_each value.
        
        Args:
            for_each_value: Evaluated for_each value
            context: Context for error messages
        
        Returns:
            List of (key, value) tuples
        
        Raises:
            InvalidExpressionError: If for_each type is invalid
        """
        # Map: { key: value }
        if isinstance(for_each_value, dict):
            return list(for_each_value.items())
        
        # Set or List: ["item1", "item2"]
        if isinstance(for_each_value, (list, set)):
            # For sets/lists, key and value are the same
            return [(str(item), item) for item in for_each_value]
        
        raise InvalidExpressionError(
            str(for_each_value),
            f"for_each must be a map or set, got {type(for_each_value).__name__} in {context}"
        )
    
    def _resolve_each_references(
        self,
        attributes: Dict[str, Any],
        key: str,
        value: Any
    ) -> Dict[str, Any]:
        """
        Resolve each.key and each.value references in attributes.
        
        Args:
            attributes: Resource attributes
            key: Current for_each key
            value: Current for_each value
        
        Returns:
            Attributes with each.key and each.value resolved
        """
        resolved = {}
        
        for attr_key, attr_value in attributes.items():
            if isinstance(attr_value, str):
                # Replace each.key and each.value references
                resolved_value = attr_value.replace("${each.key}", str(key))
                resolved_value = resolved_value.replace("each.key", str(key))
                resolved_value = resolved_value.replace("${each.value}", str(value))
                resolved_value = resolved_value.replace("each.value", str(value))
                resolved[attr_key] = resolved_value
            elif isinstance(attr_value, dict):
                resolved[attr_key] = self._resolve_each_references(attr_value, key, value)
            elif isinstance(attr_value, list):
                resolved[attr_key] = [
                    self._resolve_each_references(item, key, value) if isinstance(item, dict)
                    else item.replace("${each.key}", str(key)).replace("${each.value}", str(value))
                    if isinstance(item, str)
                    else item
                    for item in attr_value
                ]
            else:
                resolved[attr_key] = attr_value
        
        return resolved
    
    def expand_all(self, resources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Expand all resources with for_each.
        
        Args:
            resources: List of resources
        
        Returns:
            List of expanded resources
        """
        all_expanded = []
        
        for resource in resources:
            try:
                expanded = self.expand(resource)
                all_expanded.extend(expanded)
            except Exception as e:
                logger.error(f"Failed to expand resource {resource.get('name')}: {e}")
                raise
        
        return all_expanded
