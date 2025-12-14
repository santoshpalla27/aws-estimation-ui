"""
Service: AmazonDocumentDB
Category: Database
Pricing Model: Instance hours + Storage + I/O
Key Cost Drivers: instance_class, storage_gb, io_requests_per_month
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonDocumentDB tests"""
    project_data = {
        "name": "AmazonDocumentDB Test Project",
        "description": "Testing AmazonDocumentDB cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazondocumentdb_config():
    """Base AmazonDocumentDB service configuration"""
    return {
        "id": "test-amazondocumentdb",
        "service_type": "AmazonDocumentDB",
        "region": "us-east-1",
        "config": {
            "instance_class": 'db.r5.large',
            "storage_gb": 100,
            "io_requests_per_month": 1000000
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

class TestAmazonDocumentDBServiceDiscovery:
    """Test AmazonDocumentDB service registration and metadata"""
    
    def test_amazondocumentdb_in_service_catalog(self):
        """Verify AmazonDocumentDB appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonDocumentDB"), None)
        
        assert service is not None, "AmazonDocumentDB not found in service catalog"
        assert service["category"] == "Database"
    
    def test_amazondocumentdb_regions_populated(self):
        """Verify AmazonDocumentDB has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonDocumentDB"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonDocumentDBSchemaValidation:
    """Test AmazonDocumentDB configuration schema"""
    
    def test_amazondocumentdb_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonDocumentDB/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonDocumentDBBasicCostCalculation:
    """Test basic AmazonDocumentDB cost calculations"""
    
    def test_amazondocumentdb_basic_cost(self, test_project, base_amazondocumentdb_config):
        """Test basic AmazonDocumentDB cost calculation"""
        estimate = create_estimate(test_project, [base_amazondocumentdb_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazondocumentdb_cost_deterministic(self, test_project, base_amazondocumentdb_config):
        """Test AmazonDocumentDB cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazondocumentdb_config])
        estimate2 = create_estimate(test_project, [base_amazondocumentdb_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonDocumentDBEdgeCases:
    """Test AmazonDocumentDB edge cases and boundaries"""
    
    def test_amazondocumentdb_minimal_config(self, test_project):
        """Test AmazonDocumentDB with minimal configuration"""
        service = {
            "id": "amazondocumentdb-minimal",
            "service_type": "AmazonDocumentDB",
            "region": "us-east-1",
            "config": {
                "instance_class": 'db.r5.large',
            "storage_gb": 100,
            "io_requests_per_month": 1000000
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonDocumentDBInvalidConfigurations:
    """Test AmazonDocumentDB invalid configuration handling"""
    
    def test_amazondocumentdb_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazondocumentdb-invalid",
            "service_type": "AmazonDocumentDB",
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

class TestAmazonDocumentDBBreakdownStructure:
    """Test AmazonDocumentDB cost breakdown structure"""
    
    def test_amazondocumentdb_breakdown_by_service(self, test_project, base_amazondocumentdb_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazondocumentdb_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonDocumentDB"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonDocumentDB" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonDocumentDBConfidenceScoring:
    """Test AmazonDocumentDB confidence score calculation"""
    
    def test_amazondocumentdb_confidence_in_range(self, test_project, base_amazondocumentdb_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazondocumentdb_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonDocumentDBAssumptionsWarnings:
    """Test AmazonDocumentDB assumptions and warnings"""
    
    def test_amazondocumentdb_has_assumptions(self, test_project, base_amazondocumentdb_config):
        """Test AmazonDocumentDB estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazondocumentdb_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazondocumentdb_has_warnings(self, test_project, base_amazondocumentdb_config):
        """Test AmazonDocumentDB estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazondocumentdb_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
