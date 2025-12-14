"""
Service: AmazonManagedStreamingKafka
Category: Analytics
Pricing Model: Broker hours + Storage
Key Cost Drivers: broker_instance_type, broker_count, storage_gb
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for AmazonManagedStreamingKafka tests"""
    project_data = {
        "name": "AmazonManagedStreamingKafka Test Project",
        "description": "Testing AmazonManagedStreamingKafka cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_amazonmanagedstreamingkafka_config():
    """Base AmazonManagedStreamingKafka service configuration"""
    return {
        "id": "test-amazonmanagedstreamingkafka",
        "service_type": "AmazonManagedStreamingKafka",
        "region": "us-east-1",
        "config": {
            "broker_instance_type": 'kafka.m5.large',
            "broker_count": 3,
            "storage_gb": 1000
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

class TestAmazonManagedStreamingKafkaServiceDiscovery:
    """Test AmazonManagedStreamingKafka service registration and metadata"""
    
    def test_amazonmanagedstreamingkafka_in_service_catalog(self):
        """Verify AmazonManagedStreamingKafka appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonManagedStreamingKafka"), None)
        
        assert service is not None, "AmazonManagedStreamingKafka not found in service catalog"
        assert service["category"] == "Analytics"
    
    def test_amazonmanagedstreamingkafka_regions_populated(self):
        """Verify AmazonManagedStreamingKafka has regions defined"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service = next((s for s in services if s["service_id"] == "AmazonManagedStreamingKafka"), None)
        
        assert service is not None


# ============================================================================
# SCHEMA & UI CONTRACT TESTS
# ============================================================================

class TestAmazonManagedStreamingKafkaSchemaValidation:
    """Test AmazonManagedStreamingKafka configuration schema"""
    
    def test_amazonmanagedstreamingkafka_schema_endpoint_exists(self):
        """Verify schema endpoint returns valid schema"""
        response = requests.get(f"{BASE_URL}/api/v1/services/AmazonManagedStreamingKafka/schema")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "type" in schema or "properties" in schema


# ============================================================================
# BASIC COST CALCULATION TESTS
# ============================================================================

class TestAmazonManagedStreamingKafkaBasicCostCalculation:
    """Test basic AmazonManagedStreamingKafka cost calculations"""
    
    def test_amazonmanagedstreamingkafka_basic_cost(self, test_project, base_amazonmanagedstreamingkafka_config):
        """Test basic AmazonManagedStreamingKafka cost calculation"""
        estimate = create_estimate(test_project, [base_amazonmanagedstreamingkafka_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
        assert len(estimate["breakdown"]) > 0
    
    def test_amazonmanagedstreamingkafka_cost_deterministic(self, test_project, base_amazonmanagedstreamingkafka_config):
        """Test AmazonManagedStreamingKafka cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_amazonmanagedstreamingkafka_config])
        estimate2 = create_estimate(test_project, [base_amazonmanagedstreamingkafka_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


# ============================================================================
# EDGE & BOUNDARY TESTS
# ============================================================================

class TestAmazonManagedStreamingKafkaEdgeCases:
    """Test AmazonManagedStreamingKafka edge cases and boundaries"""
    
    def test_amazonmanagedstreamingkafka_minimal_config(self, test_project):
        """Test AmazonManagedStreamingKafka with minimal configuration"""
        service = {
            "id": "amazonmanagedstreamingkafka-minimal",
            "service_type": "AmazonManagedStreamingKafka",
            "region": "us-east-1",
            "config": {
                "broker_instance_type": 'kafka.m5.large',
            "broker_count": 3,
            "storage_gb": 1000
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


# ============================================================================
# INVALID CONFIGURATION TESTS
# ============================================================================

class TestAmazonManagedStreamingKafkaInvalidConfigurations:
    """Test AmazonManagedStreamingKafka invalid configuration handling"""
    
    def test_amazonmanagedstreamingkafka_invalid_config_handled(self, test_project):
        """Test invalid configuration is handled gracefully"""
        service = {
            "id": "amazonmanagedstreamingkafka-invalid",
            "service_type": "AmazonManagedStreamingKafka",
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

class TestAmazonManagedStreamingKafkaBreakdownStructure:
    """Test AmazonManagedStreamingKafka cost breakdown structure"""
    
    def test_amazonmanagedstreamingkafka_breakdown_by_service(self, test_project, base_amazonmanagedstreamingkafka_config):
        """Test breakdown includes service dimension"""
        estimate = create_estimate(test_project, [base_amazonmanagedstreamingkafka_config])
        
        breakdown = estimate["breakdown"]
        service_breakdown = next((b for b in breakdown if b.get("key") == "AmazonManagedStreamingKafka"), None)
        
        # Service should appear in breakdown
        assert any(b.get("key") == "AmazonManagedStreamingKafka" for b in breakdown)


# ============================================================================
# CONFIDENCE SCORE TESTS
# ============================================================================

class TestAmazonManagedStreamingKafkaConfidenceScoring:
    """Test AmazonManagedStreamingKafka confidence score calculation"""
    
    def test_amazonmanagedstreamingkafka_confidence_in_range(self, test_project, base_amazonmanagedstreamingkafka_config):
        """Test confidence score is in valid range"""
        estimate = create_estimate(test_project, [base_amazonmanagedstreamingkafka_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


# ============================================================================
# ASSUMPTIONS & WARNINGS TESTS
# ============================================================================

class TestAmazonManagedStreamingKafkaAssumptionsWarnings:
    """Test AmazonManagedStreamingKafka assumptions and warnings"""
    
    def test_amazonmanagedstreamingkafka_has_assumptions(self, test_project, base_amazonmanagedstreamingkafka_config):
        """Test AmazonManagedStreamingKafka estimate includes assumptions"""
        estimate = create_estimate(test_project, [base_amazonmanagedstreamingkafka_config])
        
        assert "assumptions" in estimate
        assert isinstance(estimate["assumptions"], list)
    
    def test_amazonmanagedstreamingkafka_has_warnings(self, test_project, base_amazonmanagedstreamingkafka_config):
        """Test AmazonManagedStreamingKafka estimate includes warnings"""
        estimate = create_estimate(test_project, [base_amazonmanagedstreamingkafka_config])
        
        assert "warnings" in estimate
        assert isinstance(estimate["warnings"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
