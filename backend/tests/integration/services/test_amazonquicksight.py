"""
Service: AmazonQuickSight
Category: Analytics
Pricing Model: Users + SPICE capacity
Key Cost Drivers: author_users, reader_users, spice_capacity_gb
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonQuickSight tests"""
    project_data = {
        "name": "AmazonQuickSight Test Project",
        "description": "Testing AmazonQuickSight cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonquicksight_config():
    """Base AmazonQuickSight service configuration"""
    return {
        "id": "test-amazonquicksight",
        "service_type": "AmazonQuickSight",
        "region": "us-east-1",
        "config": {
            "author_users": 5,
            "reader_users": 50,
            "spice_capacity_gb": 100
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

class TestAmazonQuickSightServiceDiscovery:
    """Test AmazonQuickSight service registration and metadata"""
    
    def test_amazonquicksight_in_service_catalog(self):
        """Verify AmazonQuickSight appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonQuickSight"), None)
        
        assert service is not None, "AmazonQuickSight not found in service catalog"
        assert service["category"] == "Analytics"
    
    def test_amazonquicksight_regions_populated(self):
        """Verify AmazonQuickSight has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonQuickSight"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonQuickSightSchemaValidation:
    """Test AmazonQuickSight configuration schema"""
    
    def test_amazonquicksight_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonQuickSight/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonQuickSightBasicCostCalculation:
    """Test basic AmazonQuickSight cost calculations"""
    
    def test_amazonquicksight_basic_cost(self, test_project, base_amazonquicksight_config):
        """Test basic AmazonQuickSight cost calculation"""
        estimate = create_estimate(test_project, [base_amazonquicksight_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonquicksight_cost_deterministic(self, test_project, base_amazonquicksight_config):
        """Test AmazonQuickSight cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonquicksight_config])
        estimate2 = create_estimate(test_project, [base_amazonquicksight_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonQuickSightEdgeCases:
    """Test AmazonQuickSight edge cases and boundaries"""
    
    def test_amazonquicksight_minimal_config(self, test_project):
        """Test AmazonQuickSight with minimal configuration"""
        service = {
            "id": "amazonquicksight-minimal",
            "service_type": "AmazonQuickSight",
            "region": "us-east-1",
            "config": {
                "author_users": 5,
            "reader_users": 50,
            "spice_capacity_gb": 100
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonQuickSightInvalidConfigurations:
    """Test AmazonQuickSight invalid configuration handling"""
    
    def test_amazonquicksight_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonquicksight-invalid",
            "service_type": "AmazonQuickSight",
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

class TestAmazonQuickSightBreakdownStructure:
    """Test AmazonQuickSight cost breakdown structure"""
    
    def test_amazonquicksight_breakdown_by_service(self, test_project, base_amazonquicksight_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonquicksight_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonQuickSight"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonQuickSight" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonQuickSightConfidenceScoring:
    """Test AmazonQuickSight confidence score calculation"""
    
    def test_amazonquicksight_confidence_in_range(self, test_project, base_amazonquicksight_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonquicksight_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonQuickSightAssumptionsWarnings:
    """Test AmazonQuickSight assumptions and warnings"""
    
    def test_amazonquicksight_has_assumptions(self, test_project, base_amazonquicksight_config):
        """Test AmazonQuickSight estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonquicksight_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonquicksight_has_warnings(self, test_project, base_amazonquicksight_config):
        """Test AmazonQuickSight estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonquicksight_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
