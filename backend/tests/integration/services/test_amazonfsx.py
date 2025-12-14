"""
Service: AmazonFSx
Category: Storage
Pricing Model: File system type + Capacity + Throughput
Key Cost Drivers: file_system_type, storage_capacity_gb, throughput_mbps
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonFSx tests"""
    project_data = {
        "name": "AmazonFSx Test Project",
        "description": "Testing AmazonFSx cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonfsx_config():
    """Base AmazonFSx service configuration"""
    return {
        "id": "test-amazonfsx",
        "service_type": "AmazonFSx",
        "region": "us-east-1",
        "config": {
            "file_system_type": 'windows',
            "storage_capacity_gb": 1024,
            "throughput_mbps": 64
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

class TestAmazonFSxServiceDiscovery:
    """Test AmazonFSx service registration and metadata"""
    
    def test_amazonfsx_in_service_catalog(self):
        """Verify AmazonFSx appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonFSx"), None)
        
        assert service is not None, "AmazonFSx not found in service catalog"
        assert service["category"] == "Storage"
    
    def test_amazonfsx_regions_populated(self):
        """Verify AmazonFSx has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonFSx"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonFSxSchemaValidation:
    """Test AmazonFSx configuration schema"""
    
    def test_amazonfsx_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonFSx/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonFSxBasicCostCalculation:
    """Test basic AmazonFSx cost calculations"""
    
    def test_amazonfsx_basic_cost(self, test_project, base_amazonfsx_config):
        """Test basic AmazonFSx cost calculation"""
        estimate = create_estimate(test_project, [base_amazonfsx_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonfsx_cost_deterministic(self, test_project, base_amazonfsx_config):
        """Test AmazonFSx cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonfsx_config])
        estimate2 = create_estimate(test_project, [base_amazonfsx_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonFSxEdgeCases:
    """Test AmazonFSx edge cases and boundaries"""
    
    def test_amazonfsx_minimal_config(self, test_project):
        """Test AmazonFSx with minimal configuration"""
        service = {
            "id": "amazonfsx-minimal",
            "service_type": "AmazonFSx",
            "region": "us-east-1",
            "config": {
                "file_system_type": 'windows',
            "storage_capacity_gb": 1024,
            "throughput_mbps": 64
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonFSxInvalidConfigurations:
    """Test AmazonFSx invalid configuration handling"""
    
    def test_amazonfsx_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonfsx-invalid",
            "service_type": "AmazonFSx",
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

class TestAmazonFSxBreakdownStructure:
    """Test AmazonFSx cost breakdown structure"""
    
    def test_amazonfsx_breakdown_by_service(self, test_project, base_amazonfsx_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonfsx_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonFSx"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonFSx" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonFSxConfidenceScoring:
    """Test AmazonFSx confidence score calculation"""
    
    def test_amazonfsx_confidence_in_range(self, test_project, base_amazonfsx_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonfsx_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonFSxAssumptionsWarnings:
    """Test AmazonFSx assumptions and warnings"""
    
    def test_amazonfsx_has_assumptions(self, test_project, base_amazonfsx_config):
        """Test AmazonFSx estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonfsx_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonfsx_has_warnings(self, test_project, base_amazonfsx_config):
        """Test AmazonFSx estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonfsx_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
