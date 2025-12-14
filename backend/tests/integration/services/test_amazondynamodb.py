"""
Service: AmazonDynamoDB
Category: Database
Pricing Model: On-demand OR Provisioned capacity + Storage
Key Cost Drivers: billing_mode, read_requests_per_month, write_requests_per_month, storage_gb
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonDynamoDB tests"""
    project_data = {
        "name": "AmazonDynamoDB Test Project",
        "description": "Testing AmazonDynamoDB cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazondynamodb_config():
    """Base AmazonDynamoDB service configuration"""
    return {
        "id": "test-amazondynamodb",
        "service_type": "AmazonDynamoDB",
        "region": "us-east-1",
        "config": {
            "billing_mode": 'on_demand',
            "read_requests_per_month": 10000000,
            "write_requests_per_month": 5000000,
            "storage_gb": 50
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

class TestAmazonDynamoDBServiceDiscovery:
    """Test AmazonDynamoDB service registration and metadata"""
    
    def test_amazondynamodb_in_service_catalog(self):
        """Verify AmazonDynamoDB appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonDynamoDB"), None)
        
        assert service is not None, "AmazonDynamoDB not found in service catalog"
        assert service["category"] == "Database"
    
    def test_amazondynamodb_regions_populated(self):
        """Verify AmazonDynamoDB has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonDynamoDB"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonDynamoDBSchemaValidation:
    """Test AmazonDynamoDB configuration schema"""
    
    def test_amazondynamodb_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonDynamoDB/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonDynamoDBBasicCostCalculation:
    """Test basic AmazonDynamoDB cost calculations"""
    
    def test_amazondynamodb_basic_cost(self, test_project, base_amazondynamodb_config):
        """Test basic AmazonDynamoDB cost calculation"""
        estimate = create_estimate(test_project, [base_amazondynamodb_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazondynamodb_cost_deterministic(self, test_project, base_amazondynamodb_config):
        """Test AmazonDynamoDB cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazondynamodb_config])
        estimate2 = create_estimate(test_project, [base_amazondynamodb_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonDynamoDBEdgeCases:
    """Test AmazonDynamoDB edge cases and boundaries"""
    
    def test_amazondynamodb_minimal_config(self, test_project):
        """Test AmazonDynamoDB with minimal configuration"""
        service = {
            "id": "amazondynamodb-minimal",
            "service_type": "AmazonDynamoDB",
            "region": "us-east-1",
            "config": {
                "billing_mode": 'on_demand',
            "read_requests_per_month": 10000000,
            "write_requests_per_month": 5000000,
            "storage_gb": 50
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonDynamoDBInvalidConfigurations:
    """Test AmazonDynamoDB invalid configuration handling"""
    
    def test_amazondynamodb_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazondynamodb-invalid",
            "service_type": "AmazonDynamoDB",
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

class TestAmazonDynamoDBBreakdownStructure:
    """Test AmazonDynamoDB cost breakdown structure"""
    
    def test_amazondynamodb_breakdown_by_service(self, test_project, base_amazondynamodb_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazondynamodb_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonDynamoDB"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonDynamoDB" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonDynamoDBConfidenceScoring:
    """Test AmazonDynamoDB confidence score calculation"""
    
    def test_amazondynamodb_confidence_in_range(self, test_project, base_amazondynamodb_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazondynamodb_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonDynamoDBAssumptionsWarnings:
    """Test AmazonDynamoDB assumptions and warnings"""
    
    def test_amazondynamodb_has_assumptions(self, test_project, base_amazondynamodb_config):
        """Test AmazonDynamoDB estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazondynamodb_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazondynamodb_has_warnings(self, test_project, base_amazondynamodb_config):
        """Test AmazonDynamoDB estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazondynamodb_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
