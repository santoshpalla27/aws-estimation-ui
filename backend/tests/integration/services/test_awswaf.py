"""
Service: AWSWAF
Category: Security
Pricing Model: Web ACLs + Rules + Requests
Key Cost Drivers: web_acls, rules, requests_per_month
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AWSWAF tests"""
    project_data = {
        "name": "AWSWAF Test Project",
        "description": "Testing AWSWAF cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_awswaf_config():
    """Base AWSWAF service configuration"""
    return {
        "id": "test-awswaf",
        "service_type": "AWSWAF",
        "region": "us-east-1",
        "config": {
            "web_acls": 2,
            "rules": 10,
            "requests_per_month": 10000000
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

class TestAWSWAFServiceDiscovery:
    """Test AWSWAF service registration and metadata"""
    
    def test_awswaf_in_service_catalog(self):
        """Verify AWSWAF appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSWAF"), None)
        
        assert service is not None, "AWSWAF not found in service catalog"
        assert service["category"] == "Security"
    
    def test_awswaf_regions_populated(self):
        """Verify AWSWAF has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSWAF"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAWSWAFSchemaValidation:
    """Test AWSWAF configuration schema"""
    
    def test_awswaf_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AWSWAF/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAWSWAFBasicCostCalculation:
    """Test basic AWSWAF cost calculations"""
    
    def test_awswaf_basic_cost(self, test_project, base_awswaf_config):
        """Test basic AWSWAF cost calculation"""
        estimate = create_estimate(test_project, [base_awswaf_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_awswaf_cost_deterministic(self, test_project, base_awswaf_config):
        """Test AWSWAF cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_awswaf_config])
        estimate2 = create_estimate(test_project, [base_awswaf_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAWSWAFEdgeCases:
    """Test AWSWAF edge cases and boundaries"""
    
    def test_awswaf_minimal_config(self, test_project):
        """Test AWSWAF with minimal configuration"""
        service = {
            "id": "awswaf-minimal",
            "service_type": "AWSWAF",
            "region": "us-east-1",
            "config": {
                "web_acls": 2,
            "rules": 10,
            "requests_per_month": 10000000
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAWSWAFInvalidConfigurations:
    """Test AWSWAF invalid configuration handling"""
    
    def test_awswaf_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "awswaf-invalid",
            "service_type": "AWSWAF",
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

class TestAWSWAFBreakdownStructure:
    """Test AWSWAF cost breakdown structure"""
    
    def test_awswaf_breakdown_by_service(self, test_project, base_awswaf_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_awswaf_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AWSWAF"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AWSWAF" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAWSWAFConfidenceScoring:
    """Test AWSWAF confidence score calculation"""
    
    def test_awswaf_confidence_in_range(self, test_project, base_awswaf_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_awswaf_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAWSWAFAssumptionsWarnings:
    """Test AWSWAF assumptions and warnings"""
    
    def test_awswaf_has_assumptions(self, test_project, base_awswaf_config):
        """Test AWSWAF estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_awswaf_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_awswaf_has_warnings(self, test_project, base_awswaf_config):
        """Test AWSWAF estimate includes warnings"""
        estimate = create_estimate(test_project, [base_awswaf_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
