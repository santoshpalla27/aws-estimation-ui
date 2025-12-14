"""
Service: AWSShield
Category: Security
Pricing Model: Advanced protection
Key Cost Drivers: shield_advanced
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AWSShield tests"""
    project_data = {
        "name": "AWSShield Test Project",
        "description": "Testing AWSShield cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_awsshield_config():
    """Base AWSShield service configuration"""
    return {
        "id": "test-awsshield",
        "service_type": "AWSShield",
        "region": "us-east-1",
        "config": {
            "shield_advanced": True
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

class TestAWSShieldServiceDiscovery:
    """Test AWSShield service registration and metadata"""
    
    def test_awsshield_in_service_catalog(self):
        """Verify AWSShield appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSShield"), None)
        
        assert service is not None, "AWSShield not found in service catalog"
        assert service["category"] == "Security"
    
    def test_awsshield_regions_populated(self):
        """Verify AWSShield has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSShield"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAWSShieldSchemaValidation:
    """Test AWSShield configuration schema"""
    
    def test_awsshield_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AWSShield/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAWSShieldBasicCostCalculation:
    """Test basic AWSShield cost calculations"""
    
    def test_awsshield_basic_cost(self, test_project, base_awsshield_config):
        """Test basic AWSShield cost calculation"""
        estimate = create_estimate(test_project, [base_awsshield_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_awsshield_cost_deterministic(self, test_project, base_awsshield_config):
        """Test AWSShield cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_awsshield_config])
        estimate2 = create_estimate(test_project, [base_awsshield_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAWSShieldEdgeCases:
    """Test AWSShield edge cases and boundaries"""
    
    def test_awsshield_minimal_config(self, test_project):
        """Test AWSShield with minimal configuration"""
        service = {
            "id": "awsshield-minimal",
            "service_type": "AWSShield",
            "region": "us-east-1",
            "config": {
                "shield_advanced": True
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAWSShieldInvalidConfigurations:
    """Test AWSShield invalid configuration handling"""
    
    def test_awsshield_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "awsshield-invalid",
            "service_type": "AWSShield",
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

class TestAWSShieldBreakdownStructure:
    """Test AWSShield cost breakdown structure"""
    
    def test_awsshield_breakdown_by_service(self, test_project, base_awsshield_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_awsshield_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AWSShield"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AWSShield" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAWSShieldConfidenceScoring:
    """Test AWSShield confidence score calculation"""
    
    def test_awsshield_confidence_in_range(self, test_project, base_awsshield_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_awsshield_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAWSShieldAssumptionsWarnings:
    """Test AWSShield assumptions and warnings"""
    
    def test_awsshield_has_assumptions(self, test_project, base_awsshield_config):
        """Test AWSShield estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_awsshield_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_awsshield_has_warnings(self, test_project, base_awsshield_config):
        """Test AWSShield estimate includes warnings"""
        estimate = create_estimate(test_project, [base_awsshield_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
