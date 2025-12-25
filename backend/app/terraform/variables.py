"""
Terraform variable resolver.
Resolves variable references and applies defaults.
"""
import logging
import re
from typing import Dict, Any, Optional
from copy import deepcopy

logger = logging.getLogger(__name__)


class VariableResolver:
    """
    Resolves Terraform variable references.
    """
    
    def __init__(self, variables: Dict, locals_dict: Dict, var_values: Optional[Dict] = None):
        """
        Initialize variable resolver.
        
        Args:
            variables: Variable definitions from Terraform
            locals_dict: Local values from Terraform
            var_values: Optional variable values (from tfvars or user input)
        """
        self.variable_defs = variables
        self.locals = locals_dict
        self.var_values = var_values or {}
        self.resolved_vars = {}
        self.resolved_locals = {}
    
    def resolve_variables(self) -> Dict:
        """
        Resolve all variables with defaults or provided values.
        
        Returns:
            Dictionary of resolved variable values
        """
        for var_name, var_def in self.variable_defs.items():
            if var_name in self.var_values:
                # Use provided value
                self.resolved_vars[var_name] = self.var_values[var_name]
            elif var_def.get("default") is not None:
                # Use default value
                self.resolved_vars[var_name] = var_def["default"]
            else:
                # No value available - log warning
                logger.warning(f"Variable '{var_name}' has no value and no default")
                self.resolved_vars[var_name] = None
        
        return self.resolved_vars
    
    def resolve_locals(self) -> Dict:
        """
        Resolve local values (may reference variables).
        
        Returns:
            Dictionary of resolved local values
        """
        # First pass: resolve simple locals
        for local_name, local_value in self.locals.items():
            if isinstance(local_value, (str, int, float, bool, list, dict)):
                self.resolved_locals[local_name] = local_value
        
        # Second pass: resolve references
        for local_name, local_value in self.locals.items():
            if isinstance(local_value, str):
                self.resolved_locals[local_name] = self.resolve_string_references(local_value)
        
        return self.resolved_locals
    
    def resolve_string_references(self, value: str) -> Any:
        """
        Resolve variable and local references in a string.
        
        Supports:
            - var.variable_name
            - local.local_name
        
        Args:
            value: String potentially containing references
        
        Returns:
            Resolved value
        """
        if not isinstance(value, str):
            return value
        
        # Pattern for var.name or local.name
        var_pattern = r'\$\{var\.([a-zA-Z0-9_]+)\}'
        local_pattern = r'\$\{local\.([a-zA-Z0-9_]+)\}'
        
        # Replace variable references
        def replace_var(match):
            var_name = match.group(1)
            if var_name in self.resolved_vars:
                return str(self.resolved_vars[var_name])
            logger.warning(f"Unresolved variable reference: var.{var_name}")
            return match.group(0)
        
        value = re.sub(var_pattern, replace_var, value)
        
        # Replace local references
        def replace_local(match):
            local_name = match.group(1)
            if local_name in self.resolved_locals:
                return str(self.resolved_locals[local_name])
            logger.warning(f"Unresolved local reference: local.{local_name}")
            return match.group(0)
        
        value = re.sub(local_pattern, replace_local, value)
        
        return value
    
    def resolve_attribute_references(self, attributes: Dict) -> Dict:
        """
        Resolve references in resource attributes.
        
        Args:
            attributes: Resource attributes dictionary
        
        Returns:
            Attributes with resolved references
        """
        resolved = {}
        
        for key, value in attributes.items():
            if isinstance(value, str):
                resolved[key] = self.resolve_string_references(value)
            elif isinstance(value, dict):
                resolved[key] = self.resolve_attribute_references(value)
            elif isinstance(value, list):
                resolved[key] = [
                    self.resolve_string_references(item) if isinstance(item, str)
                    else self.resolve_attribute_references(item) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                resolved[key] = value
        
        return resolved
    
    def resolve_all(self) -> Dict:
        """
        Resolve all variables and locals.
        
        Returns:
            Dictionary with resolved variables and locals
        """
        self.resolve_variables()
        self.resolve_locals()
        
        return {
            "variables": self.resolved_vars,
            "locals": self.resolved_locals
        }
