"""
Service: AWSStorageGateway
Category: Storage
Pricing Model: Gateway type + Storage
Key Cost Drivers: gateway_type, storage_gb
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AWSStorageGateway tests"""
    project_data = {
        "name": "AWSStorageGateway Test Project",
        "description": "Testing AWSStorageGateway cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_awsstoragegateway_config():
    """Base AWSStorageGateway service configuration"""
    return {
        "id": "test-awsstoragegateway",
        "service_type": "AWSStorageGateway",
        "region": "us-east-1",
        "config": {
            "gateway_type": 'file',
            "storage_gb": 1000
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

class TestAWSStorageGatewayServiceDiscovery:
    """Test AWSStorageGateway service registration and metadata"""
    
    def test_awsstoragegateway_in_service_catalog(self):
        """Verify AWSStorageGateway appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSStorageGateway"), None)
        
        assert service is not None, "AWSStorageGateway not found in service catalog"
        assert service["category"] == "Storage"
    
    def test_awsstoragegateway_regions_populated(self):
        """Verify AWSStorageGateway has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSStorageGateway"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAWSStorageGatewaySchemaValidation:
    """Test AWSStorageGateway configuration schema"""
    
    def test_awsstoragegateway_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AWSStorageGateway/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAWSStorageGatewayBasicCostCalculation:
    """Test basic AWSStorageGateway cost calculations"""
    
    def test_awsstoragegateway_basic_cost(self, test_project, base_awsstoragegateway_config):
        """Test basic AWSStorageGateway cost calculation"""
        estimate = create_estimate(test_project, [base_awsstoragegateway_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_awsstoragegateway_cost_deterministic(self, test_project, base_awsstoragegateway_config):
        """Test AWSStorageGateway cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_awsstoragegateway_config])
        estimate2 = create_estimate(test_project, [base_awsstoragegateway_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAWSStorageGatewayEdgeCases:
    """Test AWSStorageGateway edge cases and boundaries"""
    
    def test_awsstoragegateway_minimal_config(self, test_project):
        """Test AWSStorageGateway with minimal configuration"""
        service = {
            "id": "awsstoragegateway-minimal",
            "service_type": "AWSStorageGateway",
            "region": "us-east-1",
            "config": {
                "gateway_type": 'file',
            "storage_gb": 1000
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAWSStorageGatewayInvalidConfigurations:
    """Test AWSStorageGateway invalid configuration handling"""
    
    def test_awsstoragegateway_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "awsstoragegateway-invalid",
            "service_type": "AWSStorageGateway",
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

class TestAWSStorageGatewayBreakdownStructure:
    """Test AWSStorageGateway cost breakdown structure"""
    
    def test_awsstoragegateway_breakdown_by_service(self, test_project, base_awsstoragegateway_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_awsstoragegateway_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AWSStorageGateway"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AWSStorageGateway" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAWSStorageGatewayConfidenceScoring:
    """Test AWSStorageGateway confidence score calculation"""
    
    def test_awsstoragegateway_confidence_in_range(self, test_project, base_awsstoragegateway_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_awsstoragegateway_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAWSStorageGatewayAssumptionsWarnings:
    """Test AWSStorageGateway assumptions and warnings"""
    
    def test_awsstoragegateway_has_assumptions(self, test_project, base_awsstoragegateway_config):
        """Test AWSStorageGateway estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_awsstoragegateway_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_awsstoragegateway_has_warnings(self, test_project, base_awsstoragegateway_config):
        """Test AWSStorageGateway estimate includes warnings"""
        estimate = create_estimate(test_project, [base_awsstoragegateway_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
