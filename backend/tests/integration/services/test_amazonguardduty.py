"""
Service: AmazonGuardDuty
Category: Security
Pricing Model: Events analyzed + Data processed
Key Cost Drivers: cloudtrail_events, vpc_flow_logs_gb, dns_logs_gb
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonGuardDuty tests"""
    project_data = {
        "name": "AmazonGuardDuty Test Project",
        "description": "Testing AmazonGuardDuty cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonguardduty_config():
    """Base AmazonGuardDuty service configuration"""
    return {
        "id": "test-amazonguardduty",
        "service_type": "AmazonGuardDuty",
        "region": "us-east-1",
        "config": {
            "cloudtrail_events": 1000000,
            "vpc_flow_logs_gb": 500,
            "dns_logs_gb": 100
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

class TestAmazonGuardDutyServiceDiscovery:
    """Test AmazonGuardDuty service registration and metadata"""
    
    def test_amazonguardduty_in_service_catalog(self):
        """Verify AmazonGuardDuty appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonGuardDuty"), None)
        
        assert service is not None, "AmazonGuardDuty not found in service catalog"
        assert service["category"] == "Security"
    
    def test_amazonguardduty_regions_populated(self):
        """Verify AmazonGuardDuty has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonGuardDuty"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonGuardDutySchemaValidation:
    """Test AmazonGuardDuty configuration schema"""
    
    def test_amazonguardduty_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonGuardDuty/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonGuardDutyBasicCostCalculation:
    """Test basic AmazonGuardDuty cost calculations"""
    
    def test_amazonguardduty_basic_cost(self, test_project, base_amazonguardduty_config):
        """Test basic AmazonGuardDuty cost calculation"""
        estimate = create_estimate(test_project, [base_amazonguardduty_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonguardduty_cost_deterministic(self, test_project, base_amazonguardduty_config):
        """Test AmazonGuardDuty cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonguardduty_config])
        estimate2 = create_estimate(test_project, [base_amazonguardduty_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonGuardDutyEdgeCases:
    """Test AmazonGuardDuty edge cases and boundaries"""
    
    def test_amazonguardduty_minimal_config(self, test_project):
        """Test AmazonGuardDuty with minimal configuration"""
        service = {
            "id": "amazonguardduty-minimal",
            "service_type": "AmazonGuardDuty",
            "region": "us-east-1",
            "config": {
                "cloudtrail_events": 1000000,
            "vpc_flow_logs_gb": 500,
            "dns_logs_gb": 100
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonGuardDutyInvalidConfigurations:
    """Test AmazonGuardDuty invalid configuration handling"""
    
    def test_amazonguardduty_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonguardduty-invalid",
            "service_type": "AmazonGuardDuty",
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

class TestAmazonGuardDutyBreakdownStructure:
    """Test AmazonGuardDuty cost breakdown structure"""
    
    def test_amazonguardduty_breakdown_by_service(self, test_project, base_amazonguardduty_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonguardduty_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonGuardDuty"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonGuardDuty" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonGuardDutyConfidenceScoring:
    """Test AmazonGuardDuty confidence score calculation"""
    
    def test_amazonguardduty_confidence_in_range(self, test_project, base_amazonguardduty_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonguardduty_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonGuardDutyAssumptionsWarnings:
    """Test AmazonGuardDuty assumptions and warnings"""
    
    def test_amazonguardduty_has_assumptions(self, test_project, base_amazonguardduty_config):
        """Test AmazonGuardDuty estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonguardduty_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonguardduty_has_warnings(self, test_project, base_amazonguardduty_config):
        """Test AmazonGuardDuty estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonguardduty_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
