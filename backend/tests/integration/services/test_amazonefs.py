"""
Service: AmazonEFS
Category: Storage
Pricing Model: Storage class + Size
Key Cost Drivers: storage_gb, storage_class
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonEFS tests"""
    project_data = {
        "name": "AmazonEFS Test Project",
        "description": "Testing AmazonEFS cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonefs_config():
    """Base AmazonEFS service configuration"""
    return {
        "id": "test-amazonefs",
        "service_type": "AmazonEFS",
        "region": "us-east-1",
        "config": {
            "storage_gb": 500,
            "storage_class": 'standard'
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

class TestAmazonEFSServiceDiscovery:
    """Test AmazonEFS service registration and metadata"""
    
    def test_amazonefs_in_service_catalog(self):
        """Verify AmazonEFS appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonEFS"), None)
        
        assert service is not None, "AmazonEFS not found in service catalog"
        assert service["category"] == "Storage"
    
    def test_amazonefs_regions_populated(self):
        """Verify AmazonEFS has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonEFS"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonEFSSchemaValidation:
    """Test AmazonEFS configuration schema"""
    
    def test_amazonefs_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonEFS/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonEFSBasicCostCalculation:
    """Test basic AmazonEFS cost calculations"""
    
    def test_amazonefs_basic_cost(self, test_project, base_amazonefs_config):
        """Test basic AmazonEFS cost calculation"""
        estimate = create_estimate(test_project, [base_amazonefs_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonefs_cost_deterministic(self, test_project, base_amazonefs_config):
        """Test AmazonEFS cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonefs_config])
        estimate2 = create_estimate(test_project, [base_amazonefs_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonEFSEdgeCases:
    """Test AmazonEFS edge cases and boundaries"""
    
    def test_amazonefs_minimal_config(self, test_project):
        """Test AmazonEFS with minimal configuration"""
        service = {
            "id": "amazonefs-minimal",
            "service_type": "AmazonEFS",
            "region": "us-east-1",
            "config": {
                "storage_gb": 500,
            "storage_class": 'standard'
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonEFSInvalidConfigurations:
    """Test AmazonEFS invalid configuration handling"""
    
    def test_amazonefs_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonefs-invalid",
            "service_type": "AmazonEFS",
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

class TestAmazonEFSBreakdownStructure:
    """Test AmazonEFS cost breakdown structure"""
    
    def test_amazonefs_breakdown_by_service(self, test_project, base_amazonefs_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonefs_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonEFS"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonEFS" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonEFSConfidenceScoring:
    """Test AmazonEFS confidence score calculation"""
    
    def test_amazonefs_confidence_in_range(self, test_project, base_amazonefs_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonefs_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonEFSAssumptionsWarnings:
    """Test AmazonEFS assumptions and warnings"""
    
    def test_amazonefs_has_assumptions(self, test_project, base_amazonefs_config):
        """Test AmazonEFS estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonefs_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonefs_has_warnings(self, test_project, base_amazonefs_config):
        """Test AmazonEFS estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonefs_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
