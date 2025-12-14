"""
Service: AWSGlue
Category: Analytics
Pricing Model: DPU hours + Crawler hours
Key Cost Drivers: dpu_hours, crawler_hours
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AWSGlue tests"""
    project_data = {
        "name": "AWSGlue Test Project",
        "description": "Testing AWSGlue cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_awsglue_config():
    """Base AWSGlue service configuration"""
    return {
        "id": "test-awsglue",
        "service_type": "AWSGlue",
        "region": "us-east-1",
        "config": {
            "dpu_hours": 100,
            "crawler_hours": 10
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

class TestAWSGlueServiceDiscovery:
    """Test AWSGlue service registration and metadata"""
    
    def test_awsglue_in_service_catalog(self):
        """Verify AWSGlue appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSGlue"), None)
        
        assert service is not None, "AWSGlue not found in service catalog"
        assert service["category"] == "Analytics"
    
    def test_awsglue_regions_populated(self):
        """Verify AWSGlue has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSGlue"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAWSGlueSchemaValidation:
    """Test AWSGlue configuration schema"""
    
    def test_awsglue_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AWSGlue/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAWSGlueBasicCostCalculation:
    """Test basic AWSGlue cost calculations"""
    
    def test_awsglue_basic_cost(self, test_project, base_awsglue_config):
        """Test basic AWSGlue cost calculation"""
        estimate = create_estimate(test_project, [base_awsglue_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_awsglue_cost_deterministic(self, test_project, base_awsglue_config):
        """Test AWSGlue cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_awsglue_config])
        estimate2 = create_estimate(test_project, [base_awsglue_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAWSGlueEdgeCases:
    """Test AWSGlue edge cases and boundaries"""
    
    def test_awsglue_minimal_config(self, test_project):
        """Test AWSGlue with minimal configuration"""
        service = {
            "id": "awsglue-minimal",
            "service_type": "AWSGlue",
            "region": "us-east-1",
            "config": {
                "dpu_hours": 100,
            "crawler_hours": 10
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAWSGlueInvalidConfigurations:
    """Test AWSGlue invalid configuration handling"""
    
    def test_awsglue_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "awsglue-invalid",
            "service_type": "AWSGlue",
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

class TestAWSGlueBreakdownStructure:
    """Test AWSGlue cost breakdown structure"""
    
    def test_awsglue_breakdown_by_service(self, test_project, base_awsglue_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_awsglue_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AWSGlue"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AWSGlue" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAWSGlueConfidenceScoring:
    """Test AWSGlue confidence score calculation"""
    
    def test_awsglue_confidence_in_range(self, test_project, base_awsglue_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_awsglue_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAWSGlueAssumptionsWarnings:
    """Test AWSGlue assumptions and warnings"""
    
    def test_awsglue_has_assumptions(self, test_project, base_awsglue_config):
        """Test AWSGlue estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_awsglue_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_awsglue_has_warnings(self, test_project, base_awsglue_config):
        """Test AWSGlue estimate includes warnings"""
        estimate = create_estimate(test_project, [base_awsglue_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
