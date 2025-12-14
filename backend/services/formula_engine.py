"""
Formula Engine - Parses and executes cost formulas from plugin YAML files
"""

import yaml
import re
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class CalculationStep:
    """Represents a single calculation step"""
    id: str
    description: str
    formula: str
    output: str


@dataclass
class FormulaDefinition:
    """Parsed formula definition from cost_formula.yaml"""
    service: str
    version: str
    inputs: List[Dict[str, Any]]
    calculation_steps: List[CalculationStep]
    total_formula: str
    assumptions: List[str]
    pricing_sources: List[Dict[str, str]]


class FormulaEngine:
    """Engine to parse and execute cost formulas"""
    
    def __init__(self):
        self.context: Dict[str, Any] = {}
    
    def load_formula(self, formula_yaml: str) -> FormulaDefinition:
        """Load and parse formula from YAML string"""
        data = yaml.safe_load(formula_yaml)
        
        steps = [
            CalculationStep(
                id=step['id'],
                description=step['description'],
                formula=step['formula'],
                output=step['output']
            )
            for step in data.get('calculation_steps', [])
        ]
        
        return FormulaDefinition(
            service=data['service'],
            version=data['version'],
            inputs=data.get('inputs', []),
            calculation_steps=steps,
            total_formula=data['total_formula'],
            assumptions=data.get('assumptions', []),
            pricing_sources=data.get('pricing_sources', [])
        )
    
    def execute_formula(
        self,
        formula_def: FormulaDefinition,
        config: Dict[str, Any],
        pricing: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute formula with given configuration and pricing data
        
        Args:
            formula_def: Parsed formula definition
            config: User configuration
            pricing: Pricing data for the service/region
        
        Returns:
            {
                'total_cost': float,
                'breakdown': {step_id: cost_value},
                'assumptions': List[str],
                'confidence': float,
                'pricing_metadata': Dict (if pricing provided)
            }
        """
        # Initialize context with input config
        self.context = config.copy()
        
        # Inject pricing into context if provided
        if pricing:
            self.context['pricing'] = pricing
        
        breakdown = {}
        
        # Execute each calculation step
        for step in formula_def.calculation_steps:
            try:
                result = self._evaluate_expression(step.formula)
                self.context[step.output] = result
                breakdown[step.id] = {
                    'description': step.description,
                    'value': result,
                    'output_var': step.output
                }
            except Exception as e:
                raise ValueError(f"Error in step '{step.id}': {str(e)}")
        
        # Calculate total cost
        try:
            total_cost = self._evaluate_expression(formula_def.total_formula)
        except Exception as e:
            raise ValueError(f"Error calculating total: {str(e)}")
        
        # Calculate confidence score (simple heuristic)
        confidence = self._calculate_confidence(config, formula_def.inputs)
        
        result = {
            'total_cost': round(total_cost, 2),
            'breakdown': breakdown,
            'assumptions': formula_def.assumptions,
            'confidence': confidence,
            'service': formula_def.service
        }
        
        # Add pricing metadata if available
        if pricing and '_metadata' in pricing:
            result['pricing_metadata'] = pricing['_metadata']
        
        return result
    
    def _evaluate_expression(self, formula: str) -> float:
        """
        Evaluate a formula expression
        Supports:
        - Basic math: +, -, *, /, **
        - Comparisons: ==, !=, <, >, <=, >=
        - Conditionals: if/else
        - Functions: max(), min(), abs()
        - Variables from context
        """
        # Handle multi-line formulas (Python-like if/else)
        if 'if ' in formula and ':' in formula:
            return self._evaluate_conditional(formula)
        
        # Handle dictionary/map access
        formula = self._substitute_variables(formula)
        
        # Safe evaluation with limited globals
        safe_globals = {
            '__builtins__': {},
            'max': max,
            'min': min,
            'abs': abs,
            'round': round,
        }
        
        try:
            result = eval(formula, safe_globals, self.context)
            return float(result) if result is not None else 0.0
        except Exception as e:
            raise ValueError(f"Failed to evaluate formula '{formula}': {str(e)}")
    
    def _evaluate_conditional(self, formula: str) -> float:
        """Evaluate if/elif/else conditional expressions"""
        lines = [line.strip() for line in formula.strip().split('\n')]
        
        # Simple if/elif/else parser
        result = None
        skip_until_else = False
        
        for line in lines:
            if line.startswith('if '):
                condition = line[3:].rstrip(':')
                if self._evaluate_condition(condition):
                    skip_until_else = False
                else:
                    skip_until_else = True
            elif line.startswith('elif '):
                if skip_until_else:
                    condition = line[5:].rstrip(':')
                    if self._evaluate_condition(condition):
                        skip_until_else = False
            elif line.startswith('else:'):
                skip_until_else = False
            elif not skip_until_else and line and not line.startswith('#'):
                # This is the expression to evaluate
                result = self._evaluate_expression(line)
                skip_until_else = True  # Skip remaining branches
        
        return result if result is not None else 0.0
    
    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a boolean condition"""
        condition = self._substitute_variables(condition)
        
        safe_globals = {'__builtins__': {}}
        try:
            return bool(eval(condition, safe_globals, self.context))
        except:
            return False
    
    def _substitute_variables(self, formula: str) -> str:
        """Substitute variable references with values"""
        # Handle dictionary access like pricing_map.get(instance_class, {}).get(engine, 0.10)
        # For now, we'll keep it simple and let eval handle it
        return formula
    
    def _calculate_confidence(
        self,
        config: Dict[str, Any],
        input_schema: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate confidence score based on:
        - How many required inputs are provided
        - Whether default values are used
        - Data quality
        """
        required_inputs = [inp for inp in input_schema if inp.get('required', False)]
        provided_count = sum(1 for inp in required_inputs if inp['name'] in config)
        
        if not required_inputs:
            return 0.85
        
        base_confidence = provided_count / len(required_inputs)
        
        # Reduce confidence if using many default values
        default_count = sum(
            1 for inp in input_schema
            if inp['name'] not in config and 'default' in inp
        )
        default_penalty = default_count * 0.05
        
        return max(0.5, min(1.0, base_confidence - default_penalty))


# Example usage
if __name__ == "__main__":
    engine = FormulaEngine()
    
    # Example Lambda formula
    lambda_formula = """
service: AWSLambda
version: "1.0.0"
inputs:
  - name: memory_mb
    type: integer
    required: true
  - name: avg_duration_ms
    type: integer
    required: true
  - name: invocations_per_month
    type: integer
    required: true
calculation_steps:
  - id: compute_gb_seconds
    description: "Calculate GB-seconds"
    formula: "(memory_mb / 1024) * (avg_duration_ms / 1000) * invocations_per_month"
    output: compute_gb_seconds
  - id: compute_cost
    description: "Compute cost"
    formula: "compute_gb_seconds * 0.0000166667"
    output: compute_cost
total_formula: "compute_cost"
assumptions:
  - "AWS Free Tier not applied"
pricing_sources:
  - name: "AWS Lambda Pricing"
    url: "https://aws.amazon.com/lambda/pricing/"
"""
    
    formula_def = engine.load_formula(lambda_formula)
    result = engine.execute_formula(formula_def, {
        'memory_mb': 1024,
        'avg_duration_ms': 1000,
        'invocations_per_month': 1000000
    })
    
    print(f"Total Cost: ${result['total_cost']}")
    print(f"Confidence: {result['confidence']}")
