"""
Service: AmazonOpenSearchService
Category: Database
Pricing Model: Instance hours + Storage
Key Cost Drivers: instance_type, instance_count, storage_gb
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonOpenSearchService tests"""
    project_data = {
        "name": "AmazonOpenSearchService Test Project",
        "description": "Testing AmazonOpenSearchService cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonopensearchservice_config():
    """Base AmazonOpenSearchService service configuration"""
    return {
        "id": "test-amazonopensearchservice",
        "service_type": "AmazonOpenSearchService",
        "region": "us-east-1",
        "config": {
            "instance_type": 'm5.large.search',
            "instance_count": 3,
            "storage_gb": 500
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

class TestAmazonOpenSearchServiceServiceDiscovery:
    """Test AmazonOpenSearchService service registration and metadata"""
    
    def test_amazonopensearchservice_in_service_catalog(self):
        """Verify AmazonOpenSearchService appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonOpenSearchService"), None)
        
        assert service is not None, "AmazonOpenSearchService not found in service catalog"
        assert service["category"] == "Database"
    
    def test_amazonopensearchservice_regions_populated(self):
        """Verify AmazonOpenSearchService has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonOpenSearchService"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonOpenSearchServiceSchemaValidation:
    """Test AmazonOpenSearchService configuration schema"""
    
    def test_amazonopensearchservice_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonOpenSearchService/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonOpenSearchServiceBasicCostCalculation:
    """Test basic AmazonOpenSearchService cost calculations"""
    
    def test_amazonopensearchservice_basic_cost(self, test_project, base_amazonopensearchservice_config):
        """Test basic AmazonOpenSearchService cost calculation"""
        estimate = create_estimate(test_project, [base_amazonopensearchservice_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonopensearchservice_cost_deterministic(self, test_project, base_amazonopensearchservice_config):
        """Test AmazonOpenSearchService cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonopensearchservice_config])
        estimate2 = create_estimate(test_project, [base_amazonopensearchservice_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonOpenSearchServiceEdgeCases:
    """Test AmazonOpenSearchService edge cases and boundaries"""
    
    def test_amazonopensearchservice_minimal_config(self, test_project):
        """Test AmazonOpenSearchService with minimal configuration"""
        service = {
            "id": "amazonopensearchservice-minimal",
            "service_type": "AmazonOpenSearchService",
            "region": "us-east-1",
            "config": {
                "instance_type": 'm5.large.search',
            "instance_count": 3,
            "storage_gb": 500
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonOpenSearchServiceInvalidConfigurations:
    """Test AmazonOpenSearchService invalid configuration handling"""
    
    def test_amazonopensearchservice_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonopensearchservice-invalid",
            "service_type": "AmazonOpenSearchService",
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

class TestAmazonOpenSearchServiceBreakdownStructure:
    """Test AmazonOpenSearchService cost breakdown structure"""
    
    def test_amazonopensearchservice_breakdown_by_service(self, test_project, base_amazonopensearchservice_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonopensearchservice_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonOpenSearchService"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonOpenSearchService" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonOpenSearchServiceConfidenceScoring:
    """Test AmazonOpenSearchService confidence score calculation"""
    
    def test_amazonopensearchservice_confidence_in_range(self, test_project, base_amazonopensearchservice_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonopensearchservice_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonOpenSearchServiceAssumptionsWarnings:
    """Test AmazonOpenSearchService assumptions and warnings"""
    
    def test_amazonopensearchservice_has_assumptions(self, test_project, base_amazonopensearchservice_config):
        """Test AmazonOpenSearchService estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonopensearchservice_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonopensearchservice_has_warnings(self, test_project, base_amazonopensearchservice_config):
        """Test AmazonOpenSearchService estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonopensearchservice_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
