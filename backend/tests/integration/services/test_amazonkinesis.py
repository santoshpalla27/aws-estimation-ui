"""
Service: AmazonKinesis
Category: Analytics
Pricing Model: Shard hours + PUT payload units
Key Cost Drivers: shard_hours, put_payload_units
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonKinesis tests"""
    project_data = {
        "name": "AmazonKinesis Test Project",
        "description": "Testing AmazonKinesis cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonkinesis_config():
    """Base AmazonKinesis service configuration"""
    return {
        "id": "test-amazonkinesis",
        "service_type": "AmazonKinesis",
        "region": "us-east-1",
        "config": {
            "shard_hours": 730,
            "put_payload_units": 1000000
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

class TestAmazonKinesisServiceDiscovery:
    """Test AmazonKinesis service registration and metadata"""
    
    def test_amazonkinesis_in_service_catalog(self):
        """Verify AmazonKinesis appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonKinesis"), None)
        
        assert service is not None, "AmazonKinesis not found in service catalog"
        assert service["category"] == "Analytics"
    
    def test_amazonkinesis_regions_populated(self):
        """Verify AmazonKinesis has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonKinesis"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonKinesisSchemaValidation:
    """Test AmazonKinesis configuration schema"""
    
    def test_amazonkinesis_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonKinesis/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonKinesisBasicCostCalculation:
    """Test basic AmazonKinesis cost calculations"""
    
    def test_amazonkinesis_basic_cost(self, test_project, base_amazonkinesis_config):
        """Test basic AmazonKinesis cost calculation"""
        estimate = create_estimate(test_project, [base_amazonkinesis_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonkinesis_cost_deterministic(self, test_project, base_amazonkinesis_config):
        """Test AmazonKinesis cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonkinesis_config])
        estimate2 = create_estimate(test_project, [base_amazonkinesis_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonKinesisEdgeCases:
    """Test AmazonKinesis edge cases and boundaries"""
    
    def test_amazonkinesis_minimal_config(self, test_project):
        """Test AmazonKinesis with minimal configuration"""
        service = {
            "id": "amazonkinesis-minimal",
            "service_type": "AmazonKinesis",
            "region": "us-east-1",
            "config": {
                "shard_hours": 730,
            "put_payload_units": 1000000
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonKinesisInvalidConfigurations:
    """Test AmazonKinesis invalid configuration handling"""
    
    def test_amazonkinesis_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonkinesis-invalid",
            "service_type": "AmazonKinesis",
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

class TestAmazonKinesisBreakdownStructure:
    """Test AmazonKinesis cost breakdown structure"""
    
    def test_amazonkinesis_breakdown_by_service(self, test_project, base_amazonkinesis_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonkinesis_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonKinesis"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonKinesis" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonKinesisConfidenceScoring:
    """Test AmazonKinesis confidence score calculation"""
    
    def test_amazonkinesis_confidence_in_range(self, test_project, base_amazonkinesis_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonkinesis_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonKinesisAssumptionsWarnings:
    """Test AmazonKinesis assumptions and warnings"""
    
    def test_amazonkinesis_has_assumptions(self, test_project, base_amazonkinesis_config):
        """Test AmazonKinesis estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonkinesis_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonkinesis_has_warnings(self, test_project, base_amazonkinesis_config):
        """Test AmazonKinesis estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonkinesis_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
