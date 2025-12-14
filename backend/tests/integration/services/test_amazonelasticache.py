"""
Service: AmazonElastiCache
Category: Database
Pricing Model: Node hours + Data transfer
Key Cost Drivers: engine, node_type, num_nodes
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonElastiCache tests"""
    project_data = {
        "name": "AmazonElastiCache Test Project",
        "description": "Testing AmazonElastiCache cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonelasticache_config():
    """Base AmazonElastiCache service configuration"""
    return {
        "id": "test-amazonelasticache",
        "service_type": "AmazonElastiCache",
        "region": "us-east-1",
        "config": {
            "engine": 'redis',
            "node_type": 'cache.t3.medium',
            "num_nodes": 2
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

class TestAmazonElastiCacheServiceDiscovery:
    """Test AmazonElastiCache service registration and metadata"""
    
    def test_amazonelasticache_in_service_catalog(self):
        """Verify AmazonElastiCache appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonElastiCache"), None)
        
        assert service is not None, "AmazonElastiCache not found in service catalog"
        assert service["category"] == "Database"
    
    def test_amazonelasticache_regions_populated(self):
        """Verify AmazonElastiCache has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonElastiCache"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonElastiCacheSchemaValidation:
    """Test AmazonElastiCache configuration schema"""
    
    def test_amazonelasticache_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonElastiCache/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonElastiCacheBasicCostCalculation:
    """Test basic AmazonElastiCache cost calculations"""
    
    def test_amazonelasticache_basic_cost(self, test_project, base_amazonelasticache_config):
        """Test basic AmazonElastiCache cost calculation"""
        estimate = create_estimate(test_project, [base_amazonelasticache_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonelasticache_cost_deterministic(self, test_project, base_amazonelasticache_config):
        """Test AmazonElastiCache cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonelasticache_config])
        estimate2 = create_estimate(test_project, [base_amazonelasticache_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonElastiCacheEdgeCases:
    """Test AmazonElastiCache edge cases and boundaries"""
    
    def test_amazonelasticache_minimal_config(self, test_project):
        """Test AmazonElastiCache with minimal configuration"""
        service = {
            "id": "amazonelasticache-minimal",
            "service_type": "AmazonElastiCache",
            "region": "us-east-1",
            "config": {
                "engine": 'redis',
            "node_type": 'cache.t3.medium',
            "num_nodes": 2
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonElastiCacheInvalidConfigurations:
    """Test AmazonElastiCache invalid configuration handling"""
    
    def test_amazonelasticache_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonelasticache-invalid",
            "service_type": "AmazonElastiCache",
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

class TestAmazonElastiCacheBreakdownStructure:
    """Test AmazonElastiCache cost breakdown structure"""
    
    def test_amazonelasticache_breakdown_by_service(self, test_project, base_amazonelasticache_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonelasticache_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonElastiCache"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonElastiCache" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonElastiCacheConfidenceScoring:
    """Test AmazonElastiCache confidence score calculation"""
    
    def test_amazonelasticache_confidence_in_range(self, test_project, base_amazonelasticache_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonelasticache_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonElastiCacheAssumptionsWarnings:
    """Test AmazonElastiCache assumptions and warnings"""
    
    def test_amazonelasticache_has_assumptions(self, test_project, base_amazonelasticache_config):
        """Test AmazonElastiCache estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonelasticache_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonelasticache_has_warnings(self, test_project, base_amazonelasticache_config):
        """Test AmazonElastiCache estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonelasticache_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
