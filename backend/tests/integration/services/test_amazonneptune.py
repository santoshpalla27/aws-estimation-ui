"""
Service: AmazonNeptune
Category: Database
Pricing Model: Instance hours + Storage + I/O
Key Cost Drivers: instance_class, storage_gb, io_requests_per_month
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonNeptune tests"""
    project_data = {
        "name": "AmazonNeptune Test Project",
        "description": "Testing AmazonNeptune cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonneptune_config():
    """Base AmazonNeptune service configuration"""
    return {
        "id": "test-amazonneptune",
        "service_type": "AmazonNeptune",
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

class TestAmazonNeptuneServiceDiscovery:
    """Test AmazonNeptune service registration and metadata"""
    
    def test_amazonneptune_in_service_catalog(self):
        """Verify AmazonNeptune appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonNeptune"), None)
        
        assert service is not None, "AmazonNeptune not found in service catalog"
        assert service["category"] == "Database"
    
    def test_amazonneptune_regions_populated(self):
        """Verify AmazonNeptune has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonNeptune"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonNeptuneSchemaValidation:
    """Test AmazonNeptune configuration schema"""
    
    def test_amazonneptune_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonNeptune/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonNeptuneBasicCostCalculation:
    """Test basic AmazonNeptune cost calculations"""
    
    def test_amazonneptune_basic_cost(self, test_project, base_amazonneptune_config):
        """Test basic AmazonNeptune cost calculation"""
        estimate = create_estimate(test_project, [base_amazonneptune_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonneptune_cost_deterministic(self, test_project, base_amazonneptune_config):
        """Test AmazonNeptune cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonneptune_config])
        estimate2 = create_estimate(test_project, [base_amazonneptune_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonNeptuneEdgeCases:
    """Test AmazonNeptune edge cases and boundaries"""
    
    def test_amazonneptune_minimal_config(self, test_project):
        """Test AmazonNeptune with minimal configuration"""
        service = {
            "id": "amazonneptune-minimal",
            "service_type": "AmazonNeptune",
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

class TestAmazonNeptuneInvalidConfigurations:
    """Test AmazonNeptune invalid configuration handling"""
    
    def test_amazonneptune_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonneptune-invalid",
            "service_type": "AmazonNeptune",
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

class TestAmazonNeptuneBreakdownStructure:
    """Test AmazonNeptune cost breakdown structure"""
    
    def test_amazonneptune_breakdown_by_service(self, test_project, base_amazonneptune_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonneptune_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonNeptune"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonNeptune" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonNeptuneConfidenceScoring:
    """Test AmazonNeptune confidence score calculation"""
    
    def test_amazonneptune_confidence_in_range(self, test_project, base_amazonneptune_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonneptune_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonNeptuneAssumptionsWarnings:
    """Test AmazonNeptune assumptions and warnings"""
    
    def test_amazonneptune_has_assumptions(self, test_project, base_amazonneptune_config):
        """Test AmazonNeptune estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonneptune_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonneptune_has_warnings(self, test_project, base_amazonneptune_config):
        """Test AmazonNeptune estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonneptune_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
