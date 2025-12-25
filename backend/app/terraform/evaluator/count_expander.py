"""
Count expander for Terraform resources.
Expands resources with count meta-argument into concrete instances.
"""
import logging
from typing import Dict, List, Any
from copy import deepcopy

from app.terraform.evaluator.expression_eval import ExpressionEvaluator
from app.terraform.evaluator.errors import (
    ExpansionLimitExceededError,
    InvalidExpressionError,
    UnresolvedReferenceError
)

logger = logging.getLogger(__name__)


class CountExpander:
    """
    Expands Terraform resources with count meta-argument.
    
    Converts:
        resource "aws_instance" "web" {
            count = 3
            ...
        }
    
    Into 3 concrete resources:
        web[0], web[1], web[2]
    """
    
    def __init__(self, evaluator: ExpressionEvaluator, max_expansion: int = 1000):
        """
        Initialize count expander.
        
        Args:
            evaluator: Expression evaluator for resolving count values
            max_expansion: Maximum allowed expansion count
        """
        self.evaluator = evaluator
        self.max_expansion = max_expansion
    
    def expand(self, resource: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Expand a resource with count.
        
        Args:
            resource: Resource dictionary with potential count attribute
        
        Returns:
            List of expanded resources (1 if no count, N if count=N)
        
        Raises:
            ExpansionLimitExceededError: If count exceeds max_expansion
            UnresolvedReferenceError: If count expression cannot be resolved
            InvalidExpressionError: If count is invalid
        """
        attributes = resource.get("attributes", {})
        count_expr = attributes.get("count")
        
        # No count - return single resource
        if count_expr is None:
            return [resource]
        
        # Evaluate count expression
        resource_name = resource.get("name", "unknown")
        context = f"resource {resource.get('type', 'unknown')}.{resource_name}"
        
        try:
            count_value = self.evaluator.evaluate(count_expr, context)
        except Exception as e:
            logger.error(f"Failed to evaluate count for {context}: {e}")
            raise
        
        # Validate count value
        if not isinstance(count_value, int):
            raise InvalidExpressionError(
                str(count_expr),
                f"count must be an integer, got {type(count_value).__name__}"
            )
        
        if count_value < 0:
            raise InvalidExpressionError(
                str(count_expr),
                f"count must be non-negative, got {count_value}"
            )
        
        # Check expansion limit
        if count_value > self.max_expansion:
            raise ExpansionLimitExceededError(resource_name, count_value, self.max_expansion)
        
        # count = 0 means no resources
        if count_value == 0:
            logger.info(f"Resource {context} has count=0, skipping")
            return []
        
        # Expand into N resources
        expanded = []
        for index in range(count_value):
            expanded_resource = deepcopy(resource)
            
            # Set logical ID with index
            expanded_resource["logical_id"] = f"{resource_name}[{index}]"
            expanded_resource["physical_index"] = index
            expanded_resource["count_index"] = index
            
            # Remove count from attributes (it's been processed)
            if "count" in expanded_resource.get("attributes", {}):
                del expanded_resource["attributes"]["count"]
            
            # Resolve count.index references in attributes
            expanded_resource["attributes"] = self._resolve_count_index(
                expanded_resource["attributes"],
                index
            )
            
            expanded.append(expanded_resource)
        
        logger.info(f"Expanded {context} with count={count_value} into {len(expanded)} resources")
        return expanded
    
    def _resolve_count_index(self, attributes: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        Resolve count.index references in attributes.
        
        Args:
            attributes: Resource attributes
            index: Current count index
        
        Returns:
            Attributes with count.index resolved
        """
        resolved = {}
        
        for key, value in attributes.items():
            if isinstance(value, str):
                # Replace count.index references
                resolved[key] = value.replace("${count.index}", str(index))
                resolved[key] = resolved[key].replace("count.index", str(index))
            elif isinstance(value, dict):
                resolved[key] = self._resolve_count_index(value, index)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_count_index(item, index) if isinstance(item, dict)
                    else item.replace("${count.index}", str(index)) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                resolved[key] = value
        
        return resolved
    
    def expand_all(self, resources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Expand all resources with count.
        
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
