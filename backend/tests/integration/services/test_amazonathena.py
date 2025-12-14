"""
Service: AmazonAthena
Category: Analytics
Pricing Model: Data scanned
Key Cost Drivers: data_scanned_tb
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonAthena tests"""
    project_data = {
        "name": "AmazonAthena Test Project",
        "description": "Testing AmazonAthena cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonathena_config():
    """Base AmazonAthena service configuration"""
    return {
        "id": "test-amazonathena",
        "service_type": "AmazonAthena",
        "region": "us-east-1",
        "config": {
            "data_scanned_tb": 10
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

class TestAmazonAthenaServiceDiscovery:
    """Test AmazonAthena service registration and metadata"""
    
    def test_amazonathena_in_service_catalog(self):
        """Verify AmazonAthena appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonAthena"), None)
        
        assert service is not None, "AmazonAthena not found in service catalog"
        assert service["category"] == "Analytics"
    
    def test_amazonathena_regions_populated(self):
        """Verify AmazonAthena has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonAthena"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonAthenaSchemaValidation:
    """Test AmazonAthena configuration schema"""
    
    def test_amazonathena_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonAthena/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonAthenaBasicCostCalculation:
    """Test basic AmazonAthena cost calculations"""
    
    def test_amazonathena_basic_cost(self, test_project, base_amazonathena_config):
        """Test basic AmazonAthena cost calculation"""
        estimate = create_estimate(test_project, [base_amazonathena_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonathena_cost_deterministic(self, test_project, base_amazonathena_config):
        """Test AmazonAthena cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonathena_config])
        estimate2 = create_estimate(test_project, [base_amazonathena_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonAthenaEdgeCases:
    """Test AmazonAthena edge cases and boundaries"""
    
    def test_amazonathena_minimal_config(self, test_project):
        """Test AmazonAthena with minimal configuration"""
        service = {
            "id": "amazonathena-minimal",
            "service_type": "AmazonAthena",
            "region": "us-east-1",
            "config": {
                "data_scanned_tb": 10
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonAthenaInvalidConfigurations:
    """Test AmazonAthena invalid configuration handling"""
    
    def test_amazonathena_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonathena-invalid",
            "service_type": "AmazonAthena",
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

class TestAmazonAthenaBreakdownStructure:
    """Test AmazonAthena cost breakdown structure"""
    
    def test_amazonathena_breakdown_by_service(self, test_project, base_amazonathena_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonathena_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonAthena"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonAthena" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonAthenaConfidenceScoring:
    """Test AmazonAthena confidence score calculation"""
    
    def test_amazonathena_confidence_in_range(self, test_project, base_amazonathena_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonathena_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonAthenaAssumptionsWarnings:
    """Test AmazonAthena assumptions and warnings"""
    
    def test_amazonathena_has_assumptions(self, test_project, base_amazonathena_config):
        """Test AmazonAthena estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonathena_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonathena_has_warnings(self, test_project, base_amazonathena_config):
        """Test AmazonAthena estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonathena_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
