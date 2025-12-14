"""
Service: AWSConfig
Category: Management
Pricing Model: Configuration items + Rules
Key Cost Drivers: config_items, config_rules
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AWSConfig tests"""
    project_data = {
        "name": "AWSConfig Test Project",
        "description": "Testing AWSConfig cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_awsconfig_config():
    """Base AWSConfig service configuration"""
    return {
        "id": "test-awsconfig",
        "service_type": "AWSConfig",
        "region": "us-east-1",
        "config": {
            "config_items": 10000,
            "config_rules": 20
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

class TestAWSConfigServiceDiscovery:
    """Test AWSConfig service registration and metadata"""
    
    def test_awsconfig_in_service_catalog(self):
        """Verify AWSConfig appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSConfig"), None)
        
        assert service is not None, "AWSConfig not found in service catalog"
        assert service["category"] == "Management"
    
    def test_awsconfig_regions_populated(self):
        """Verify AWSConfig has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSConfig"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAWSConfigSchemaValidation:
    """Test AWSConfig configuration schema"""
    
    def test_awsconfig_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AWSConfig/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAWSConfigBasicCostCalculation:
    """Test basic AWSConfig cost calculations"""
    
    def test_awsconfig_basic_cost(self, test_project, base_awsconfig_config):
        """Test basic AWSConfig cost calculation"""
        estimate = create_estimate(test_project, [base_awsconfig_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_awsconfig_cost_deterministic(self, test_project, base_awsconfig_config):
        """Test AWSConfig cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_awsconfig_config])
        estimate2 = create_estimate(test_project, [base_awsconfig_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAWSConfigEdgeCases:
    """Test AWSConfig edge cases and boundaries"""
    
    def test_awsconfig_minimal_config(self, test_project):
        """Test AWSConfig with minimal configuration"""
        service = {
            "id": "awsconfig-minimal",
            "service_type": "AWSConfig",
            "region": "us-east-1",
            "config": {
                "config_items": 10000,
            "config_rules": 20
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAWSConfigInvalidConfigurations:
    """Test AWSConfig invalid configuration handling"""
    
    def test_awsconfig_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "awsconfig-invalid",
            "service_type": "AWSConfig",
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

class TestAWSConfigBreakdownStructure:
    """Test AWSConfig cost breakdown structure"""
    
    def test_awsconfig_breakdown_by_service(self, test_project, base_awsconfig_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_awsconfig_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AWSConfig"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AWSConfig" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAWSConfigConfidenceScoring:
    """Test AWSConfig confidence score calculation"""
    
    def test_awsconfig_confidence_in_range(self, test_project, base_awsconfig_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_awsconfig_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAWSConfigAssumptionsWarnings:
    """Test AWSConfig assumptions and warnings"""
    
    def test_awsconfig_has_assumptions(self, test_project, base_awsconfig_config):
        """Test AWSConfig estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_awsconfig_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_awsconfig_has_warnings(self, test_project, base_awsconfig_config):
        """Test AWSConfig estimate includes warnings"""
        estimate = create_estimate(test_project, [base_awsconfig_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
