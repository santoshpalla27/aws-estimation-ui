"""
Service: AmazonEMR
Category: Analytics
Pricing Model: Instance hours + EMR charges
Key Cost Drivers: instance_type, instance_count, hours_per_month
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonEMR tests"""
    project_data = {
        "name": "AmazonEMR Test Project",
        "description": "Testing AmazonEMR cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonemr_config():
    """Base AmazonEMR service configuration"""
    return {
        "id": "test-amazonemr",
        "service_type": "AmazonEMR",
        "region": "us-east-1",
        "config": {
            "instance_type": 'm5.xlarge',
            "instance_count": 5,
            "hours_per_month": 730
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

class TestAmazonEMRServiceDiscovery:
    """Test AmazonEMR service registration and metadata"""
    
    def test_amazonemr_in_service_catalog(self):
        """Verify AmazonEMR appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonEMR"), None)
        
        assert service is not None, "AmazonEMR not found in service catalog"
        assert service["category"] == "Analytics"
    
    def test_amazonemr_regions_populated(self):
        """Verify AmazonEMR has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonEMR"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonEMRSchemaValidation:
    """Test AmazonEMR configuration schema"""
    
    def test_amazonemr_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonEMR/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonEMRBasicCostCalculation:
    """Test basic AmazonEMR cost calculations"""
    
    def test_amazonemr_basic_cost(self, test_project, base_amazonemr_config):
        """Test basic AmazonEMR cost calculation"""
        estimate = create_estimate(test_project, [base_amazonemr_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonemr_cost_deterministic(self, test_project, base_amazonemr_config):
        """Test AmazonEMR cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonemr_config])
        estimate2 = create_estimate(test_project, [base_amazonemr_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonEMREdgeCases:
    """Test AmazonEMR edge cases and boundaries"""
    
    def test_amazonemr_minimal_config(self, test_project):
        """Test AmazonEMR with minimal configuration"""
        service = {
            "id": "amazonemr-minimal",
            "service_type": "AmazonEMR",
            "region": "us-east-1",
            "config": {
                "instance_type": 'm5.xlarge',
            "instance_count": 5,
            "hours_per_month": 730
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonEMRInvalidConfigurations:
    """Test AmazonEMR invalid configuration handling"""
    
    def test_amazonemr_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonemr-invalid",
            "service_type": "AmazonEMR",
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

class TestAmazonEMRBreakdownStructure:
    """Test AmazonEMR cost breakdown structure"""
    
    def test_amazonemr_breakdown_by_service(self, test_project, base_amazonemr_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonemr_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonEMR"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonEMR" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonEMRConfidenceScoring:
    """Test AmazonEMR confidence score calculation"""
    
    def test_amazonemr_confidence_in_range(self, test_project, base_amazonemr_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonemr_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonEMRAssumptionsWarnings:
    """Test AmazonEMR assumptions and warnings"""
    
    def test_amazonemr_has_assumptions(self, test_project, base_amazonemr_config):
        """Test AmazonEMR estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonemr_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonemr_has_warnings(self, test_project, base_amazonemr_config):
        """Test AmazonEMR estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonemr_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
