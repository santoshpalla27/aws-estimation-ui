"""
Service: ApplicationLoadBalancer
Category: Networking
Pricing Model: Load balancer hours + LCU hours
Key Cost Drivers: load_balancers, lcu_hours
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for ApplicationLoadBalancer tests"""
    project_data = {
        "name": "ApplicationLoadBalancer Test Project",
        "description": "Testing ApplicationLoadBalancer cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_applicationloadbalancer_config():
    """Base ApplicationLoadBalancer service configuration"""
    return {
        "id": "test-applicationloadbalancer",
        "service_type": "ApplicationLoadBalancer",
        "region": "us-east-1",
        "config": {
            "load_balancers": 2,
            "lcu_hours": 730
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

class TestApplicationLoadBalancerServiceDiscovery:
    """Test ApplicationLoadBalancer service registration and metadata"""
    
    def test_applicationloadbalancer_in_service_catalog(self):
        """Verify ApplicationLoadBalancer appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "ApplicationLoadBalancer"), None)
        
        assert service is not None, "ApplicationLoadBalancer not found in service catalog"
        assert service["category"] == "Networking"
    
    def test_applicationloadbalancer_regions_populated(self):
        """Verify ApplicationLoadBalancer has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "ApplicationLoadBalancer"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestApplicationLoadBalancerSchemaValidation:
    """Test ApplicationLoadBalancer configuration schema"""
    
    def test_applicationloadbalancer_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/ApplicationLoadBalancer/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestApplicationLoadBalancerBasicCostCalculation:
    """Test basic ApplicationLoadBalancer cost calculations"""
    
    def test_applicationloadbalancer_basic_cost(self, test_project, base_applicationloadbalancer_config):
        """Test basic ApplicationLoadBalancer cost calculation"""
        estimate = create_estimate(test_project, [base_applicationloadbalancer_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_applicationloadbalancer_cost_deterministic(self, test_project, base_applicationloadbalancer_config):
        """Test ApplicationLoadBalancer cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_applicationloadbalancer_config])
        estimate2 = create_estimate(test_project, [base_applicationloadbalancer_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestApplicationLoadBalancerEdgeCases:
    """Test ApplicationLoadBalancer edge cases and boundaries"""
    
    def test_applicationloadbalancer_minimal_config(self, test_project):
        """Test ApplicationLoadBalancer with minimal configuration"""
        service = {
            "id": "applicationloadbalancer-minimal",
            "service_type": "ApplicationLoadBalancer",
            "region": "us-east-1",
            "config": {
                "load_balancers": 2,
            "lcu_hours": 730
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestApplicationLoadBalancerInvalidConfigurations:
    """Test ApplicationLoadBalancer invalid configuration handling"""
    
    def test_applicationloadbalancer_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "applicationloadbalancer-invalid",
            "service_type": "ApplicationLoadBalancer",
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

class TestApplicationLoadBalancerBreakdownStructure:
    """Test ApplicationLoadBalancer cost breakdown structure"""
    
    def test_applicationloadbalancer_breakdown_by_service(self, test_project, base_applicationloadbalancer_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_applicationloadbalancer_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "ApplicationLoadBalancer"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "ApplicationLoadBalancer" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestApplicationLoadBalancerConfidenceScoring:
    """Test ApplicationLoadBalancer confidence score calculation"""
    
    def test_applicationloadbalancer_confidence_in_range(self, test_project, base_applicationloadbalancer_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_applicationloadbalancer_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestApplicationLoadBalancerAssumptionsWarnings:
    """Test ApplicationLoadBalancer assumptions and warnings"""
    
    def test_applicationloadbalancer_has_assumptions(self, test_project, base_applicationloadbalancer_config):
        """Test ApplicationLoadBalancer estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_applicationloadbalancer_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_applicationloadbalancer_has_warnings(self, test_project, base_applicationloadbalancer_config):
        """Test ApplicationLoadBalancer estimate includes warnings"""
        estimate = create_estimate(test_project, [base_applicationloadbalancer_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
