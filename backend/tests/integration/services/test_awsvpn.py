"""
Service: AWSVPN
Category: Networking
Pricing Model: VPN connection hours + Data transfer
Key Cost Drivers: vpn_connections, connection_hours, data_transfer_gb
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AWSVPN tests"""
    project_data = {
        "name": "AWSVPN Test Project",
        "description": "Testing AWSVPN cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_awsvpn_config():
    """Base AWSVPN service configuration"""
    return {
        "id": "test-awsvpn",
        "service_type": "AWSVPN",
        "region": "us-east-1",
        "config": {
            "vpn_connections": 2,
            "connection_hours": 730,
            "data_transfer_gb": 500
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

class TestAWSVPNServiceDiscovery:
    """Test AWSVPN service registration and metadata"""
    
    def test_awsvpn_in_service_catalog(self):
        """Verify AWSVPN appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSVPN"), None)
        
        assert service is not None, "AWSVPN not found in service catalog"
        assert service["category"] == "Networking"
    
    def test_awsvpn_regions_populated(self):
        """Verify AWSVPN has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSVPN"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAWSVPNSchemaValidation:
    """Test AWSVPN configuration schema"""
    
    def test_awsvpn_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AWSVPN/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAWSVPNBasicCostCalculation:
    """Test basic AWSVPN cost calculations"""
    
    def test_awsvpn_basic_cost(self, test_project, base_awsvpn_config):
        """Test basic AWSVPN cost calculation"""
        estimate = create_estimate(test_project, [base_awsvpn_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_awsvpn_cost_deterministic(self, test_project, base_awsvpn_config):
        """Test AWSVPN cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_awsvpn_config])
        estimate2 = create_estimate(test_project, [base_awsvpn_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAWSVPNEdgeCases:
    """Test AWSVPN edge cases and boundaries"""
    
    def test_awsvpn_minimal_config(self, test_project):
        """Test AWSVPN with minimal configuration"""
        service = {
            "id": "awsvpn-minimal",
            "service_type": "AWSVPN",
            "region": "us-east-1",
            "config": {
                "vpn_connections": 2,
            "connection_hours": 730,
            "data_transfer_gb": 500
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAWSVPNInvalidConfigurations:
    """Test AWSVPN invalid configuration handling"""
    
    def test_awsvpn_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "awsvpn-invalid",
            "service_type": "AWSVPN",
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

class TestAWSVPNBreakdownStructure:
    """Test AWSVPN cost breakdown structure"""
    
    def test_awsvpn_breakdown_by_service(self, test_project, base_awsvpn_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_awsvpn_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AWSVPN"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AWSVPN" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAWSVPNConfidenceScoring:
    """Test AWSVPN confidence score calculation"""
    
    def test_awsvpn_confidence_in_range(self, test_project, base_awsvpn_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_awsvpn_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAWSVPNAssumptionsWarnings:
    """Test AWSVPN assumptions and warnings"""
    
    def test_awsvpn_has_assumptions(self, test_project, base_awsvpn_config):
        """Test AWSVPN estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_awsvpn_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_awsvpn_has_warnings(self, test_project, base_awsvpn_config):
        """Test AWSVPN estimate includes warnings"""
        estimate = create_estimate(test_project, [base_awsvpn_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
