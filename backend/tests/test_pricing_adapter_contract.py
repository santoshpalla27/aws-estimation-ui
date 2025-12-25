"""
Unit tests for strict pricing adapter contract.
Validates that adapters cannot silently fail.
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, MagicMock

from app.pricing.adapters.base import (
    PricingAdapter,
    PricingRule,
    CostResult,
    CalculationStep,
    FreeTierStatus,
    ValidationError,
    PricingMatchError,
    CalculationError,
    UnitMismatchError
)
from app.pricing.adapters.ec2_strict import StrictEC2Adapter


class TestCostResult:
    """Test CostResult validation."""
    
    def test_valid_cost_result(self):
        """Test creating a valid CostResult."""
        steps = [
            CalculationStep(
                description="Test step",
                formula="1 + 1",
                inputs={"a": 1},
                result=Decimal("2"),
                unit="USD"
            )
        ]
        
        result = CostResult(
            monthly_cost=Decimal("100.50"),
            pricing_rule_id=123,
            unit="USD/month",
            calculation_steps=steps,
            free_tier_applied=FreeTierStatus.NOT_APPLICABLE
        )
        
        assert result.monthly_cost == Decimal("100.50")
        assert result.pricing_rule_id == 123
        assert len(result.calculation_steps) == 1
    
    def test_negative_cost_fails(self):
        """Test that negative costs are rejected."""
        steps = [CalculationStep("test", "1+1", {}, Decimal("1"), "USD")]
        
        with pytest.raises(CalculationError, match="cannot be negative"):
            CostResult(
                monthly_cost=Decimal("-10"),
                pricing_rule_id=123,
                unit="USD",
                calculation_steps=steps,
                free_tier_applied=FreeTierStatus.NOT_APPLICABLE
            )
    
    def test_missing_pricing_rule_id_fails(self):
        """Test that missing pricing_rule_id is rejected."""
        steps = [CalculationStep("test", "1+1", {}, Decimal("1"), "USD")]
        
        with pytest.raises(CalculationError, match="pricing_rule_id must be set"):
            CostResult(
                monthly_cost=Decimal("10"),
                pricing_rule_id=None,
                unit="USD",
                calculation_steps=steps,
                free_tier_applied=FreeTierStatus.NOT_APPLICABLE
            )
    
    def test_empty_calculation_steps_fails(self):
        """Test that empty calculation steps are rejected."""
        with pytest.raises(CalculationError, match="calculation_steps cannot be empty"):
            CostResult(
                monthly_cost=Decimal("10"),
                pricing_rule_id=123,
                unit="USD",
                calculation_steps=[],
                free_tier_applied=FreeTierStatus.NOT_APPLICABLE
            )
    
    def test_missing_free_tier_status_fails(self):
        """Test that missing free_tier_applied is rejected."""
        steps = [CalculationStep("test", "1+1", {}, Decimal("1"), "USD")]
        
        with pytest.raises(CalculationError, match="free_tier_applied must be explicitly set"):
            CostResult(
                monthly_cost=Decimal("10"),
                pricing_rule_id=123,
                unit="USD",
                calculation_steps=steps,
                free_tier_applied=None
            )


class TestPricingRule:
    """Test PricingRule validation."""
    
    def test_valid_pricing_rule(self):
        """Test creating a valid PricingRule."""
        rule = PricingRule(
            id=1,
            service_code="AmazonEC2",
            region_code="us-east-1",
            price_per_unit=Decimal("0.0116"),
            unit="Hrs",
            currency="USD",
            attributes={"instanceType": "t3.micro"}
        )
        
        assert rule.price_per_unit == Decimal("0.0116")
    
    def test_negative_price_fails(self):
        """Test that negative prices are rejected."""
        with pytest.raises(ValueError, match="cannot be negative"):
            PricingRule(
                id=1,
                service_code="AmazonEC2",
                region_code="us-east-1",
                price_per_unit=Decimal("-1"),
                unit="Hrs",
                currency="USD",
                attributes={}
            )


class TestStrictEC2Adapter:
    """Test strict EC2 adapter contract enforcement."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.db = Mock()
        self.pricing_version = Mock()
        self.pricing_version.id = 1
        self.adapter = StrictEC2Adapter(self.db, self.pricing_version)
    
    def test_required_attributes_declared(self):
        """Test that required attributes are declared."""
        assert "instance_type" in self.adapter.required_attributes
        assert "region" in self.adapter.required_attributes
    
    def test_supported_regions_declared(self):
        """Test that supported regions are declared."""
        assert "us-east-1" in self.adapter.supported_regions
        assert len(self.adapter.supported_regions) > 0
    
    def test_validate_missing_attribute_fails(self):
        """Test that missing required attributes cause validation to fail."""
        resource = {"region": "us-east-1"}  # Missing instance_type
        
        with pytest.raises(ValidationError, match="Missing required attributes"):
            self.adapter.validate(resource)
    
    def test_validate_unsupported_region_fails(self):
        """Test that unsupported regions cause validation to fail."""
        resource = {
            "instance_type": "t3.micro",
            "region": "invalid-region"
        }
        
        with pytest.raises(ValidationError, match="not supported"):
            self.adapter.validate(resource)
    
    def test_validate_invalid_instance_type_fails(self):
        """Test that invalid instance type format fails."""
        resource = {
            "instance_type": "invalid",  # No dot separator
            "region": "us-east-1"
        }
        
        with pytest.raises(ValidationError, match="Invalid instance_type format"):
            self.adapter.validate(resource)
    
    def test_validate_success(self):
        """Test successful validation."""
        resource = {
            "instance_type": "t3.micro",
            "region": "us-east-1"
        }
        
        # Should not raise
        self.adapter.validate(resource)
    
    def test_match_pricing_no_result_fails(self):
        """Test that no pricing match causes error."""
        resource = {
            "instance_type": "t3.micro",
            "region": "us-east-1"
        }
        
        # Mock database to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = mock_result
        
        with pytest.raises(PricingMatchError, match="No pricing found"):
            self.adapter.match_pricing(resource)
    
    def test_match_pricing_success(self):
        """Test successful pricing match."""
        resource = {
            "instance_type": "t3.micro",
            "region": "us-east-1"
        }
        
        # Mock database result
        mock_dimension = Mock()
        mock_dimension.id = 123
        mock_dimension.service_code = "AmazonEC2"
        mock_dimension.region_code = "us-east-1"
        mock_dimension.price_per_unit = Decimal("0.0116")
        mock_dimension.unit = "Hrs"
        mock_dimension.currency = "USD"
        mock_dimension.attributes = {"instanceType": "t3.micro"}
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_dimension
        self.db.execute.return_value = mock_result
        
        rule = self.adapter.match_pricing(resource)
        
        assert isinstance(rule, PricingRule)
        assert rule.id == 123
        assert rule.price_per_unit == Decimal("0.0116")
    
    def test_calculate_unit_mismatch_fails(self):
        """Test that unit mismatch causes error."""
        resource = {
            "instance_type": "t3.micro",
            "region": "us-east-1"
        }
        
        # Pricing rule with wrong unit
        pricing_rule = PricingRule(
            id=123,
            service_code="AmazonEC2",
            region_code="us-east-1",
            price_per_unit=Decimal("0.0116"),
            unit="GB",  # Wrong unit!
            currency="USD",
            attributes={}
        )
        
        with pytest.raises(UnitMismatchError, match="Unit mismatch"):
            self.adapter.calculate(resource, pricing_rule)
    
    def test_calculate_success(self):
        """Test successful cost calculation."""
        resource = {
            "instance_type": "t3.micro",
            "region": "us-east-1",
            "name": "web-server"
        }
        
        pricing_rule = PricingRule(
            id=123,
            service_code="AmazonEC2",
            region_code="us-east-1",
            price_per_unit=Decimal("0.0116"),
            unit="Hrs",
            currency="USD",
            attributes={"instanceType": "t3.micro"}
        )
        
        result = self.adapter.calculate(resource, pricing_rule)
        
        # Validate result
        assert isinstance(result, CostResult)
        assert result.monthly_cost > 0
        assert result.pricing_rule_id == 123
        assert result.unit == "USD/month"
        assert len(result.calculation_steps) == 3
        assert result.free_tier_applied in [FreeTierStatus.NOT_APPLICABLE, FreeTierStatus.EXCEEDED]
    
    def test_calculate_cost_pipeline(self):
        """Test complete calculate_cost pipeline."""
        resource = {
            "instance_type": "t3.micro",
            "region": "us-east-1"
        }
        
        # Mock pricing match
        mock_dimension = Mock()
        mock_dimension.id = 123
        mock_dimension.service_code = "AmazonEC2"
        mock_dimension.region_code = "us-east-1"
        mock_dimension.price_per_unit = Decimal("0.0116")
        mock_dimension.unit = "Hrs"
        mock_dimension.currency = "USD"
        mock_dimension.attributes = {"instanceType": "t3.micro"}
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_dimension
        self.db.execute.return_value = mock_result
        
        # Execute full pipeline
        result = self.adapter.calculate_cost(resource)
        
        # Validate complete result
        assert isinstance(result, CostResult)
        assert result.monthly_cost > 0
        assert len(result.calculation_steps) > 0


class TestAdapterContractEnforcement:
    """Test that adapter contract is enforced."""
    
    def test_adapter_must_return_cost_result(self):
        """Test that adapters must return CostResult, not None."""
        
        class BadAdapter(PricingAdapter):
            @property
            def required_attributes(self):
                return []
            
            @property
            def supported_regions(self):
                return ["us-east-1"]
            
            @property
            def service_code(self):
                return "Test"
            
            def validate(self, resource):
                pass
            
            def match_pricing(self, resource):
                return PricingRule(
                    id=1,
                    service_code="Test",
                    region_code="us-east-1",
                    price_per_unit=Decimal("1"),
                    unit="Hrs",
                    currency="USD",
                    attributes={}
                )
            
            def calculate(self, resource, pricing_rule):
                return None  # BAD! Must return CostResult
        
        adapter = BadAdapter()
        
        with pytest.raises(CalculationError, match="must return CostResult"):
            adapter.calculate_cost({})
