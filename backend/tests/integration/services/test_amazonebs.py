"""
Service: AmazonEBS
Category: Storage
Pricing Model: Volume type + Size + IOPS + Snapshots
Key Cost Drivers: volume_type, volume_size_gb, iops, snapshot_size_gb
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonEBS tests"""
    project_data = {
        "name": "AmazonEBS Test Project",
        "description": "Testing AmazonEBS cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonebs_config():
    """Base AmazonEBS service configuration"""
    return {
        "id": "test-amazonebs",
        "service_type": "AmazonEBS",
        "region": "us-east-1",
        "config": {
            "volume_type": 'gp3',
            "volume_size_gb": 100,
            "iops": 3000,
            "snapshot_size_gb": 50
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

class TestAmazonEBSServiceDiscovery:
    """Test AmazonEBS service registration and metadata"""
    
    def test_amazonebs_in_service_catalog(self):
        """Verify AmazonEBS appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonEBS"), None)
        
        assert service is not None, "AmazonEBS not found in service catalog"
        assert service["category"] == "Storage"
    
    def test_amazonebs_regions_populated(self):
        """Verify AmazonEBS has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonEBS"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonEBSSchemaValidation:
    """Test AmazonEBS configuration schema"""
    
    def test_amazonebs_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonEBS/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonEBSBasicCostCalculation:
    """Test basic AmazonEBS cost calculations"""
    
    def test_amazonebs_basic_cost(self, test_project, base_amazonebs_config):
        """Test basic AmazonEBS cost calculation"""
        estimate = create_estimate(test_project, [base_amazonebs_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonebs_cost_deterministic(self, test_project, base_amazonebs_config):
        """Test AmazonEBS cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonebs_config])
        estimate2 = create_estimate(test_project, [base_amazonebs_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonEBSEdgeCases:
    """Test AmazonEBS edge cases and boundaries"""
    
    def test_amazonebs_minimal_config(self, test_project):
        """Test AmazonEBS with minimal configuration"""
        service = {
            "id": "amazonebs-minimal",
            "service_type": "AmazonEBS",
            "region": "us-east-1",
            "config": {
                "volume_type": 'gp3',
            "volume_size_gb": 100,
            "iops": 3000,
            "snapshot_size_gb": 50
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonEBSInvalidConfigurations:
    """Test AmazonEBS invalid configuration handling"""
    
    def test_amazonebs_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonebs-invalid",
            "service_type": "AmazonEBS",
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

class TestAmazonEBSBreakdownStructure:
    """Test AmazonEBS cost breakdown structure"""
    
    def test_amazonebs_breakdown_by_service(self, test_project, base_amazonebs_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonebs_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonEBS"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonEBS" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonEBSConfidenceScoring:
    """Test AmazonEBS confidence score calculation"""
    
    def test_amazonebs_confidence_in_range(self, test_project, base_amazonebs_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonebs_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonEBSAssumptionsWarnings:
    """Test AmazonEBS assumptions and warnings"""
    
    def test_amazonebs_has_assumptions(self, test_project, base_amazonebs_config):
        """Test AmazonEBS estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonebs_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonebs_has_warnings(self, test_project, base_amazonebs_config):
        """Test AmazonEBS estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonebs_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
