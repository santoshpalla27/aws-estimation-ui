"""
Unit tests for cost analytics with explicit resource status.
"""
import pytest
from decimal import Decimal

from app.engine.analytics import (
    ResourceStatus,
    ResourceCostResult,
    CostAnalytics,
    CostAggregator
)


class TestResourceCostResult:
    """Test resource cost result validation."""
    
    def test_supported_resource_valid(self):
        """Test creating valid SUPPORTED resource."""
        result = ResourceCostResult(
            resource_id="web-1",
            resource_type="aws_instance",
            resource_name="web-server",
            status=ResourceStatus.SUPPORTED,
            monthly_cost=Decimal("100.50"),
            pricing_rule_id=123,
            calculation_steps=[{"step": "calc"}],
            service_code="AmazonEC2",
            region="us-east-1"
        )
        
        assert result.status == ResourceStatus.SUPPORTED
        assert result.monthly_cost == Decimal("100.50")
    
    def test_supported_without_pricing_rule_fails(self):
        """Test SUPPORTED resource must have pricing_rule_id."""
        with pytest.raises(ValueError, match="must have pricing_rule_id"):
            ResourceCostResult(
                resource_id="web-1",
                resource_type="aws_instance",
                resource_name="web",
                status=ResourceStatus.SUPPORTED,
                monthly_cost=Decimal("100"),
                pricing_rule_id=None,  # Missing!
                calculation_steps=[{"step": "calc"}]
            )
    
    def test_supported_without_calculation_steps_fails(self):
        """Test SUPPORTED resource must have calculation_steps."""
        with pytest.raises(ValueError, match="must have calculation_steps"):
            ResourceCostResult(
                resource_id="web-1",
                resource_type="aws_instance",
                resource_name="web",
                status=ResourceStatus.SUPPORTED,
                monthly_cost=Decimal("100"),
                pricing_rule_id=123,
                calculation_steps=[]  # Empty!
            )
    
    def test_unsupported_resource_valid(self):
        """Test creating valid UNSUPPORTED resource."""
        result = ResourceCostResult(
            resource_id="vpc-1",
            resource_type="aws_vpc",
            resource_name="main-vpc",
            status=ResourceStatus.UNSUPPORTED,
            unsupported_reason="VPC resources have no direct cost",
            service_code="AmazonVPC"
        )
        
        assert result.status == ResourceStatus.UNSUPPORTED
        assert result.monthly_cost == Decimal("0")
    
    def test_unsupported_without_reason_fails(self):
        """Test UNSUPPORTED resource must have reason."""
        with pytest.raises(ValueError, match="must have unsupported_reason"):
            ResourceCostResult(
                resource_id="vpc-1",
                resource_type="aws_vpc",
                resource_name="vpc",
                status=ResourceStatus.UNSUPPORTED,
                unsupported_reason=None  # Missing!
            )
    
    def test_error_resource_valid(self):
        """Test creating valid ERROR resource."""
        result = ResourceCostResult(
            resource_id="db-1",
            resource_type="aws_db_instance",
            resource_name="database",
            status=ResourceStatus.ERROR,
            error_message="No pricing found for instance class",
            service_code="AmazonRDS"
        )
        
        assert result.status == ResourceStatus.ERROR
        assert result.error_message is not None
    
    def test_error_without_message_fails(self):
        """Test ERROR resource must have error_message."""
        with pytest.raises(ValueError, match="must have error_message"):
            ResourceCostResult(
                resource_id="db-1",
                resource_type="aws_db_instance",
                resource_name="db",
                status=ResourceStatus.ERROR,
                error_message=None  # Missing!
            )


class TestCostAggregator:
    """Test cost aggregation with explicit status."""
    
    def test_aggregate_supported_only(self):
        """Test aggregating only SUPPORTED resources."""
        results = [
            ResourceCostResult(
                resource_id="ec2-1",
                resource_type="aws_instance",
                resource_name="web-1",
                status=ResourceStatus.SUPPORTED,
                monthly_cost=Decimal("100"),
                pricing_rule_id=1,
                calculation_steps=[{}],
                service_code="AmazonEC2",
                region="us-east-1"
            ),
            ResourceCostResult(
                resource_id="ec2-2",
                resource_type="aws_instance",
                resource_name="web-2",
                status=ResourceStatus.SUPPORTED,
                monthly_cost=Decimal("150"),
                pricing_rule_id=1,
                calculation_steps=[{}],
                service_code="AmazonEC2",
                region="us-east-1"
            )
        ]
        
        aggregator = CostAggregator(results)
        analytics = aggregator.aggregate()
        
        assert analytics.total_monthly_cost == Decimal("250")
        assert analytics.total_supported_resources == 2
        assert analytics.total_resources == 2
        assert analytics.coverage_percentage == 100.0
        assert len(analytics.unsupported_resources) == 0
        assert len(analytics.error_resources) == 0
    
    def test_aggregate_excludes_unsupported(self):
        """Test UNSUPPORTED resources excluded from totals."""
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
                unsupported_reason="No direct cost",
                service_code="AmazonVPC"
            )
        ]
        
        aggregator = CostAggregator(results)
        analytics = aggregator.aggregate()
        
        # Total includes SUPPORTED only
        assert analytics.total_monthly_cost == Decimal("100")
        assert analytics.total_supported_resources == 1
        assert analytics.total_resources == 2
        assert analytics.coverage_percentage == 50.0
        
        # UNSUPPORTED reported separately
        assert len(analytics.unsupported_resources) == 1
        assert analytics.unsupported_resources[0].resource_id == "vpc-1"
    
    def test_aggregate_excludes_errors(self):
        """Test ERROR resources excluded from totals."""
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
                resource_id="db-1",
                resource_type="aws_db_instance",
                resource_name="db",
                status=ResourceStatus.ERROR,
                error_message="Pricing match failed",
                service_code="AmazonRDS"
            )
        ]
        
        aggregator = CostAggregator(results)
        analytics = aggregator.aggregate()
        
        # Total includes SUPPORTED only
        assert analytics.total_monthly_cost == Decimal("100")
        assert analytics.total_supported_resources == 1
        
        # ERROR reported separately
        assert len(analytics.error_resources) == 1
        assert analytics.error_resources[0].resource_id == "db-1"
    
    def test_aggregate_by_service(self):
        """Test aggregation by service (SUPPORTED only)."""
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
                resource_id="s3-1",
                resource_type="aws_s3_bucket",
                resource_name="bucket",
                status=ResourceStatus.SUPPORTED,
                monthly_cost=Decimal("50"),
                pricing_rule_id=2,
                calculation_steps=[{}],
                service_code="AmazonS3"
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
        
        # Only SUPPORTED resources in breakdown
        assert analytics.cost_by_service["AmazonEC2"] == Decimal("100")
        assert analytics.cost_by_service["AmazonS3"] == Decimal("50")
        assert "AmazonVPC" not in analytics.cost_by_service
    
    def test_aggregate_by_region(self):
        """Test aggregation by region (SUPPORTED only)."""
        results = [
            ResourceCostResult(
                resource_id="ec2-1",
                resource_type="aws_instance",
                resource_name="web-east",
                status=ResourceStatus.SUPPORTED,
                monthly_cost=Decimal("100"),
                pricing_rule_id=1,
                calculation_steps=[{}],
                region="us-east-1"
            ),
            ResourceCostResult(
                resource_id="ec2-2",
                resource_type="aws_instance",
                resource_name="web-west",
                status=ResourceStatus.SUPPORTED,
                monthly_cost=Decimal("120"),
                pricing_rule_id=1,
                calculation_steps=[{}],
                region="us-west-2"
            )
        ]
        
        aggregator = CostAggregator(results)
        analytics = aggregator.aggregate()
        
        assert analytics.cost_by_region["us-east-1"] == Decimal("100")
        assert analytics.cost_by_region["us-west-2"] == Decimal("120")
    
    def test_get_unsupported_summary(self):
        """Test getting unsupported resources summary."""
        results = [
            ResourceCostResult(
                resource_id="vpc-1",
                resource_type="aws_vpc",
                resource_name="vpc1",
                status=ResourceStatus.UNSUPPORTED,
                unsupported_reason="No direct cost"
            ),
            ResourceCostResult(
                resource_id="vpc-2",
                resource_type="aws_vpc",
                resource_name="vpc2",
                status=ResourceStatus.UNSUPPORTED,
                unsupported_reason="No direct cost"
            ),
            ResourceCostResult(
                resource_id="custom-1",
                resource_type="custom_resource",
                resource_name="custom",
                status=ResourceStatus.UNSUPPORTED,
                unsupported_reason="Custom resource type"
            )
        ]
        
        aggregator = CostAggregator(results)
        summary = aggregator.get_unsupported_summary()
        
        assert len(summary["No direct cost"]) == 2
        assert len(summary["Custom resource type"]) == 1
    
    def test_get_error_summary(self):
        """Test getting error resources summary."""
        results = [
            ResourceCostResult(
                resource_id="db-1",
                resource_type="aws_db_instance",
                resource_name="db1",
                status=ResourceStatus.ERROR,
                error_message="PricingMatchError: No pricing found"
            ),
            ResourceCostResult(
                resource_id="db-2",
                resource_type="aws_db_instance",
                resource_name="db2",
                status=ResourceStatus.ERROR,
                error_message="PricingMatchError: Invalid region"
            ),
            ResourceCostResult(
                resource_id="ec2-1",
                resource_type="aws_instance",
                resource_name="web",
                status=ResourceStatus.ERROR,
                error_message="ValidationError: Missing attribute"
            )
        ]
        
        aggregator = CostAggregator(results)
        summary = aggregator.get_error_summary()
        
        assert len(summary["PricingMatchError"]) == 2
        assert len(summary["ValidationError"]) == 1
    
    def test_get_missing_coverage(self):
        """Test getting missing pricing coverage by service."""
        results = [
            ResourceCostResult(
                resource_id="vpc-1",
                resource_type="aws_vpc",
                resource_name="vpc1",
                status=ResourceStatus.UNSUPPORTED,
                unsupported_reason="No adapter",
                service_code="AmazonVPC"
            ),
            ResourceCostResult(
                resource_id="vpc-2",
                resource_type="aws_vpc",
                resource_name="vpc2",
                status=ResourceStatus.UNSUPPORTED,
                unsupported_reason="No adapter",
                service_code="AmazonVPC"
            ),
            ResourceCostResult(
                resource_id="cf-1",
                resource_type="aws_cloudfront",
                resource_name="cdn",
                status=ResourceStatus.UNSUPPORTED,
                unsupported_reason="No adapter",
                service_code="AmazonCloudFront"
            )
        ]
        
        aggregator = CostAggregator(results)
        coverage = aggregator.get_missing_coverage()
        
        assert coverage["AmazonVPC"] == 2
        assert coverage["AmazonCloudFront"] == 1
    
    def test_no_inference_from_zero_cost(self):
        """Test that zero cost doesn't imply unsupported."""
        # A SUPPORTED resource can have zero cost (e.g., free tier)
        results = [
            ResourceCostResult(
                resource_id="lambda-1",
                resource_type="aws_lambda_function",
                resource_name="func",
                status=ResourceStatus.SUPPORTED,  # Explicitly SUPPORTED
                monthly_cost=Decimal("0"),  # But zero cost (free tier)
                pricing_rule_id=1,
                calculation_steps=[{"free_tier": "applied"}],
                service_code="AWSLambda"
            )
        ]
        
        aggregator = CostAggregator(results)
        analytics = aggregator.aggregate()
        
        # Zero-cost SUPPORTED resource IS included in totals
        assert analytics.total_monthly_cost == Decimal("0")
        assert analytics.total_supported_resources == 1
        assert len(analytics.unsupported_resources) == 0
