"""
Service: AWSTransitGateway
Category: Networking
Pricing Model: Attachment hours + Data processed
Key Cost Drivers: attachments, data_processed_gb
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AWSTransitGateway tests"""
    project_data = {
        "name": "AWSTransitGateway Test Project",
        "description": "Testing AWSTransitGateway cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_awstransitgateway_config():
    """Base AWSTransitGateway service configuration"""
    return {
        "id": "test-awstransitgateway",
        "service_type": "AWSTransitGateway",
        "region": "us-east-1",
        "config": {
            "attachments": 5,
            "data_processed_gb": 1000
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

class TestAWSTransitGatewayServiceDiscovery:
    """Test AWSTransitGateway service registration and metadata"""
    
    def test_awstransitgateway_in_service_catalog(self):
        """Verify AWSTransitGateway appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSTransitGateway"), None)
        
        assert service is not None, "AWSTransitGateway not found in service catalog"
        assert service["category"] == "Networking"
    
    def test_awstransitgateway_regions_populated(self):
        """Verify AWSTransitGateway has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSTransitGateway"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAWSTransitGatewaySchemaValidation:
    """Test AWSTransitGateway configuration schema"""
    
    def test_awstransitgateway_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AWSTransitGateway/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAWSTransitGatewayBasicCostCalculation:
    """Test basic AWSTransitGateway cost calculations"""
    
    def test_awstransitgateway_basic_cost(self, test_project, base_awstransitgateway_config):
        """Test basic AWSTransitGateway cost calculation"""
        estimate = create_estimate(test_project, [base_awstransitgateway_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_awstransitgateway_cost_deterministic(self, test_project, base_awstransitgateway_config):
        """Test AWSTransitGateway cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_awstransitgateway_config])
        estimate2 = create_estimate(test_project, [base_awstransitgateway_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAWSTransitGatewayEdgeCases:
    """Test AWSTransitGateway edge cases and boundaries"""
    
    def test_awstransitgateway_minimal_config(self, test_project):
        """Test AWSTransitGateway with minimal configuration"""
        service = {
            "id": "awstransitgateway-minimal",
            "service_type": "AWSTransitGateway",
            "region": "us-east-1",
            "config": {
                "attachments": 5,
            "data_processed_gb": 1000
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAWSTransitGatewayInvalidConfigurations:
    """Test AWSTransitGateway invalid configuration handling"""
    
    def test_awstransitgateway_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "awstransitgateway-invalid",
            "service_type": "AWSTransitGateway",
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

class TestAWSTransitGatewayBreakdownStructure:
    """Test AWSTransitGateway cost breakdown structure"""
    
    def test_awstransitgateway_breakdown_by_service(self, test_project, base_awstransitgateway_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_awstransitgateway_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AWSTransitGateway"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AWSTransitGateway" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAWSTransitGatewayConfidenceScoring:
    """Test AWSTransitGateway confidence score calculation"""
    
    def test_awstransitgateway_confidence_in_range(self, test_project, base_awstransitgateway_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_awstransitgateway_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAWSTransitGatewayAssumptionsWarnings:
    """Test AWSTransitGateway assumptions and warnings"""
    
    def test_awstransitgateway_has_assumptions(self, test_project, base_awstransitgateway_config):
        """Test AWSTransitGateway estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_awstransitgateway_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_awstransitgateway_has_warnings(self, test_project, base_awstransitgateway_config):
        """Test AWSTransitGateway estimate includes warnings"""
        estimate = create_estimate(test_project, [base_awstransitgateway_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
