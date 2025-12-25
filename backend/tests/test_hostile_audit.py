"""
Hostile audit test cases.
Tests that validate fail-fast behavior and explicit status.
"""
import pytest
from decimal import Decimal

from app.terraform.evaluator.engine import TerraformEvaluationEngine
from app.terraform.evaluator.errors import (
    UnresolvedReferenceError,
    InvalidExpressionError
)
from app.engine.analytics import ResourceStatus, ResourceCostResult


class TestHostileAudit:
    """Hostile audit test cases to validate correctness."""
    
    def test_missing_variable_fails(self):
        """Test 1: Missing variables cause ERROR, not silent success."""
        terraform_code = """
        variable "region" {
          default = "us-east-1"
        }
        
        resource "aws_instance" "web" {
          instance_type = var.missing_var  # Should ERROR
          region = var.region
        }
        """
        
        engine = TerraformEvaluationEngine()
        
        with pytest.raises(UnresolvedReferenceError, match="var.missing_var"):
            # This should FAIL FAST, not return $0
            engine.evaluate_terraform_string(terraform_code)
    
    def test_for_each_map_expansion(self):
        """Test 2: for_each maps expand correctly."""
        terraform_code = """
        variable "instances" {
          default = {
            prod = "t3.large"
            dev  = "t3.micro"
          }
        }
        
        resource "aws_instance" "app" {
          for_each      = var.instances
          instance_type = each.value
          region        = "us-east-1"
        }
        """
        
        engine = TerraformEvaluationEngine()
        expanded = engine.evaluate_terraform_string(terraform_code)
        
        # Should create 2 resources
        assert len(expanded) == 2
        
        # Check logical IDs
        ids = {r.logical_id for r in expanded}
        assert 'app["prod"]' in ids
        assert 'app["dev"]' in ids
        
        # Check instance types
        prod = next(r for r in expanded if r.physical_index == "prod")
        assert prod.resolved_attributes["instance_type"] == "t3.large"
    
    def test_unsupported_resource_explicit_status(self):
        """Test 5: Unsupported resources have UNSUPPORTED status, not $0."""
        # VPC has no direct cost
        result = ResourceCostResult(
            resource_id="vpc-1",
            resource_type="aws_vpc",
            resource_name="main",
            status=ResourceStatus.UNSUPPORTED,
            unsupported_reason="VPC resources have no direct cost",
            service_code="AmazonVPC"
        )
        
        # Verify status is explicit
        assert result.status == ResourceStatus.UNSUPPORTED
        assert result.unsupported_reason is not None
        assert result.monthly_cost == Decimal("0")
        
        # This is CORRECT: zero cost with explicit UNSUPPORTED status
        # NOT: zero cost with SUPPORTED status (which would be wrong)
    
    def test_no_silent_zero_cost(self):
        """Test: SUPPORTED resources with $0 must have explicit reason."""
        # This should FAIL validation
        with pytest.raises(ValueError, match="must have pricing_rule_id"):
            ResourceCostResult(
                resource_id="test-1",
                resource_type="aws_instance",
                resource_name="web",
                status=ResourceStatus.SUPPORTED,
                monthly_cost=Decimal("0"),
                pricing_rule_id=None,  # Missing!
                calculation_steps=[]
            )
    
    def test_error_resource_explicit_message(self):
        """Test 6: ERROR resources have explicit error message."""
        result = ResourceCostResult(
            resource_id="db-1",
            resource_type="aws_db_instance",
            resource_name="database",
            status=ResourceStatus.ERROR,
            error_message="PricingMatchError: No pricing for db.t3.xlarge in eu-north-1",
            service_code="AmazonRDS"
        )
        
        assert result.status == ResourceStatus.ERROR
        assert result.error_message is not None
        assert "PricingMatchError" in result.error_message
    
    def test_coverage_warning_when_incomplete(self):
        """Test: Coverage < 100% triggers warning."""
        from app.engine.analytics import CostAggregator
        
        results = [
            ResourceCostResult(
                resource_id="ec2-1",
                resource_type="aws_instance",
                resource_name="web",
                status=ResourceStatus.SUPPORTED,
                monthly_cost=Decimal("100"),
                pricing_rule_id=1,
                calculation_steps=[{}],
                service_code="AmazonEC2"
            ),
            ResourceCostResult(
                resource_id="vpc-1",
                resource_type="aws_vpc",
                resource_name="vpc",
                status=ResourceStatus.UNSUPPORTED,
                unsupported_reason="No cost",
                service_code="AmazonVPC"
            )
        ]
        
        aggregator = CostAggregator(results)
        analytics = aggregator.aggregate()
        
        # Coverage should be 50%
        assert analytics.coverage_percentage == 50.0
        
        # Should have warning
        assert any("coverage" in w.lower() for w in analytics.global_warnings)
    
    def test_count_zero_produces_no_resources(self):
        """Test: count = 0 produces no resources, not ERROR."""
        terraform_code = """
        variable "create_db" {
          default = false
        }
        
        resource "aws_db_instance" "main" {
          count = var.create_db ? 1 : 0
          instance_class = "db.t3.micro"
        }
        """
        
        engine = TerraformEvaluationEngine()
        expanded = engine.evaluate_terraform_string(terraform_code)
        
        # Should create 0 resources (not an error)
        assert len(expanded) == 0
    
    def test_dynamic_value_fails(self):
        """Test: Dynamic values (data sources) cause ERROR."""
        terraform_code = """
        data "aws_ami" "latest" {
          most_recent = true
        }
        
        resource "aws_instance" "web" {
          ami = data.aws_ami.latest.id  # Dynamic!
          instance_type = "t3.micro"
        }
        """
        
        engine = TerraformEvaluationEngine()
        
        with pytest.raises(Exception):
            # Should fail - cannot resolve data source statically
            engine.evaluate_terraform_string(terraform_code)


class TestRegionEnforcement:
    """Test region resolution and enforcement."""
    
    def test_missing_region_fails(self):
        """Test: Missing region causes ERROR, not default."""
        from app.terraform.region_resolver import RegionResolver, RegionResolutionError
        
        resolver = RegionResolver()
        
        resource = {
            "type": "aws_instance",
            "name": "web",
            "instance_type": "t3.micro"
            # No region!
        }
        
        with pytest.raises(RegionResolutionError, match="Cannot determine region"):
            resolver.resolve_region(resource)
    
    def test_invalid_region_fails(self):
        """Test: Invalid region causes ERROR."""
        from app.terraform.region_resolver import RegionResolver, RegionResolutionError
        
        resolver = RegionResolver()
        
        with pytest.raises(RegionResolutionError, match="Invalid region"):
            resolver.validate_region("invalid-region-1", "test")
    
    def test_az_to_region_conversion(self):
        """Test: AZ correctly converted to region."""
        from app.terraform.region_resolver import RegionResolver
        
        resolver = RegionResolver()
        
        region = resolver.az_to_region("us-east-1a")
        assert region == "us-east-1"
        
        region = resolver.az_to_region("eu-west-2b")
        assert region == "eu-west-2"


class TestSecurityValidation:
    """Test file security validation."""
    
    def test_zip_slip_prevented(self):
        """Test: Zip Slip attack is prevented."""
        from app.security.file_validation import FileValidator, SecurityError
        
        with pytest.raises(SecurityError, match="Path traversal"):
            FileValidator.validate_filename("../../../etc/passwd")
    
    def test_absolute_path_rejected(self):
        """Test: Absolute paths are rejected."""
        from app.security.file_validation import FileValidator, SecurityError
        
        with pytest.raises(SecurityError, match="Absolute paths not allowed"):
            FileValidator.validate_filename("/etc/passwd")
    
    def test_invalid_extension_rejected(self):
        """Test: Invalid file extensions are rejected."""
        from app.security.file_validation import FileValidator, SecurityError
        
        with pytest.raises(SecurityError, match="File type not allowed"):
            FileValidator.validate_filename("malicious.exe")
