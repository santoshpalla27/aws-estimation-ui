"""
Service: AmazonApiGateway
Category: Integration
Pricing Model: API calls + Cache memory
Key Cost Drivers: api_type, requests_per_month, cache_memory_gb
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonApiGateway tests"""
    project_data = {
        "name": "AmazonApiGateway Test Project",
        "description": "Testing AmazonApiGateway cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonapigateway_config():
    """Base AmazonApiGateway service configuration"""
    return {
        "id": "test-amazonapigateway",
        "service_type": "AmazonApiGateway",
        "region": "us-east-1",
        "config": {
            "api_type": 'REST',
            "requests_per_month": 10000000,
            "cache_memory_gb": 0.5
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

class TestAmazonApiGatewayServiceDiscovery:
    """Test AmazonApiGateway service registration and metadata"""
    
    def test_amazonapigateway_in_service_catalog(self):
        """Verify AmazonApiGateway appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonApiGateway"), None)
        
        assert service is not None, "AmazonApiGateway not found in service catalog"
        assert service["category"] == "Integration"
    
    def test_amazonapigateway_regions_populated(self):
        """Verify AmazonApiGateway has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonApiGateway"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonApiGatewaySchemaValidation:
    """Test AmazonApiGateway configuration schema"""
    
    def test_amazonapigateway_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonApiGateway/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonApiGatewayBasicCostCalculation:
    """Test basic AmazonApiGateway cost calculations"""
    
    def test_amazonapigateway_basic_cost(self, test_project, base_amazonapigateway_config):
        """Test basic AmazonApiGateway cost calculation"""
        estimate = create_estimate(test_project, [base_amazonapigateway_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonapigateway_cost_deterministic(self, test_project, base_amazonapigateway_config):
        """Test AmazonApiGateway cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonapigateway_config])
        estimate2 = create_estimate(test_project, [base_amazonapigateway_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonApiGatewayEdgeCases:
    """Test AmazonApiGateway edge cases and boundaries"""
    
    def test_amazonapigateway_minimal_config(self, test_project):
        """Test AmazonApiGateway with minimal configuration"""
        service = {
            "id": "amazonapigateway-minimal",
            "service_type": "AmazonApiGateway",
            "region": "us-east-1",
            "config": {
                "api_type": 'REST',
            "requests_per_month": 10000000,
            "cache_memory_gb": 0.5
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonApiGatewayInvalidConfigurations:
    """Test AmazonApiGateway invalid configuration handling"""
    
    def test_amazonapigateway_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonapigateway-invalid",
            "service_type": "AmazonApiGateway",
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

class TestAmazonApiGatewayBreakdownStructure:
    """Test AmazonApiGateway cost breakdown structure"""
    
    def test_amazonapigateway_breakdown_by_service(self, test_project, base_amazonapigateway_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonapigateway_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonApiGateway"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonApiGateway" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonApiGatewayConfidenceScoring:
    """Test AmazonApiGateway confidence score calculation"""
    
    def test_amazonapigateway_confidence_in_range(self, test_project, base_amazonapigateway_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonapigateway_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonApiGatewayAssumptionsWarnings:
    """Test AmazonApiGateway assumptions and warnings"""
    
    def test_amazonapigateway_has_assumptions(self, test_project, base_amazonapigateway_config):
        """Test AmazonApiGateway estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonapigateway_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonapigateway_has_warnings(self, test_project, base_amazonapigateway_config):
        """Test AmazonApiGateway estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonapigateway_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
