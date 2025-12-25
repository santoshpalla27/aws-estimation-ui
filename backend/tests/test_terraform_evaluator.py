"""
Unit tests for Terraform Semantic Evaluation Engine.
Tests all expansion scenarios with strict validation.
"""
import pytest
from pathlib import Path

from app.terraform.evaluator.expression_eval import ExpressionEvaluator
from app.terraform.evaluator.count_expander import CountExpander
from app.terraform.evaluator.foreach_expander import ForEachExpander
from app.terraform.evaluator.conditional_eval import ConditionalEvaluator
from app.terraform.evaluator.errors import (
    UnresolvedReferenceError,
    InvalidExpressionError,
    ExpansionLimitExceededError,
    DynamicValueError
)


class TestExpressionEvaluator:
    """Test expression evaluation."""
    
    def test_variable_reference(self):
        """Test variable reference resolution."""
        evaluator = ExpressionEvaluator(
            variables={"instance_type": "t3.micro"},
            locals_dict={}
        )
        
        result = evaluator.evaluate("${var.instance_type}")
        assert result == "t3.micro"
    
    def test_local_reference(self):
        """Test local reference resolution."""
        evaluator = ExpressionEvaluator(
            variables={},
            locals_dict={"environment": "production"}
        )
        
        result = evaluator.evaluate("${local.environment}")
        assert result == "production"
    
    def test_unresolved_reference_fails(self):
        """Test that unresolved references fail fast."""
        evaluator = ExpressionEvaluator(variables={}, locals_dict={})
        
        with pytest.raises(UnresolvedReferenceError) as exc:
            evaluator.evaluate("${var.missing}")
        
        assert "var.missing" in str(exc.value)
    
    def test_arithmetic_expressions(self):
        """Test arithmetic operations."""
        evaluator = ExpressionEvaluator(
            variables={"count": 5, "multiplier": 2},
            locals_dict={}
        )
        
        assert evaluator.evaluate("${var.count + 3}") == 8
        assert evaluator.evaluate("${var.count * var.multiplier}") == 10
        assert evaluator.evaluate("${var.count - 1}") == 4
        assert evaluator.evaluate("${var.count / 2}") == 2.5
    
    def test_comparison_expressions(self):
        """Test comparison operations."""
        evaluator = ExpressionEvaluator(
            variables={"count": 5},
            locals_dict={}
        )
        
        assert evaluator.evaluate("${var.count > 3}") is True
        assert evaluator.evaluate("${var.count < 10}") is True
        assert evaluator.evaluate("${var.count == 5}") is True
        assert evaluator.evaluate("${var.count != 3}") is True
    
    def test_ternary_conditional(self):
        """Test ternary conditional expressions."""
        evaluator = ExpressionEvaluator(
            variables={"enabled": True, "disabled": False},
            locals_dict={}
        )
        
        result = evaluator.evaluate("${var.enabled ? \"yes\" : \"no\"}")
        assert result == "yes"
        
        result = evaluator.evaluate("${var.disabled ? \"yes\" : \"no\"}")
        assert result == "no"
    
    def test_logical_operators(self):
        """Test logical AND/OR operations."""
        evaluator = ExpressionEvaluator(
            variables={"a": True, "b": False},
            locals_dict={}
        )
        
        assert evaluator.evaluate("${var.a && var.a}") is True
        assert evaluator.evaluate("${var.a && var.b}") is False
        assert evaluator.evaluate("${var.a || var.b}") is True
        assert evaluator.evaluate("${var.b || var.b}") is False
    
    def test_string_interpolation(self):
        """Test string interpolation."""
        evaluator = ExpressionEvaluator(
            variables={"name": "web", "env": "prod"},
            locals_dict={}
        )
        
        result = evaluator.evaluate("${var.name}-${var.env}")
        assert result == "web-prod"
    
    def test_function_length(self):
        """Test length() function."""
        evaluator = ExpressionEvaluator(
            variables={"items": ["a", "b", "c"]},
            locals_dict={}
        )
        
        result = evaluator.evaluate("${length(var.items)}")
        assert result == 3
    
    def test_function_min_max(self):
        """Test min() and max() functions."""
        evaluator = ExpressionEvaluator(variables={}, locals_dict={})
        
        assert evaluator.evaluate("${min(1, 5, 3)}") == 1
        assert evaluator.evaluate("${max(1, 5, 3)}") == 5
    
    def test_dynamic_value_fails(self):
        """Test that dynamic values (resource references) fail fast."""
        evaluator = ExpressionEvaluator(variables={}, locals_dict={})
        
        with pytest.raises(DynamicValueError):
            evaluator.evaluate("${data.aws_ami.latest.id}")
        
        with pytest.raises(DynamicValueError):
            evaluator.evaluate("${resource.aws_instance.web.id}")


class TestCountExpander:
    """Test count expansion."""
    
    def test_count_zero(self):
        """Test count = 0 produces no resources."""
        evaluator = ExpressionEvaluator(variables={"count": 0}, locals_dict={})
        expander = CountExpander(evaluator)
        
        resource = {
            "name": "web",
            "type": "aws_instance",
            "attributes": {"count": "${var.count}"}
        }
        
        result = expander.expand(resource)
        assert len(result) == 0
    
    def test_count_one(self):
        """Test count = 1 produces one resource."""
        evaluator = ExpressionEvaluator(variables={"count": 1}, locals_dict={})
        expander = CountExpander(evaluator)
        
        resource = {
            "name": "web",
            "type": "aws_instance",
            "attributes": {"count": "${var.count}"}
        }
        
        result = expander.expand(resource)
        assert len(result) == 1
        assert result[0]["logical_id"] == "web[0]"
        assert result[0]["count_index"] == 0
    
    def test_count_multiple(self):
        """Test count = N produces N resources."""
        evaluator = ExpressionEvaluator(variables={"count": 5}, locals_dict={})
        expander = CountExpander(evaluator)
        
        resource = {
            "name": "web",
            "type": "aws_instance",
            "attributes": {"count": "${var.count}"}
        }
        
        result = expander.expand(resource)
        assert len(result) == 5
        
        for i in range(5):
            assert result[i]["logical_id"] == f"web[{i}]"
            assert result[i]["count_index"] == i
    
    def test_count_index_resolution(self):
        """Test count.index is resolved in attributes."""
        evaluator = ExpressionEvaluator(variables={"count": 3}, locals_dict={})
        expander = CountExpander(evaluator)
        
        resource = {
            "name": "web",
            "type": "aws_instance",
            "attributes": {
                "count": "${var.count}",
                "name": "server-${count.index}"
            }
        }
        
        result = expander.expand(resource)
        assert result[0]["attributes"]["name"] == "server-0"
        assert result[1]["attributes"]["name"] == "server-1"
        assert result[2]["attributes"]["name"] == "server-2"
    
    def test_count_limit_exceeded(self):
        """Test expansion limit is enforced."""
        evaluator = ExpressionEvaluator(variables={"count": 2000}, locals_dict={})
        expander = CountExpander(evaluator, max_expansion=1000)
        
        resource = {
            "name": "web",
            "type": "aws_instance",
            "attributes": {"count": "${var.count}"}
        }
        
        with pytest.raises(ExpansionLimitExceededError) as exc:
            expander.expand(resource)
        
        assert exc.value.count == 2000
        assert exc.value.limit == 1000
    
    def test_count_invalid_type(self):
        """Test invalid count type fails."""
        evaluator = ExpressionEvaluator(variables={"count": "invalid"}, locals_dict={})
        expander = CountExpander(evaluator)
        
        resource = {
            "name": "web",
            "type": "aws_instance",
            "attributes": {"count": "${var.count}"}
        }
        
        with pytest.raises(InvalidExpressionError):
            expander.expand(resource)


class TestForEachExpander:
    """Test for_each expansion."""
    
    def test_foreach_map(self):
        """Test for_each with map."""
        evaluator = ExpressionEvaluator(
            variables={"instances": {"prod": "t3.large", "dev": "t3.micro"}},
            locals_dict={}
        )
        expander = ForEachExpander(evaluator)
        
        resource = {
            "name": "web",
            "type": "aws_instance",
            "attributes": {
                "for_each": "${var.instances}",
                "instance_type": "${each.value}"
            }
        }
        
        result = expander.expand(resource)
        assert len(result) == 2
        
        # Find prod and dev instances
        prod = next(r for r in result if r["for_each_key"] == "prod")
        dev = next(r for r in result if r["for_each_key"] == "dev")
        
        assert prod["logical_id"] == 'web["prod"]'
        assert prod["attributes"]["instance_type"] == "t3.large"
        
        assert dev["logical_id"] == 'web["dev"]'
        assert dev["attributes"]["instance_type"] == "t3.micro"
    
    def test_foreach_set(self):
        """Test for_each with set/list."""
        evaluator = ExpressionEvaluator(
            variables={"regions": ["us-east-1", "us-west-2"]},
            locals_dict={}
        )
        expander = ForEachExpander(evaluator)
        
        resource = {
            "name": "bucket",
            "type": "aws_s3_bucket",
            "attributes": {
                "for_each": "${var.regions}",
                "region": "${each.value}"
            }
        }
        
        result = expander.expand(resource)
        assert len(result) == 2
        
        assert result[0]["attributes"]["region"] == "us-east-1"
        assert result[1]["attributes"]["region"] == "us-west-2"
    
    def test_foreach_empty(self):
        """Test for_each with empty collection produces no resources."""
        evaluator = ExpressionEvaluator(variables={"items": {}}, locals_dict={})
        expander = ForEachExpander(evaluator)
        
        resource = {
            "name": "web",
            "type": "aws_instance",
            "attributes": {"for_each": "${var.items}"}
        }
        
        result = expander.expand(resource)
        assert len(result) == 0
    
    def test_foreach_each_key_resolution(self):
        """Test each.key is resolved in attributes."""
        evaluator = ExpressionEvaluator(
            variables={"envs": {"prod": "large", "dev": "small"}},
            locals_dict={}
        )
        expander = ForEachExpander(evaluator)
        
        resource = {
            "name": "web",
            "type": "aws_instance",
            "attributes": {
                "for_each": "${var.envs}",
                "name": "server-${each.key}",
                "size": "${each.value}"
            }
        }
        
        result = expander.expand(resource)
        
        prod = next(r for r in result if r["for_each_key"] == "prod")
        assert prod["attributes"]["name"] == "server-prod"
        assert prod["attributes"]["size"] == "large"
    
    def test_foreach_limit_exceeded(self):
        """Test expansion limit is enforced."""
        large_map = {f"item{i}": i for i in range(2000)}
        evaluator = ExpressionEvaluator(variables={"items": large_map}, locals_dict={})
        expander = ForEachExpander(evaluator, max_expansion=1000)
        
        resource = {
            "name": "web",
            "type": "aws_instance",
            "attributes": {"for_each": "${var.items}"}
        }
        
        with pytest.raises(ExpansionLimitExceededError):
            expander.expand(resource)


class TestConditionalEvaluator:
    """Test conditional evaluation."""
    
    def test_conditional_count_true(self):
        """Test conditional count = 1 when condition is true."""
        evaluator = ExpressionEvaluator(variables={"create": True}, locals_dict={})
        conditional = ConditionalEvaluator(evaluator)
        
        resource = {
            "name": "web",
            "type": "aws_instance",
            "attributes": {"count": "${var.create ? 1 : 0}"}
        }
        
        result = conditional.evaluate_resource_condition(resource)
        assert result is not None
    
    def test_conditional_count_false(self):
        """Test conditional count = 0 when condition is false."""
        evaluator = ExpressionEvaluator(variables={"create": False}, locals_dict={})
        conditional = ConditionalEvaluator(evaluator)
        
        resource = {
            "name": "web",
            "type": "aws_instance",
            "attributes": {"count": "${var.create ? 1 : 0}"}
        }
        
        result = conditional.evaluate_resource_condition(resource)
        assert result is None
    
    def test_conditional_attributes(self):
        """Test conditional attribute values."""
        evaluator = ExpressionEvaluator(
            variables={"env": "prod", "is_prod": True},
            locals_dict={}
        )
        conditional = ConditionalEvaluator(evaluator)
        
        attributes = {
            "instance_type": "${var.is_prod ? \"t3.large\" : \"t3.micro\"}",
            "name": "${var.env}-server"
        }
        
        result = conditional.evaluate_attribute_conditionals(attributes)
        assert result["instance_type"] == "t3.large"
        assert result["name"] == "prod-server"
    
    def test_nested_conditionals(self):
        """Test nested conditional expressions."""
        evaluator = ExpressionEvaluator(
            variables={"tier": "premium"},
            locals_dict={}
        )
        conditional = ConditionalEvaluator(evaluator)
        
        attributes = {
            "size": "${var.tier == \"premium\" ? \"xlarge\" : var.tier == \"standard\" ? \"large\" : \"small\"}"
        }
        
        result = conditional.evaluate_attribute_conditionals(attributes)
        assert result["size"] == "xlarge"


class TestIntegration:
    """Integration tests for complete evaluation pipeline."""
    
    def test_count_and_conditionals(self):
        """Test count expansion with conditional attributes."""
        evaluator = ExpressionEvaluator(
            variables={"count": 3, "env": "prod"},
            locals_dict={}
        )
        
        conditional = ConditionalEvaluator(evaluator)
        count_expander = CountExpander(evaluator)
        
        resource = {
            "name": "web",
            "type": "aws_instance",
            "attributes": {
                "count": "${var.count}",
                "instance_type": "${var.env == \"prod\" ? \"t3.large\" : \"t3.micro\"}",
                "name": "server-${count.index}"
            }
        }
        
        # Resolve conditionals first
        resolved = conditional.resolve_all_conditionals([resource])
        
        # Then expand count
        expanded = count_expander.expand_all(resolved)
        
        assert len(expanded) == 3
        for i, res in enumerate(expanded):
            assert res["attributes"]["instance_type"] == "t3.large"
            assert res["attributes"]["name"] == f"server-{i}"
    
    def test_foreach_with_conditionals(self):
        """Test for_each expansion with conditional attributes."""
        evaluator = ExpressionEvaluator(
            variables={
                "instances": {"prod": True, "dev": False},
                "base_type": "t3"
            },
            locals_dict={}
        )
        
        conditional = ConditionalEvaluator(evaluator)
        foreach_expander = ForEachExpander(evaluator)
        
        resource = {
            "name": "web",
            "type": "aws_instance",
            "attributes": {
                "for_each": "${var.instances}",
                "instance_type": "${each.value ? \"${var.base_type}.large\" : \"${var.base_type}.micro\"}",
                "name": "${each.key}-server"
            }
        }
        
        # Resolve conditionals first
        resolved = conditional.resolve_all_conditionals([resource])
        
        # Then expand for_each
        expanded = foreach_expander.expand_all(resolved)
        
        assert len(expanded) == 2
        
        prod = next(r for r in expanded if r["for_each_key"] == "prod")
        dev = next(r for r in expanded if r["for_each_key"] == "dev")
        
        assert prod["attributes"]["instance_type"] == "t3.large"
        assert dev["attributes"]["instance_type"] == "t3.micro"
