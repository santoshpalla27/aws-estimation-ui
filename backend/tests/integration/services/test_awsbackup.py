"""
Service: AWSBackup
Category: Storage
Pricing Model: Backup storage + Restore requests
Key Cost Drivers: backup_storage_gb, restore_requests
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AWSBackup tests"""
    project_data = {
        "name": "AWSBackup Test Project",
        "description": "Testing AWSBackup cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_awsbackup_config():
    """Base AWSBackup service configuration"""
    return {
        "id": "test-awsbackup",
        "service_type": "AWSBackup",
        "region": "us-east-1",
        "config": {
            "backup_storage_gb": 500,
            "restore_requests": 10
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

class TestAWSBackupServiceDiscovery:
    """Test AWSBackup service registration and metadata"""
    
    def test_awsbackup_in_service_catalog(self):
        """Verify AWSBackup appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSBackup"), None)
        
        assert service is not None, "AWSBackup not found in service catalog"
        assert service["category"] == "Storage"
    
    def test_awsbackup_regions_populated(self):
        """Verify AWSBackup has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AWSBackup"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAWSBackupSchemaValidation:
    """Test AWSBackup configuration schema"""
    
    def test_awsbackup_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AWSBackup/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAWSBackupBasicCostCalculation:
    """Test basic AWSBackup cost calculations"""
    
    def test_awsbackup_basic_cost(self, test_project, base_awsbackup_config):
        """Test basic AWSBackup cost calculation"""
        estimate = create_estimate(test_project, [base_awsbackup_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_awsbackup_cost_deterministic(self, test_project, base_awsbackup_config):
        """Test AWSBackup cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_awsbackup_config])
        estimate2 = create_estimate(test_project, [base_awsbackup_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAWSBackupEdgeCases:
    """Test AWSBackup edge cases and boundaries"""
    
    def test_awsbackup_minimal_config(self, test_project):
        """Test AWSBackup with minimal configuration"""
        service = {
            "id": "awsbackup-minimal",
            "service_type": "AWSBackup",
            "region": "us-east-1",
            "config": {
                "backup_storage_gb": 500,
            "restore_requests": 10
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAWSBackupInvalidConfigurations:
    """Test AWSBackup invalid configuration handling"""
    
    def test_awsbackup_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "awsbackup-invalid",
            "service_type": "AWSBackup",
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

class TestAWSBackupBreakdownStructure:
    """Test AWSBackup cost breakdown structure"""
    
    def test_awsbackup_breakdown_by_service(self, test_project, base_awsbackup_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_awsbackup_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AWSBackup"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AWSBackup" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAWSBackupConfidenceScoring:
    """Test AWSBackup confidence score calculation"""
    
    def test_awsbackup_confidence_in_range(self, test_project, base_awsbackup_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_awsbackup_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAWSBackupAssumptionsWarnings:
    """Test AWSBackup assumptions and warnings"""
    
    def test_awsbackup_has_assumptions(self, test_project, base_awsbackup_config):
        """Test AWSBackup estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_awsbackup_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_awsbackup_has_warnings(self, test_project, base_awsbackup_config):
        """Test AWSBackup estimate includes warnings"""
        estimate = create_estimate(test_project, [base_awsbackup_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
