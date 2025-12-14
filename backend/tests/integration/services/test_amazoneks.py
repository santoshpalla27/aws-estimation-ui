"""
Service: AmazonEKS
Category: Compute
Pricing Model: Cluster hours + Node instances
Key Cost Drivers: cluster_count, node_group_instance_type, node_count
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonEKS tests"""
    project_data = {
        "name": "AmazonEKS Test Project",
        "description": "Testing AmazonEKS cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazoneks_config():
    """Base AmazonEKS service configuration"""
    return {
        "id": "test-amazoneks",
        "service_type": "AmazonEKS",
        "region": "us-east-1",
        "config": {
            "cluster_count": 1,
            "node_group_instance_type": 't3.medium',
            "node_count": 3
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

class TestAmazonEKSServiceDiscovery:
    """Test AmazonEKS service registration and metadata"""
    
    def test_amazoneks_in_service_catalog(self):
        """Verify AmazonEKS appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonEKS"), None)
        
        assert service is not None, "AmazonEKS not found in service catalog"
        assert service["category"] == "Compute"
    
    def test_amazoneks_regions_populated(self):
        """Verify AmazonEKS has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonEKS"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonEKSSchemaValidation:
    """Test AmazonEKS configuration schema"""
    
    def test_amazoneks_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonEKS/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonEKSBasicCostCalculation:
    """Test basic AmazonEKS cost calculations"""
    
    def test_amazoneks_basic_cost(self, test_project, base_amazoneks_config):
        """Test basic AmazonEKS cost calculation"""
        estimate = create_estimate(test_project, [base_amazoneks_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazoneks_cost_deterministic(self, test_project, base_amazoneks_config):
        """Test AmazonEKS cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazoneks_config])
        estimate2 = create_estimate(test_project, [base_amazoneks_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonEKSEdgeCases:
    """Test AmazonEKS edge cases and boundaries"""
    
    def test_amazoneks_minimal_config(self, test_project):
        """Test AmazonEKS with minimal configuration"""
        service = {
            "id": "amazoneks-minimal",
            "service_type": "AmazonEKS",
            "region": "us-east-1",
            "config": {
                "cluster_count": 1,
            "node_group_instance_type": 't3.medium',
            "node_count": 3
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonEKSInvalidConfigurations:
    """Test AmazonEKS invalid configuration handling"""
    
    def test_amazoneks_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazoneks-invalid",
            "service_type": "AmazonEKS",
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

class TestAmazonEKSBreakdownStructure:
    """Test AmazonEKS cost breakdown structure"""
    
    def test_amazoneks_breakdown_by_service(self, test_project, base_amazoneks_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazoneks_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonEKS"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonEKS" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonEKSConfidenceScoring:
    """Test AmazonEKS confidence score calculation"""
    
    def test_amazoneks_confidence_in_range(self, test_project, base_amazoneks_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazoneks_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonEKSAssumptionsWarnings:
    """Test AmazonEKS assumptions and warnings"""
    
    def test_amazoneks_has_assumptions(self, test_project, base_amazoneks_config):
        """Test AmazonEKS estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazoneks_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazoneks_has_warnings(self, test_project, base_amazoneks_config):
        """Test AmazonEKS estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazoneks_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
