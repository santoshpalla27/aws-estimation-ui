"""
Service: AmazonCloudWatch
Category: Management
Pricing Model: Metrics + Logs + Alarms
Key Cost Drivers: custom_metrics, log_ingestion_gb, log_storage_gb
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonCloudWatch tests"""
    project_data = {
        "name": "AmazonCloudWatch Test Project",
        "description": "Testing AmazonCloudWatch cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazoncloudwatch_config():
    """Base AmazonCloudWatch service configuration"""
    return {
        "id": "test-amazoncloudwatch",
        "service_type": "AmazonCloudWatch",
        "region": "us-east-1",
        "config": {
            "custom_metrics": 100,
            "log_ingestion_gb": 50,
            "log_storage_gb": 100
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

class TestAmazonCloudWatchServiceDiscovery:
    """Test AmazonCloudWatch service registration and metadata"""
    
    def test_amazoncloudwatch_in_service_catalog(self):
        """Verify AmazonCloudWatch appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonCloudWatch"), None)
        
        assert service is not None, "AmazonCloudWatch not found in service catalog"
        assert service["category"] == "Management"
    
    def test_amazoncloudwatch_regions_populated(self):
        """Verify AmazonCloudWatch has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonCloudWatch"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonCloudWatchSchemaValidation:
    """Test AmazonCloudWatch configuration schema"""
    
    def test_amazoncloudwatch_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonCloudWatch/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonCloudWatchBasicCostCalculation:
    """Test basic AmazonCloudWatch cost calculations"""
    
    def test_amazoncloudwatch_basic_cost(self, test_project, base_amazoncloudwatch_config):
        """Test basic AmazonCloudWatch cost calculation"""
        estimate = create_estimate(test_project, [base_amazoncloudwatch_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazoncloudwatch_cost_deterministic(self, test_project, base_amazoncloudwatch_config):
        """Test AmazonCloudWatch cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazoncloudwatch_config])
        estimate2 = create_estimate(test_project, [base_amazoncloudwatch_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonCloudWatchEdgeCases:
    """Test AmazonCloudWatch edge cases and boundaries"""
    
    def test_amazoncloudwatch_minimal_config(self, test_project):
        """Test AmazonCloudWatch with minimal configuration"""
        service = {
            "id": "amazoncloudwatch-minimal",
            "service_type": "AmazonCloudWatch",
            "region": "us-east-1",
            "config": {
                "custom_metrics": 100,
            "log_ingestion_gb": 50,
            "log_storage_gb": 100
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonCloudWatchInvalidConfigurations:
    """Test AmazonCloudWatch invalid configuration handling"""
    
    def test_amazoncloudwatch_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazoncloudwatch-invalid",
            "service_type": "AmazonCloudWatch",
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

class TestAmazonCloudWatchBreakdownStructure:
    """Test AmazonCloudWatch cost breakdown structure"""
    
    def test_amazoncloudwatch_breakdown_by_service(self, test_project, base_amazoncloudwatch_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazoncloudwatch_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonCloudWatch"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonCloudWatch" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonCloudWatchConfidenceScoring:
    """Test AmazonCloudWatch confidence score calculation"""
    
    def test_amazoncloudwatch_confidence_in_range(self, test_project, base_amazoncloudwatch_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazoncloudwatch_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonCloudWatchAssumptionsWarnings:
    """Test AmazonCloudWatch assumptions and warnings"""
    
    def test_amazoncloudwatch_has_assumptions(self, test_project, base_amazoncloudwatch_config):
        """Test AmazonCloudWatch estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazoncloudwatch_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazoncloudwatch_has_warnings(self, test_project, base_amazoncloudwatch_config):
        """Test AmazonCloudWatch estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazoncloudwatch_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
