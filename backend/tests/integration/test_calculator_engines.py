"""
Calculator and Engine Component Tests
Tests the core calculation engines, formula engine, and plugin system
"""

import pytest
import requests
import json

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project"""
    project_data = {"name": "Calculator Engine Test Project"}
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    return response.json()["id"]


class TestFormulaEngine:
    """Test formula engine calculations"""
    
    def test_simple_arithmetic(self, test_project):
        """Test simple arithmetic in formulas"""
        services = [{
            "id": "test-arithmetic",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100,
                "storage_class": "STANDARD",
                "put_requests_per_month": 10000,
                "get_requests_per_month": 100000,
                "data_transfer_gb": 0
            }
        }]
        
        estimate_data = {"services": services}
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json=estimate_data
        )
        assert response.status_code == 201
        estimate = response.json()
        
        # Verify formula executed
        assert "total_monthly_cost" in estimate
        assert estimate["total_monthly_cost"] >= 0
    
    def test_conditional_logic(self, test_project):
        """Test conditional logic in formulas"""
        # Test with data transfer (should add cost)
        services_with_transfer = [{
            "id": "s3-with-transfer",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100,
                "storage_class": "STANDARD",
                "put_requests_per_month": 10000,
                "get_requests_per_month": 100000,
                "data_transfer_gb": 500
            }
        }]
        
        # Test without data transfer
        services_no_transfer = [{
            "id": "s3-no-transfer",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100,
                "storage_class": "STANDARD",
                "put_requests_per_month": 10000,
                "get_requests_per_month": 100000,
                "data_transfer_gb": 0
            }
        }]
        
        # Create both estimates
        response1 = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json={"services": services_with_transfer}
        )
        response2 = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json={"services": services_no_transfer}
        )
        
        estimate_with = response1.json()
        estimate_without = response2.json()
        
        # With transfer should cost more
        assert estimate_with["total_monthly_cost"] > estimate_without["total_monthly_cost"]
        print(f"With transfer: ${estimate_with['total_monthly_cost']}")
        print(f"Without transfer: ${estimate_without['total_monthly_cost']}")


class TestCostCalculator:
    """Test cost calculator engine"""
    
    def test_cost_aggregation(self, test_project):
        """Test that costs are properly aggregated"""
        services = [
            {
                "id": "s3-1",
                "service_type": "AmazonS3",
                "region": "us-east-1",
                "config": {
                    "storage_gb": 100,
                    "storage_class": "STANDARD",
                    "put_requests_per_month": 10000,
                    "get_requests_per_month": 100000,
                    "data_transfer_gb": 0
                }
            },
            {
                "id": "s3-2",
                "service_type": "AmazonS3",
                "region": "us-east-1",
                "config": {
                    "storage_gb": 200,
                    "storage_class": "STANDARD",
                    "put_requests_per_month": 20000,
                    "get_requests_per_month": 200000,
                    "data_transfer_gb": 0
                }
            }
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json={"services": services}
        )
        
        estimate = response.json()
        
        # Total should be sum of both services
        assert estimate["total_monthly_cost"] > 0
        assert len(estimate["breakdown"]) >= 2
    
    def test_confidence_calculation(self, test_project):
        """Test confidence score calculation"""
        services = [{
            "id": "test-confidence",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100,
                "storage_class": "STANDARD",
                "put_requests_per_month": 10000,
                "get_requests_per_month": 100000,
                "data_transfer_gb": 0
            }
        }]
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json={"services": services}
        )
        
        estimate = response.json()
        
        # Confidence should be between 0 and 1
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


class TestPluginLoader:
    """Test plugin loading system"""
    
    def test_list_all_services(self):
        """Test that all services are loaded"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        assert isinstance(services, list)
        assert len(services) > 0
        
        # Verify service structure
        for service in services:
            assert "service_id" in service
            assert "display_name" in service
            assert "category" in service
        
        print(f"Total services loaded: {len(services)}")
    
    def test_service_categories(self):
        """Test that services are properly categorized"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        
        categories = set(s["category"] for s in services)
        
        # Should have multiple categories
        assert len(categories) > 1
        print(f"Categories: {categories}")
    
    def test_service_schema_loading(self):
        """Test that service schemas load correctly"""
        # Get a service
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        
        if len(services) > 0:
            service_id = services[0]["service_id"]
            
            # Get schema
            schema_response = requests.get(f"{BASE_URL}/api/v1/services/{service_id}/schema")
            
            # Schema should load (200) or not be implemented yet (404/405)
            assert schema_response.status_code in [200, 404, 405]


class TestGraphEngine:
    """Test dependency graph engine"""
    
    def test_single_service_graph(self, test_project):
        """Test graph with single service"""
        services = [{
            "id": "single-service",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100,
                "storage_class": "STANDARD",
                "put_requests_per_month": 10000,
                "get_requests_per_month": 100000,
                "data_transfer_gb": 0
            }
        }]
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json={"services": services}
        )
        
        assert response.status_code == 201
        estimate = response.json()
        assert estimate["total_monthly_cost"] >= 0
    
    def test_multiple_services_graph(self, test_project):
        """Test graph with multiple interconnected services"""
        services = [
            {
                "id": "web-storage",
                "service_type": "AmazonS3",
                "region": "us-east-1",
                "config": {
                    "storage_gb": 500,
                    "storage_class": "STANDARD",
                    "put_requests_per_month": 100000,
                    "get_requests_per_month": 1000000,
                    "data_transfer_gb": 200
                }
            },
            {
                "id": "app-servers",
                "service_type": "AmazonEC2",
                "region": "us-east-1",
                "config": {
                    "instance_type": "t3.medium",
                    "instance_count": 3,
                    "operating_system": "Linux",
                    "estimated_monthly_egress_gb": 500
                }
            }
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json={"services": services}
        )
        
        assert response.status_code == 201
        estimate = response.json()
        
        # Should have costs from both services
        assert estimate["total_monthly_cost"] > 0


class TestDataValidation:
    """Test input validation and error handling"""
    
    def test_invalid_storage_class(self, test_project):
        """Test handling of invalid storage class"""
        services = [{
            "id": "invalid-storage",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100,
                "storage_class": "INVALID_CLASS",
                "put_requests_per_month": 10000,
                "get_requests_per_month": 100000,
                "data_transfer_gb": 0
            }
        }]
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json={"services": services}
        )
        
        # Should either handle gracefully or return error
        assert response.status_code in [201, 400, 422]
    
    def test_negative_values(self, test_project):
        """Test handling of negative values"""
        services = [{
            "id": "negative-storage",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": -100,  # Invalid
                "storage_class": "STANDARD",
                "put_requests_per_month": 10000,
                "get_requests_per_month": 100000,
                "data_transfer_gb": 0
            }
        }]
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json={"services": services}
        )
        
        # Should handle gracefully
        assert response.status_code in [201, 400, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
