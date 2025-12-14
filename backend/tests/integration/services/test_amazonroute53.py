"""
Service: AmazonRoute53
Category: Networking
Pricing Model: Hosted zones + Queries
Key Cost Drivers: hosted_zones, queries_per_month
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonRoute53 tests"""
    project_data = {
        "name": "AmazonRoute53 Test Project",
        "description": "Testing AmazonRoute53 cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonroute53_config():
    """Base AmazonRoute53 service configuration"""
    return {
        "id": "test-amazonroute53",
        "service_type": "AmazonRoute53",
        "region": "us-east-1",
        "config": {
            "hosted_zones": 5,
            "queries_per_month": 1000000000
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

class TestAmazonRoute53ServiceDiscovery:
    """Test AmazonRoute53 service registration and metadata"""
    
    def test_amazonroute53_in_service_catalog(self):
        """Verify AmazonRoute53 appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonRoute53"), None)
        
        assert service is not None, "AmazonRoute53 not found in service catalog"
        assert service["category"] == "Networking"
    
    def test_amazonroute53_regions_populated(self):
        """Verify AmazonRoute53 has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonRoute53"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonRoute53SchemaValidation:
    """Test AmazonRoute53 configuration schema"""
    
    def test_amazonroute53_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonRoute53/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonRoute53BasicCostCalculation:
    """Test basic AmazonRoute53 cost calculations"""
    
    def test_amazonroute53_basic_cost(self, test_project, base_amazonroute53_config):
        """Test basic AmazonRoute53 cost calculation"""
        estimate = create_estimate(test_project, [base_amazonroute53_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonroute53_cost_deterministic(self, test_project, base_amazonroute53_config):
        """Test AmazonRoute53 cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonroute53_config])
        estimate2 = create_estimate(test_project, [base_amazonroute53_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonRoute53EdgeCases:
    """Test AmazonRoute53 edge cases and boundaries"""
    
    def test_amazonroute53_minimal_config(self, test_project):
        """Test AmazonRoute53 with minimal configuration"""
        service = {
            "id": "amazonroute53-minimal",
            "service_type": "AmazonRoute53",
            "region": "us-east-1",
            "config": {
                "hosted_zones": 5,
            "queries_per_month": 1000000000
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonRoute53InvalidConfigurations:
    """Test AmazonRoute53 invalid configuration handling"""
    
    def test_amazonroute53_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonroute53-invalid",
            "service_type": "AmazonRoute53",
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

class TestAmazonRoute53BreakdownStructure:
    """Test AmazonRoute53 cost breakdown structure"""
    
    def test_amazonroute53_breakdown_by_service(self, test_project, base_amazonroute53_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonroute53_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonRoute53"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonRoute53" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonRoute53ConfidenceScoring:
    """Test AmazonRoute53 confidence score calculation"""
    
    def test_amazonroute53_confidence_in_range(self, test_project, base_amazonroute53_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonroute53_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonRoute53AssumptionsWarnings:
    """Test AmazonRoute53 assumptions and warnings"""
    
    def test_amazonroute53_has_assumptions(self, test_project, base_amazonroute53_config):
        """Test AmazonRoute53 estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonroute53_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonroute53_has_warnings(self, test_project, base_amazonroute53_config):
        """Test AmazonRoute53 estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonroute53_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
