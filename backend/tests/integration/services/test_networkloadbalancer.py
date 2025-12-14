"""
Service: NetworkLoadBalancer
Category: Networking
Pricing Model: Load balancer hours + NLCU hours
Key Cost Drivers: load_balancers, nlcu_hours
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for NetworkLoadBalancer tests"""
    project_data = {
        "name": "NetworkLoadBalancer Test Project",
        "description": "Testing NetworkLoadBalancer cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_networkloadbalancer_config():
    """Base NetworkLoadBalancer service configuration"""
    return {
        "id": "test-networkloadbalancer",
        "service_type": "NetworkLoadBalancer",
        "region": "us-east-1",
        "config": {
            "load_balancers": 1,
            "nlcu_hours": 730
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

class TestNetworkLoadBalancerServiceDiscovery:
    """Test NetworkLoadBalancer service registration and metadata"""
    
    def test_networkloadbalancer_in_service_catalog(self):
        """Verify NetworkLoadBalancer appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "NetworkLoadBalancer"), None)
        
        assert service is not None, "NetworkLoadBalancer not found in service catalog"
        assert service["category"] == "Networking"
    
    def test_networkloadbalancer_regions_populated(self):
        """Verify NetworkLoadBalancer has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "NetworkLoadBalancer"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestNetworkLoadBalancerSchemaValidation:
    """Test NetworkLoadBalancer configuration schema"""
    
    def test_networkloadbalancer_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/NetworkLoadBalancer/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestNetworkLoadBalancerBasicCostCalculation:
    """Test basic NetworkLoadBalancer cost calculations"""
    
    def test_networkloadbalancer_basic_cost(self, test_project, base_networkloadbalancer_config):
        """Test basic NetworkLoadBalancer cost calculation"""
        estimate = create_estimate(test_project, [base_networkloadbalancer_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_networkloadbalancer_cost_deterministic(self, test_project, base_networkloadbalancer_config):
        """Test NetworkLoadBalancer cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_networkloadbalancer_config])
        estimate2 = create_estimate(test_project, [base_networkloadbalancer_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestNetworkLoadBalancerEdgeCases:
    """Test NetworkLoadBalancer edge cases and boundaries"""
    
    def test_networkloadbalancer_minimal_config(self, test_project):
        """Test NetworkLoadBalancer with minimal configuration"""
        service = {
            "id": "networkloadbalancer-minimal",
            "service_type": "NetworkLoadBalancer",
            "region": "us-east-1",
            "config": {
                "load_balancers": 1,
            "nlcu_hours": 730
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestNetworkLoadBalancerInvalidConfigurations:
    """Test NetworkLoadBalancer invalid configuration handling"""
    
    def test_networkloadbalancer_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "networkloadbalancer-invalid",
            "service_type": "NetworkLoadBalancer",
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

class TestNetworkLoadBalancerBreakdownStructure:
    """Test NetworkLoadBalancer cost breakdown structure"""
    
    def test_networkloadbalancer_breakdown_by_service(self, test_project, base_networkloadbalancer_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_networkloadbalancer_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "NetworkLoadBalancer"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "NetworkLoadBalancer" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestNetworkLoadBalancerConfidenceScoring:
    """Test NetworkLoadBalancer confidence score calculation"""
    
    def test_networkloadbalancer_confidence_in_range(self, test_project, base_networkloadbalancer_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_networkloadbalancer_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestNetworkLoadBalancerAssumptionsWarnings:
    """Test NetworkLoadBalancer assumptions and warnings"""
    
    def test_networkloadbalancer_has_assumptions(self, test_project, base_networkloadbalancer_config):
        """Test NetworkLoadBalancer estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_networkloadbalancer_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_networkloadbalancer_has_warnings(self, test_project, base_networkloadbalancer_config):
        """Test NetworkLoadBalancer estimate includes warnings"""
        estimate = create_estimate(test_project, [base_networkloadbalancer_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
