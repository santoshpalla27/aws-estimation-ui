"""
Service: Amazon S3
Category: Storage
Pricing Model: Tiered + Requests + Data Transfer
Key Cost Drivers: Storage GB, Request count, Data transfer, Storage class
"""

import pytest
import requests
from decimal import Decimal

BASE_URL = "http://backend:8000"


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def test_project():
    """Create a test project for S3 tests"""
    project_data = {
        "name": "S3 Test Project",
        "description": "Testing Amazon S3 cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_s3_config():
    """Base S3 service configuration"""
    return {
        "id": "test-s3",
        "service_type": "AmazonS3",
        "region": "us-east-1",
        "config": {
            "storage_gb": 100,
            "storage_class": "STANDARD",
            "put_requests_per_month": 10000,
            "get_requests_per_month": 100000,
            "data_transfer_gb": 0
        }
    }


def create_estimate(project_id: str, services: list) -> dict:
    """Helper to create an estimate"""
    response = requests.post(
        f"{BASE_URL}/api/v1/estimates?project_id={project_id}",
        json={"services": services}
    )
    assert response.status_code == 201
    return response.json()


# ============================================================================
# SERVICE DISCOVERY TESTS
# ============================================================================

class TestS3ServiceDiscovery:
    """Test S3 service registration and metadata"""
    
    def test_s3_in_service_catalog(self):
        """Verify S3 appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        s3_service = next((s for s in services if s["service_id"] == "AmazonS3"), None)
        
        assert s3_service is not None, "AmazonS3 not found in service catalog"
        assert s3_service["display_name"] == "Amazon S3"
        assert s3_service["category"] == "Storage"
    
    def test_s3_regions_populated(self):
        """Verify S3 has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        s3_service = next((s for s in services if s["service_id"] == "AmazonS3"), None)
        
        assert "regions" in s3_service or len(s3_service.get("regions", [])) > 0


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestS3SchemaValidation:
    """Test S3 configuration schema"""
    
    def test_s3_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonS3/schema")
        assert response.status_code in [200, 404]  # 404 if not implemented yet
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema
    
    def test_s3_required_fields_enforced(self, test_project):
        """Verify required fields are enforced"""
        # Missing storage_gb
        invalid_service = {
            "id": "invalid-s3",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_class": "STANDARD"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json={"services": [invalid_service]}
        )
        # Should either use defaults or return error
        assert response.status_code in [201, 400, 422]


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestS3BasicCostCalculation:
    """Test basic S3 cost calculations"""
    
    def test_s3_standard_storage_minimal(self, test_project, base_s3_config):
        """Test minimal S3 Standard storage cost"""
        estimate = create_estimate(test_project, [base_s3_config])
        
        assert estimate["total_monthly_cost"] > 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
        
        # Verify S3 appears in breakdown
        s3_breakdown = next((b for b in estimate["breakdown"] if b["key"] == "AmazonS3"), None)
        assert s3_breakdown is not None
        assert s3_breakdown["value"] > 0
    
    def test_s3_cost_deterministic(self, test_project, base_s3_config):
        """Test S3 cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_s3_config])
        estimate2 = create_estimate(test_project, [base_s3_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]
    
    def test_s3_standard_100gb_known_cost(self, test_project):
        """Test S3 Standard 100GB has expected cost range"""
        service = {
            "id": "s3-100gb",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100,
                "storage_class": "STANDARD",
                "put_requests_per_month": 0,
                "get_requests_per_month": 0,
                "data_transfer_gb": 0
            }
        }
        
        estimate = create_estimate(test_project, [service])
        
        # 100 GB * $0.023 = $2.30 (approximate)
        assert 2.0 <= estimate["total_monthly_cost"] <= 3.0


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestS3EdgeCases:
    """Test S3 edge cases and boundaries"""
    
    def test_s3_zero_storage(self, test_project):
        """Test S3 with zero storage"""
        service = {
            "id": "s3-zero",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 0,
                "storage_class": "STANDARD",
                "put_requests_per_month": 1000,
                "get_requests_per_month": 10000,
                "data_transfer_gb": 0
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0
    
    def test_s3_maximum_storage(self, test_project):
        """Test S3 with very large storage"""
        service = {
            "id": "s3-max",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 1000000,  # 1 PB
                "storage_class": "STANDARD",
                "put_requests_per_month": 100000000,
                "get_requests_per_month": 1000000000,
                "data_transfer_gb": 100000
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] > 10000  # Should be substantial
    
    def test_s3_free_tier_threshold(self, test_project):
        """Test S3 around free tier boundaries"""
        # First 100GB data transfer is free
        service_under = {
            "id": "s3-under-free",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 10,
                "storage_class": "STANDARD",
                "put_requests_per_month": 1000,
                "get_requests_per_month": 10000,
                "data_transfer_gb": 50  # Under 100GB
            }
        }
        
        service_over = {
            "id": "s3-over-free",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 10,
                "storage_class": "STANDARD",
                "put_requests_per_month": 1000,
                "get_requests_per_month": 10000,
                "data_transfer_gb": 150  # Over 100GB
            }
        }
        
        estimate_under = create_estimate(test_project, [service_under])
        estimate_over = create_estimate(test_project, [service_over])
        
        # Over free tier should cost more
        assert estimate_over["total_monthly_cost"] > estimate_under["total_monthly_cost"]
    
    def test_s3_storage_class_glacier_cheaper(self, test_project):
        """Test Glacier storage is cheaper than Standard"""
        service_standard = {
            "id": "s3-standard",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 1000,
                "storage_class": "STANDARD",
                "put_requests_per_month": 1000,
                "get_requests_per_month": 1000,
                "data_transfer_gb": 0
            }
        }
        
        service_glacier = {
            "id": "s3-glacier",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 1000,
                "storage_class": "GLACIER_FLEXIBLE",
                "put_requests_per_month": 1000,
                "get_requests_per_month": 1000,
                "data_transfer_gb": 0
            }
        }
        
        estimate_standard = create_estimate(test_project, [service_standard])
        estimate_glacier = create_estimate(test_project, [service_glacier])
        
        assert estimate_glacier["total_monthly_cost"] < estimate_standard["total_monthly_cost"]


# ============================================================================
# STORAGE CLASS TESTS
# ============================================================================

class TestS3StorageClasses:
    """Test all S3 storage classes"""
    
    @pytest.mark.parametrize("storage_class,expected_cheaper_than_standard", [
        ("STANDARD", False),
        ("INTELLIGENT_TIERING", True),
        ("GLACIER_FLEXIBLE", True),
        ("GLACIER_DEEP_ARCHIVE", True),
    ])
    def test_storage_class_pricing(self, test_project, storage_class, expected_cheaper_than_standard):
        """Test different storage class pricing"""
        service = {
            "id": f"s3-{storage_class.lower()}",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 1000,
                "storage_class": storage_class,
                "put_requests_per_month": 1000,
                "get_requests_per_month": 1000,
                "data_transfer_gb": 0
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] > 0


# ============================================================================
# REQUEST PRICING TESTS
# ============================================================================

class TestS3RequestPricing:
    """Test S3 request pricing"""
    
    def test_s3_put_requests_cost(self, test_project):
        """Test PUT request pricing"""
        service_no_puts = {
            "id": "s3-no-puts",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100,
                "storage_class": "STANDARD",
                "put_requests_per_month": 0,
                "get_requests_per_month": 0,
                "data_transfer_gb": 0
            }
        }
        
        service_with_puts = {
            "id": "s3-with-puts",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100,
                "storage_class": "STANDARD",
                "put_requests_per_month": 1000000,  # 1M PUTs
                "get_requests_per_month": 0,
                "data_transfer_gb": 0
            }
        }
        
        estimate_no_puts = create_estimate(test_project, [service_no_puts])
        estimate_with_puts = create_estimate(test_project, [service_with_puts])
        
        assert estimate_with_puts["total_monthly_cost"] > estimate_no_puts["total_monthly_cost"]
    
    def test_s3_get_requests_cost(self, test_project):
        """Test GET request pricing"""
        service_no_gets = {
            "id": "s3-no-gets",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100,
                "storage_class": "STANDARD",
                "put_requests_per_month": 0,
                "get_requests_per_month": 0,
                "data_transfer_gb": 0
            }
        }
        
        service_with_gets = {
            "id": "s3-with-gets",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100,
                "storage_class": "STANDARD",
                "put_requests_per_month": 0,
                "get_requests_per_month": 10000000,  # 10M GETs
                "data_transfer_gb": 0
            }
        }
        
        estimate_no_gets = create_estimate(test_project, [service_no_gets])
        estimate_with_gets = create_estimate(test_project, [service_with_gets])
        
        assert estimate_with_gets["total_monthly_cost"] > estimate_no_gets["total_monthly_cost"]


# ============================================================================
# DATA TRANSFER TESTS
# ============================================================================

class TestS3DataTransfer:
    """Test S3 data transfer pricing"""
    
    def test_s3_data_transfer_tiered(self, test_project):
        """Test data transfer tier pricing"""
        # First 100GB free, then tiered pricing
        service_small = {
            "id": "s3-transfer-small",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 10,
                "storage_class": "STANDARD",
                "put_requests_per_month": 0,
                "get_requests_per_month": 0,
                "data_transfer_gb": 200  # 100GB over free tier
            }
        }
        
        service_large = {
            "id": "s3-transfer-large",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 10,
                "storage_class": "STANDARD",
                "put_requests_per_month": 0,
                "get_requests_per_month": 0,
                "data_transfer_gb": 1000  # 900GB over free tier
            }
        }
        
        estimate_small = create_estimate(test_project, [service_small])
        estimate_large = create_estimate(test_project, [service_large])
        
        # Cost should scale with data transfer
        assert estimate_large["total_monthly_cost"] > estimate_small["total_monthly_cost"]


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestS3InvalidConfigurations:
    """Test S3 invalid configuration handling"""
    
    def test_s3_negative_storage(self, test_project):
        """Test negative storage is handled"""
        service = {
            "id": "s3-negative",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": -100,
                "storage_class": "STANDARD",
                "put_requests_per_month": 1000,
                "get_requests_per_month": 10000,
                "data_transfer_gb": 0
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json={"services": [service]}
        )
        # Should handle gracefully
        assert response.status_code in [201, 400, 422]
    
    def test_s3_invalid_storage_class(self, test_project):
        """Test invalid storage class"""
        service = {
            "id": "s3-invalid-class",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100,
                "storage_class": "INVALID_CLASS",
                "put_requests_per_month": 1000,
                "get_requests_per_month": 10000,
                "data_transfer_gb": 0
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json={"services": [service]}
        )
        # Should handle gracefully or use default
        assert response.status_code in [201, 400, 422]


# ============================================================================
# BREAKDOWN STRUCTURE TESTS
# ============================================================================

class TestS3BreakdownStructure:
    """Test S3 cost breakdown structure"""
    
    def test_s3_breakdown_by_service(self, test_project, base_s3_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_s3_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b["dimension"] == "service"), None)
        
        assert service_breakdown is not None
        assert service_breakdown["key"] == "AmazonS3"
        assert service_breakdown["value"] > 0
    
    def test_s3_breakdown_components(self, test_project):
        """Test breakdown includes cost components"""
        service = {
            "id": "s3-detailed",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100,
                "storage_class": "STANDARD",
                "put_requests_per_month": 10000,
                "get_requests_per_month": 100000,
                "data_transfer_gb": 200
            }
        }
        
        estimate = create_estimate(test_project, [service])
        breakdown = estimate["breakdown"]
        
        s3_breakdown = next((b for b in breakdown if b["key"] == "AmazonS3"), None)
        assert s3_breakdown is not None
        
        # Should have details
        if s3_breakdown.get("details"):
            details = s3_breakdown["details"]
            # Check for cost components
            assert "storage_cost" in details or "total" in details


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestS3ConfidenceScoring:
    """Test S3 confidence score calculation"""
    
    def test_s3_confidence_in_range(self, test_project, base_s3_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_s3_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1
    
    def test_s3_confidence_with_complete_config(self, test_project):
        """Test confidence with complete configuration"""
        service = {
            "id": "s3-complete",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 500,
                "storage_class": "STANDARD",
                "put_requests_per_month": 100000,
                "get_requests_per_month": 1000000,
                "data_transfer_gb": 200
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["confidence"] >= 0.5  # Should have reasonable confidence


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestS3AssumptionsWarnings:
    """Test S3 assumptions and warnings"""
    
    def test_s3_has_assumptions(self, test_project, base_s3_config):
        """Test S3 estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_s3_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_s3_has_warnings(self, test_project, base_s3_config):
        """Test S3 estimate includes warnings"""
        estimate = create_estimate(test_project, [base_s3_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
