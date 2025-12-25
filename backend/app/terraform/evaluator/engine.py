"""
Terraform Semantic Evaluation Engine.
Orchestrates the complete evaluation pipeline.
"""
import logging
from typing import Dict, List, Any
from pathlib import Path

from app.terraform.parser import TerraformParser
from app.terraform.variables import VariableResolver
from app.terraform.evaluator.expression_eval import ExpressionEvaluator
from app.terraform.evaluator.count_expander import CountExpander
from app.terraform.evaluator.foreach_expander import ForEachExpander
from app.terraform.evaluator.conditional_eval import ConditionalEvaluator
from app.terraform.evaluator.errors import TerraformEvaluationError
from app.config import settings

logger = logging.getLogger(__name__)


class ExpandedResource:
    """
    Fully expanded and resolved Terraform resource.
    
    Contract:
    - logical_id: Unique identifier (e.g., "web[0]", "db["prod"]")
    - physical_index: Index or key from count/for_each
    - resolved_attributes: All attributes fully evaluated
    - resolved_region: Concrete AWS region
    """
    
    def __init__(
        self,
        logical_id: str,
        resource_type: str,
        physical_index: Any,
        resolved_attributes: Dict[str, Any],
        resolved_region: str
    ):
        self.logical_id = logical_id
        self.resource_type = resource_type
        self.physical_index = physical_index
        self.resolved_attributes = resolved_attributes
        self.resolved_region = resolved_region
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "logical_id": self.logical_id,
            "resource_type": self.resource_type,
            "physical_index": self.physical_index,
            "resolved_attributes": self.resolved_attributes,
            "resolved_region": self.resolved_region
        }


class TerraformEvaluationEngine:
    """
    Complete Terraform semantic evaluation engine.
    
    Pipeline:
    1. Parse HCL
    2. Resolve variables and locals
    3. Evaluate conditionals
    4. Expand count
    5. Expand for_each
    6. Resolve all expressions
    7. Validate completeness
    """
    
    def __init__(
        self,
        max_expansion: int = None,
        variable_overrides: Dict[str, Any] = None
    ):
        """
        Initialize evaluation engine.
        
        Args:
            max_expansion: Maximum resource expansion limit
            variable_overrides: Variable values to override defaults
        """
        self.max_expansion = max_expansion or settings.max_count_expansion
        self.variable_overrides = variable_overrides or {}
        self.parser = TerraformParser()
    
    def evaluate(self, terraform_path: Path) -> List[ExpandedResource]:
        """
        Evaluate Terraform configuration to fully expanded resources.
        
        Args:
            terraform_path: Path to Terraform file or directory
        
        Returns:
            List of fully expanded and resolved resources
        
        Raises:
            TerraformEvaluationError: If evaluation fails at any stage
        """
        logger.info(f"Starting Terraform evaluation for {terraform_path}")
        
        # Stage 1: Parse HCL
        logger.info("Stage 1: Parsing HCL")
        parsed = self.parser.parse(terraform_path)
        
        # Stage 2: Resolve variables and locals
        logger.info("Stage 2: Resolving variables and locals")
        resolver = VariableResolver(
            parsed["variables"],
            parsed["locals"],
            self.variable_overrides
        )
        resolved = resolver.resolve_all()
        
        # Create expression evaluator
        evaluator = ExpressionEvaluator(
            resolved["variables"],
            resolved["locals"]
        )
        
        # Stage 3: Evaluate conditionals
        logger.info("Stage 3: Evaluating conditionals")
        conditional_eval = ConditionalEvaluator(evaluator)
        resources = conditional_eval.resolve_all_conditionals(parsed["resources"])
        
        logger.info(f"After conditional evaluation: {len(resources)} resources")
        
        # Stage 4: Expand count
        logger.info("Stage 4: Expanding count")
        count_expander = CountExpander(evaluator, self.max_expansion)
        resources = count_expander.expand_all(resources)
        
        logger.info(f"After count expansion: {len(resources)} resources")
        
        # Stage 5: Expand for_each
        logger.info("Stage 5: Expanding for_each")
        foreach_expander = ForEachExpander(evaluator, self.max_expansion)
        resources = foreach_expander.expand_all(resources)
        
        logger.info(f"After for_each expansion: {len(resources)} resources")
        
        # Stage 6: Final resolution and validation
        logger.info("Stage 6: Final resolution and validation")
        expanded_resources = self._finalize_resources(resources, evaluator)
        
        logger.info(f"Evaluation complete: {len(expanded_resources)} fully expanded resources")
        return expanded_resources
    
    def _finalize_resources(
        self,
        resources: List[Dict[str, Any]],
        evaluator: ExpressionEvaluator
    ) -> List[ExpandedResource]:
        """
        Finalize resources into ExpandedResource objects.
        
        Args:
            resources: Expanded resources
            evaluator: Expression evaluator
        
        Returns:
            List of ExpandedResource objects
        
        Raises:
            TerraformEvaluationError: If any attribute cannot be resolved
        """
        expanded = []
        
        for resource in resources:
            try:
                # Get logical ID (set by expanders or use name)
                logical_id = resource.get("logical_id", resource.get("name"))
                
                # Get physical index (from count or for_each)
                physical_index = resource.get("physical_index", 0)
                
                # Resolve all attributes
                resolved_attrs = evaluator.evaluate(
                    resource.get("attributes", {}),
                    f"resource {logical_id}"
                )
                
                # Extract region
                resolved_region = self._extract_region(resolved_attrs)
                
                # Create ExpandedResource
                expanded_resource = ExpandedResource(
                    logical_id=logical_id,
                    resource_type=resource.get("type"),
                    physical_index=physical_index,
                    resolved_attributes=resolved_attrs,
                    resolved_region=resolved_region
                )
                
                expanded.append(expanded_resource)
            
            except Exception as e:
                logger.error(f"Failed to finalize resource {resource.get('name')}: {e}")
                raise TerraformEvaluationError(
                    f"Resource finalization failed for {resource.get('name')}: {e}"
                )
        
        return expanded
    
    def _extract_region(self, attributes: Dict[str, Any]) -> str:
        """
        Extract AWS region from resource attributes.
        
        Args:
            attributes: Resolved resource attributes
        
        Returns:
            AWS region code
        """
        # Check for explicit region attribute
        if "region" in attributes:
            return str(attributes["region"])
        
        # Check for availability_zone and extract region
        if "availability_zone" in attributes:
            az = str(attributes["availability_zone"])
            # Strip AZ suffix (e.g., us-east-1a -> us-east-1)
            if az and az[-1].isalpha():
                return az[:-1]
            return az
        
        # Default to us-east-1
        return "us-east-1"
