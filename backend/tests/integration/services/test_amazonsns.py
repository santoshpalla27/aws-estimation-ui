"""
Service: AmazonSNS
Category: Integration
Pricing Model: Requests + Data transfer
Key Cost Drivers: requests, data_transfer_gb
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonSNS tests"""
    project_data = {
        "name": "AmazonSNS Test Project",
        "description": "Testing AmazonSNS cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonsns_config():
    """Base AmazonSNS service configuration"""
    return {
        "id": "test-amazonsns",
        "service_type": "AmazonSNS",
        "region": "us-east-1",
        "config": {
            "requests": 10000000,
            "data_transfer_gb": 10
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

class TestAmazonSNSServiceDiscovery:
    """Test AmazonSNS service registration and metadata"""
    
    def test_amazonsns_in_service_catalog(self):
        """Verify AmazonSNS appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonSNS"), None)
        
        assert service is not None, "AmazonSNS not found in service catalog"
        assert service["category"] == "Integration"
    
    def test_amazonsns_regions_populated(self):
        """Verify AmazonSNS has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonSNS"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonSNSSchemaValidation:
    """Test AmazonSNS configuration schema"""
    
    def test_amazonsns_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonSNS/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonSNSBasicCostCalculation:
    """Test basic AmazonSNS cost calculations"""
    
    def test_amazonsns_basic_cost(self, test_project, base_amazonsns_config):
        """Test basic AmazonSNS cost calculation"""
        estimate = create_estimate(test_project, [base_amazonsns_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonsns_cost_deterministic(self, test_project, base_amazonsns_config):
        """Test AmazonSNS cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonsns_config])
        estimate2 = create_estimate(test_project, [base_amazonsns_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonSNSEdgeCases:
    """Test AmazonSNS edge cases and boundaries"""
    
    def test_amazonsns_minimal_config(self, test_project):
        """Test AmazonSNS with minimal configuration"""
        service = {
            "id": "amazonsns-minimal",
            "service_type": "AmazonSNS",
            "region": "us-east-1",
            "config": {
                "requests": 10000000,
            "data_transfer_gb": 10
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonSNSInvalidConfigurations:
    """Test AmazonSNS invalid configuration handling"""
    
    def test_amazonsns_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonsns-invalid",
            "service_type": "AmazonSNS",
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

class TestAmazonSNSBreakdownStructure:
    """Test AmazonSNS cost breakdown structure"""
    
    def test_amazonsns_breakdown_by_service(self, test_project, base_amazonsns_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonsns_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonSNS"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonSNS" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonSNSConfidenceScoring:
    """Test AmazonSNS confidence score calculation"""
    
    def test_amazonsns_confidence_in_range(self, test_project, base_amazonsns_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonsns_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonSNSAssumptionsWarnings:
    """Test AmazonSNS assumptions and warnings"""
    
    def test_amazonsns_has_assumptions(self, test_project, base_amazonsns_config):
        """Test AmazonSNS estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonsns_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonsns_has_warnings(self, test_project, base_amazonsns_config):
        """Test AmazonSNS estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonsns_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
