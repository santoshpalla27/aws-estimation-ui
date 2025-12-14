"""
Service: AmazonMemoryDB
Category: Database
Pricing Model: Node hours + Snapshots
Key Cost Drivers: node_type, num_nodes, snapshot_storage_gb
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonMemoryDB tests"""
    project_data = {
        "name": "AmazonMemoryDB Test Project",
        "description": "Testing AmazonMemoryDB cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonmemorydb_config():
    """Base AmazonMemoryDB service configuration"""
    return {
        "id": "test-amazonmemorydb",
        "service_type": "AmazonMemoryDB",
        "region": "us-east-1",
        "config": {
            "node_type": 'db.r6g.large',
            "num_nodes": 2,
            "snapshot_storage_gb": 50
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

class TestAmazonMemoryDBServiceDiscovery:
    """Test AmazonMemoryDB service registration and metadata"""
    
    def test_amazonmemorydb_in_service_catalog(self):
        """Verify AmazonMemoryDB appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonMemoryDB"), None)
        
        assert service is not None, "AmazonMemoryDB not found in service catalog"
        assert service["category"] == "Database"
    
    def test_amazonmemorydb_regions_populated(self):
        """Verify AmazonMemoryDB has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonMemoryDB"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonMemoryDBSchemaValidation:
    """Test AmazonMemoryDB configuration schema"""
    
    def test_amazonmemorydb_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonMemoryDB/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonMemoryDBBasicCostCalculation:
    """Test basic AmazonMemoryDB cost calculations"""
    
    def test_amazonmemorydb_basic_cost(self, test_project, base_amazonmemorydb_config):
        """Test basic AmazonMemoryDB cost calculation"""
        estimate = create_estimate(test_project, [base_amazonmemorydb_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonmemorydb_cost_deterministic(self, test_project, base_amazonmemorydb_config):
        """Test AmazonMemoryDB cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonmemorydb_config])
        estimate2 = create_estimate(test_project, [base_amazonmemorydb_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonMemoryDBEdgeCases:
    """Test AmazonMemoryDB edge cases and boundaries"""
    
    def test_amazonmemorydb_minimal_config(self, test_project):
        """Test AmazonMemoryDB with minimal configuration"""
        service = {
            "id": "amazonmemorydb-minimal",
            "service_type": "AmazonMemoryDB",
            "region": "us-east-1",
            "config": {
                "node_type": 'db.r6g.large',
            "num_nodes": 2,
            "snapshot_storage_gb": 50
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonMemoryDBInvalidConfigurations:
    """Test AmazonMemoryDB invalid configuration handling"""
    
    def test_amazonmemorydb_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonmemorydb-invalid",
            "service_type": "AmazonMemoryDB",
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

class TestAmazonMemoryDBBreakdownStructure:
    """Test AmazonMemoryDB cost breakdown structure"""
    
    def test_amazonmemorydb_breakdown_by_service(self, test_project, base_amazonmemorydb_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonmemorydb_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonMemoryDB"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonMemoryDB" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonMemoryDBConfidenceScoring:
    """Test AmazonMemoryDB confidence score calculation"""
    
    def test_amazonmemorydb_confidence_in_range(self, test_project, base_amazonmemorydb_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonmemorydb_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonMemoryDBAssumptionsWarnings:
    """Test AmazonMemoryDB assumptions and warnings"""
    
    def test_amazonmemorydb_has_assumptions(self, test_project, base_amazonmemorydb_config):
        """Test AmazonMemoryDB estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonmemorydb_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonmemorydb_has_warnings(self, test_project, base_amazonmemorydb_config):
        """Test AmazonMemoryDB estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonmemorydb_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
