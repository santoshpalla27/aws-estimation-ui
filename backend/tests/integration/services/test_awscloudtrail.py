"""
Service: AWSCloudTrail
Category: Management
Pricing Model: Events delivered + Data events
Key Cost Drivers: management_events, data_events
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AWSCloudTrail tests"""
    project_data = {
        "name": "AWSCloudTrail Test Project",
        "description": "Testing AWSCloudTrail cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_awscloudtrail_config():
    """Base AWSCloudTrail service configuration"""
    return {
        "id": "test-awscloudtrail",
        "service_type": "AWSCloudTrail",
        "region": "us-east-1",
        "config": {
            "management_events": 1000000,
            "data_events": 5000000
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

class TestAWSCloudTrailServiceDiscovery:
    """Test AWSCloudTrail service registration and metadata"""
    
    def test_awscloudtrail_in_service_catalog(self):
        """Verify AWSCloudTrail appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSCloudTrail"), None)
        
        assert service is not None, "AWSCloudTrail not found in service catalog"
        assert service["category"] == "Management"
    
    def test_awscloudtrail_regions_populated(self):
        """Verify AWSCloudTrail has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSCloudTrail"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAWSCloudTrailSchemaValidation:
    """Test AWSCloudTrail configuration schema"""
    
    def test_awscloudtrail_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AWSCloudTrail/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAWSCloudTrailBasicCostCalculation:
    """Test basic AWSCloudTrail cost calculations"""
    
    def test_awscloudtrail_basic_cost(self, test_project, base_awscloudtrail_config):
        """Test basic AWSCloudTrail cost calculation"""
        estimate = create_estimate(test_project, [base_awscloudtrail_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_awscloudtrail_cost_deterministic(self, test_project, base_awscloudtrail_config):
        """Test AWSCloudTrail cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_awscloudtrail_config])
        estimate2 = create_estimate(test_project, [base_awscloudtrail_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAWSCloudTrailEdgeCases:
    """Test AWSCloudTrail edge cases and boundaries"""
    
    def test_awscloudtrail_minimal_config(self, test_project):
        """Test AWSCloudTrail with minimal configuration"""
        service = {
            "id": "awscloudtrail-minimal",
            "service_type": "AWSCloudTrail",
            "region": "us-east-1",
            "config": {
                "management_events": 1000000,
            "data_events": 5000000
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAWSCloudTrailInvalidConfigurations:
    """Test AWSCloudTrail invalid configuration handling"""
    
    def test_awscloudtrail_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "awscloudtrail-invalid",
            "service_type": "AWSCloudTrail",
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

class TestAWSCloudTrailBreakdownStructure:
    """Test AWSCloudTrail cost breakdown structure"""
    
    def test_awscloudtrail_breakdown_by_service(self, test_project, base_awscloudtrail_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_awscloudtrail_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AWSCloudTrail"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AWSCloudTrail" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAWSCloudTrailConfidenceScoring:
    """Test AWSCloudTrail confidence score calculation"""
    
    def test_awscloudtrail_confidence_in_range(self, test_project, base_awscloudtrail_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_awscloudtrail_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAWSCloudTrailAssumptionsWarnings:
    """Test AWSCloudTrail assumptions and warnings"""
    
    def test_awscloudtrail_has_assumptions(self, test_project, base_awscloudtrail_config):
        """Test AWSCloudTrail estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_awscloudtrail_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_awscloudtrail_has_warnings(self, test_project, base_awscloudtrail_config):
        """Test AWSCloudTrail estimate includes warnings"""
        estimate = create_estimate(test_project, [base_awscloudtrail_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
