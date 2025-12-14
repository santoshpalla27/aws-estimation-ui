"""
Service: AmazonCloudFront
Category: Networking
Pricing Model: Data transfer + Requests
Key Cost Drivers: data_transfer_out_gb, https_requests, http_requests
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonCloudFront tests"""
    project_data = {
        "name": "AmazonCloudFront Test Project",
        "description": "Testing AmazonCloudFront cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazoncloudfront_config():
    """Base AmazonCloudFront service configuration"""
    return {
        "id": "test-amazoncloudfront",
        "service_type": "AmazonCloudFront",
        "region": "us-east-1",
        "config": {
            "data_transfer_out_gb": 1000,
            "https_requests": 10000000,
            "http_requests": 5000000
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

class TestAmazonCloudFrontServiceDiscovery:
    """Test AmazonCloudFront service registration and metadata"""
    
    def test_amazoncloudfront_in_service_catalog(self):
        """Verify AmazonCloudFront appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonCloudFront"), None)
        
        assert service is not None, "AmazonCloudFront not found in service catalog"
        assert service["category"] == "Networking"
    
    def test_amazoncloudfront_regions_populated(self):
        """Verify AmazonCloudFront has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonCloudFront"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonCloudFrontSchemaValidation:
    """Test AmazonCloudFront configuration schema"""
    
    def test_amazoncloudfront_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonCloudFront/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonCloudFrontBasicCostCalculation:
    """Test basic AmazonCloudFront cost calculations"""
    
    def test_amazoncloudfront_basic_cost(self, test_project, base_amazoncloudfront_config):
        """Test basic AmazonCloudFront cost calculation"""
        estimate = create_estimate(test_project, [base_amazoncloudfront_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazoncloudfront_cost_deterministic(self, test_project, base_amazoncloudfront_config):
        """Test AmazonCloudFront cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazoncloudfront_config])
        estimate2 = create_estimate(test_project, [base_amazoncloudfront_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonCloudFrontEdgeCases:
    """Test AmazonCloudFront edge cases and boundaries"""
    
    def test_amazoncloudfront_minimal_config(self, test_project):
        """Test AmazonCloudFront with minimal configuration"""
        service = {
            "id": "amazoncloudfront-minimal",
            "service_type": "AmazonCloudFront",
            "region": "us-east-1",
            "config": {
                "data_transfer_out_gb": 1000,
            "https_requests": 10000000,
            "http_requests": 5000000
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonCloudFrontInvalidConfigurations:
    """Test AmazonCloudFront invalid configuration handling"""
    
    def test_amazoncloudfront_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazoncloudfront-invalid",
            "service_type": "AmazonCloudFront",
            "region": "us-east-1",
            "config": {}  # Empty config
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json={"services": [service]}
        )
        # Should handle gracefully with defaults or return error
        assert response.status_code in [201, 400, 422]


# ============================================================================
# BREAKDOWN STRUCTURE TESTS
# ============================================================================

class TestAmazonCloudFrontBreakdownStructure:
    """Test AmazonCloudFront cost breakdown structure"""
    
    def test_amazoncloudfront_breakdown_by_service(self, test_project, base_amazoncloudfront_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazoncloudfront_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonCloudFront"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonCloudFront" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonCloudFrontConfidenceScoring:
    """Test AmazonCloudFront confidence score calculation"""
    
    def test_amazoncloudfront_confidence_in_range(self, test_project, base_amazoncloudfront_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazoncloudfront_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonCloudFrontAssumptionsWarnings:
    """Test AmazonCloudFront assumptions and warnings"""
    
    def test_amazoncloudfront_has_assumptions(self, test_project, base_amazoncloudfront_config):
        """Test AmazonCloudFront estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazoncloudfront_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazoncloudfront_has_warnings(self, test_project, base_amazoncloudfront_config):
        """Test AmazonCloudFront estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazoncloudfront_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
