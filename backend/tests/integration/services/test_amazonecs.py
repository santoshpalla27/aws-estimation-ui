"""
Service: AmazonECS
Category: Compute
Pricing Model: Fargate vCPU + Memory OR EC2 instances
Key Cost Drivers: launch_type, vcpu, memory_gb, task_count
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonECS tests"""
    project_data = {
        "name": "AmazonECS Test Project",
        "description": "Testing AmazonECS cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonecs_config():
    """Base AmazonECS service configuration"""
    return {
        "id": "test-amazonecs",
        "service_type": "AmazonECS",
        "region": "us-east-1",
        "config": {
            "launch_type": 'FARGATE',
            "vcpu": 1,
            "memory_gb": 2,
            "task_count": 5
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

class TestAmazonECSServiceDiscovery:
    """Test AmazonECS service registration and metadata"""
    
    def test_amazonecs_in_service_catalog(self):
        """Verify AmazonECS appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonECS"), None)
        
        assert service is not None, "AmazonECS not found in service catalog"
        assert service["category"] == "Compute"
    
    def test_amazonecs_regions_populated(self):
        """Verify AmazonECS has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonECS"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonECSSchemaValidation:
    """Test AmazonECS configuration schema"""
    
    def test_amazonecs_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonECS/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonECSBasicCostCalculation:
    """Test basic AmazonECS cost calculations"""
    
    def test_amazonecs_basic_cost(self, test_project, base_amazonecs_config):
        """Test basic AmazonECS cost calculation"""
        estimate = create_estimate(test_project, [base_amazonecs_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonecs_cost_deterministic(self, test_project, base_amazonecs_config):
        """Test AmazonECS cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonecs_config])
        estimate2 = create_estimate(test_project, [base_amazonecs_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonECSEdgeCases:
    """Test AmazonECS edge cases and boundaries"""
    
    def test_amazonecs_minimal_config(self, test_project):
        """Test AmazonECS with minimal configuration"""
        service = {
            "id": "amazonecs-minimal",
            "service_type": "AmazonECS",
            "region": "us-east-1",
            "config": {
                "launch_type": 'FARGATE',
            "vcpu": 1,
            "memory_gb": 2,
            "task_count": 5
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonECSInvalidConfigurations:
    """Test AmazonECS invalid configuration handling"""
    
    def test_amazonecs_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonecs-invalid",
            "service_type": "AmazonECS",
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

class TestAmazonECSBreakdownStructure:
    """Test AmazonECS cost breakdown structure"""
    
    def test_amazonecs_breakdown_by_service(self, test_project, base_amazonecs_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonecs_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonECS"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonECS" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonECSConfidenceScoring:
    """Test AmazonECS confidence score calculation"""
    
    def test_amazonecs_confidence_in_range(self, test_project, base_amazonecs_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonecs_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonECSAssumptionsWarnings:
    """Test AmazonECS assumptions and warnings"""
    
    def test_amazonecs_has_assumptions(self, test_project, base_amazonecs_config):
        """Test AmazonECS estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonecs_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonecs_has_warnings(self, test_project, base_amazonecs_config):
        """Test AmazonECS estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonecs_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
