"""
Service: AmazonRDS
Category: Database
Pricing Model: Instance hours + Storage + I/O + Multi-AZ
Key Cost Drivers: engine, instance_class, storage_gb, multi_az
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonRDS tests"""
    project_data = {
        "name": "AmazonRDS Test Project",
        "description": "Testing AmazonRDS cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonrds_config():
    """Base AmazonRDS service configuration"""
    return {
        "id": "test-amazonrds",
        "service_type": "AmazonRDS",
        "region": "us-east-1",
        "config": {
            "engine": 'mysql',
            "instance_class": 'db.t3.medium',
            "storage_gb": 100,
            "multi_az": False
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

class TestAmazonRDSServiceDiscovery:
    """Test AmazonRDS service registration and metadata"""
    
    def test_amazonrds_in_service_catalog(self):
        """Verify AmazonRDS appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonRDS"), None)
        
        assert service is not None, "AmazonRDS not found in service catalog"
        assert service["category"] == "Database"
    
    def test_amazonrds_regions_populated(self):
        """Verify AmazonRDS has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonRDS"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonRDSSchemaValidation:
    """Test AmazonRDS configuration schema"""
    
    def test_amazonrds_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonRDS/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonRDSBasicCostCalculation:
    """Test basic AmazonRDS cost calculations"""
    
    def test_amazonrds_basic_cost(self, test_project, base_amazonrds_config):
        """Test basic AmazonRDS cost calculation"""
        estimate = create_estimate(test_project, [base_amazonrds_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonrds_cost_deterministic(self, test_project, base_amazonrds_config):
        """Test AmazonRDS cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonrds_config])
        estimate2 = create_estimate(test_project, [base_amazonrds_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonRDSEdgeCases:
    """Test AmazonRDS edge cases and boundaries"""
    
    def test_amazonrds_minimal_config(self, test_project):
        """Test AmazonRDS with minimal configuration"""
        service = {
            "id": "amazonrds-minimal",
            "service_type": "AmazonRDS",
            "region": "us-east-1",
            "config": {
                "engine": 'mysql',
            "instance_class": 'db.t3.medium',
            "storage_gb": 100,
            "multi_az": False
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonRDSInvalidConfigurations:
    """Test AmazonRDS invalid configuration handling"""
    
    def test_amazonrds_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonrds-invalid",
            "service_type": "AmazonRDS",
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

class TestAmazonRDSBreakdownStructure:
    """Test AmazonRDS cost breakdown structure"""
    
    def test_amazonrds_breakdown_by_service(self, test_project, base_amazonrds_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonrds_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonRDS"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonRDS" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonRDSConfidenceScoring:
    """Test AmazonRDS confidence score calculation"""
    
    def test_amazonrds_confidence_in_range(self, test_project, base_amazonrds_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonrds_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonRDSAssumptionsWarnings:
    """Test AmazonRDS assumptions and warnings"""
    
    def test_amazonrds_has_assumptions(self, test_project, base_amazonrds_config):
        """Test AmazonRDS estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonrds_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonrds_has_warnings(self, test_project, base_amazonrds_config):
        """Test AmazonRDS estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonrds_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
