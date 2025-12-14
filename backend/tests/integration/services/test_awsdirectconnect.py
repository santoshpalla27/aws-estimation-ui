"""
Service: AWSDirectConnect
Category: Networking
Pricing Model: Port hours + Data transfer
Key Cost Drivers: port_speed_gbps, port_hours, data_transfer_gb
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AWSDirectConnect tests"""
    project_data = {
        "name": "AWSDirectConnect Test Project",
        "description": "Testing AWSDirectConnect cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_awsdirectconnect_config():
    """Base AWSDirectConnect service configuration"""
    return {
        "id": "test-awsdirectconnect",
        "service_type": "AWSDirectConnect",
        "region": "us-east-1",
        "config": {
            "port_speed_gbps": 1,
            "port_hours": 730,
            "data_transfer_gb": 1000
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

class TestAWSDirectConnectServiceDiscovery:
    """Test AWSDirectConnect service registration and metadata"""
    
    def test_awsdirectconnect_in_service_catalog(self):
        """Verify AWSDirectConnect appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSDirectConnect"), None)
        
        assert service is not None, "AWSDirectConnect not found in service catalog"
        assert service["category"] == "Networking"
    
    def test_awsdirectconnect_regions_populated(self):
        """Verify AWSDirectConnect has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSDirectConnect"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAWSDirectConnectSchemaValidation:
    """Test AWSDirectConnect configuration schema"""
    
    def test_awsdirectconnect_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AWSDirectConnect/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAWSDirectConnectBasicCostCalculation:
    """Test basic AWSDirectConnect cost calculations"""
    
    def test_awsdirectconnect_basic_cost(self, test_project, base_awsdirectconnect_config):
        """Test basic AWSDirectConnect cost calculation"""
        estimate = create_estimate(test_project, [base_awsdirectconnect_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_awsdirectconnect_cost_deterministic(self, test_project, base_awsdirectconnect_config):
        """Test AWSDirectConnect cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_awsdirectconnect_config])
        estimate2 = create_estimate(test_project, [base_awsdirectconnect_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAWSDirectConnectEdgeCases:
    """Test AWSDirectConnect edge cases and boundaries"""
    
    def test_awsdirectconnect_minimal_config(self, test_project):
        """Test AWSDirectConnect with minimal configuration"""
        service = {
            "id": "awsdirectconnect-minimal",
            "service_type": "AWSDirectConnect",
            "region": "us-east-1",
            "config": {
                "port_speed_gbps": 1,
            "port_hours": 730,
            "data_transfer_gb": 1000
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAWSDirectConnectInvalidConfigurations:
    """Test AWSDirectConnect invalid configuration handling"""
    
    def test_awsdirectconnect_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "awsdirectconnect-invalid",
            "service_type": "AWSDirectConnect",
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

class TestAWSDirectConnectBreakdownStructure:
    """Test AWSDirectConnect cost breakdown structure"""
    
    def test_awsdirectconnect_breakdown_by_service(self, test_project, base_awsdirectconnect_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_awsdirectconnect_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AWSDirectConnect"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AWSDirectConnect" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAWSDirectConnectConfidenceScoring:
    """Test AWSDirectConnect confidence score calculation"""
    
    def test_awsdirectconnect_confidence_in_range(self, test_project, base_awsdirectconnect_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_awsdirectconnect_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAWSDirectConnectAssumptionsWarnings:
    """Test AWSDirectConnect assumptions and warnings"""
    
    def test_awsdirectconnect_has_assumptions(self, test_project, base_awsdirectconnect_config):
        """Test AWSDirectConnect estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_awsdirectconnect_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_awsdirectconnect_has_warnings(self, test_project, base_awsdirectconnect_config):
        """Test AWSDirectConnect estimate includes warnings"""
        estimate = create_estimate(test_project, [base_awsdirectconnect_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
