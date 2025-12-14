"""
Integration tests for API endpoints
Tests all REST API endpoints for correct responses and data
"""

import pytest
import requests
import time
from typing import Dict, Any

# Base URL for API
BASE_URL = "http://backend:8000"
MAX_RETRIES = 30
RETRY_DELAY = 2


@pytest.fixture(scope="session")
def wait_for_backend():
    """Wait for backend to be ready"""
    for i in range(MAX_RETRIES):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ Backend ready after {i+1} attempts")
                return
        except requests.exceptions.RequestException:
            if i < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise
    raise Exception("Backend failed to start")


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self, wait_for_backend):
        """Test /health endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestProjectsAPI:
    """Test projects CRUD operations"""
    
    def test_list_projects_empty(self, wait_for_backend):
        """Test listing projects when none exist"""
        response = requests.get(f"{BASE_URL}/api/v1/projects")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_project(self, wait_for_backend):
        """Test creating a new project"""
        project_data = {
            "name": "Test Project",
            "description": "Integration test project"
        }
        response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert "id" in data
        return data["id"]
    
    def test_get_project(self, wait_for_backend):
        """Test retrieving a specific project"""
        # Create project first
        project_id = self.test_create_project(wait_for_backend)
        
        # Get project
        response = requests.get(f"{BASE_URL}/api/v1/projects/{project_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == "Test Project"
    
    def test_update_project(self, wait_for_backend):
        """Test updating a project"""
        # Create project first
        project_id = self.test_create_project(wait_for_backend)
        
        # Update project
        update_data = {
            "name": "Updated Test Project",
            "description": "Updated description"
        }
        response = requests.put(f"{BASE_URL}/api/v1/projects/{project_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Test Project"
    
    def test_delete_project(self, wait_for_backend):
        """Test deleting a project"""
        # Create project first
        project_id = self.test_create_project(wait_for_backend)
        
        # Delete project
        response = requests.delete(f"{BASE_URL}/api/v1/projects/{project_id}")
        assert response.status_code == 204
        
        # Verify deletion
        response = requests.get(f"{BASE_URL}/api/v1/projects/{project_id}")
        assert response.status_code == 404


class TestServicesAPI:
    """Test services listing endpoint"""
    
    def test_list_services(self, wait_for_backend):
        """Test listing all available services"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        services = response.json()
        assert isinstance(services, list)
        assert len(services) > 0
        
        # Verify service structure
        service = services[0]
        assert "service_id" in service
        assert "display_name" in service
        assert "category" in service
    
    def test_get_service_schema(self, wait_for_backend):
        """Test getting UI schema for a service"""
        # Get services list first
        response = requests.get(f"{BASE_URL}/api/v1/services")
        services = response.json()
        service_id = services[0]["service_id"]
        
        # Get service schema
        response = requests.get(f"{BASE_URL}/api/v1/services/{service_id}/schema")
        assert response.status_code == 200
        schema = response.json()
        assert "properties" in schema or "type" in schema


class TestEstimatesAPI:
    """Test cost estimation endpoints"""
    
    @pytest.fixture
    def test_project(self, wait_for_backend):
        """Create a test project for estimates"""
        project_data = {
            "name": "Estimate Test Project",
            "description": "Project for testing estimates"
        }
        response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
        return response.json()["id"]
    
    def test_create_estimate_single_service(self, wait_for_backend, test_project):
        """Test creating estimate with single service"""
        estimate_data = {
            "services": [
                {
                    "id": "service-1",
                    "service_type": "AmazonS3",
                    "region": "us-east-1",
                    "config": {
                        "storage_gb": 100,
                        "storage_class": "STANDARD",
                        "put_requests_per_month": 10000,
                        "get_requests_per_month": 100000,
                        "data_transfer_gb": 50
                    }
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json=estimate_data
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "total_monthly_cost" in data
        assert "breakdown" in data
    
    def test_create_estimate_multiple_services(self, wait_for_backend, test_project):
        """Test creating estimate with multiple services"""
        estimate_data = {
            "services": [
                {
                    "id": "s3-1",
                    "service_type": "AmazonS3",
                    "region": "us-east-1",
                    "config": {
                        "storage_gb": 100,
                        "storage_class": "STANDARD",
                        "put_requests_per_month": 10000,
                        "get_requests_per_month": 100000
                    }
                },
                {
                    "id": "ec2-1",
                    "service_type": "AmazonEC2",
                    "region": "us-east-1",
                    "config": {
                        "instance_type": "t3.micro",
                        "instance_count": 2,
                        "operating_system": "Linux",
                        "estimated_monthly_egress_gb": 200
                    }
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json=estimate_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["total_monthly_cost"] >= 0
        assert len(data["breakdown"]) > 0
    
    def test_list_estimates(self, wait_for_backend, test_project):
        """Test listing estimates for a project"""
        # Create an estimate first
        self.test_create_estimate_single_service(wait_for_backend, test_project)
        
        # List estimates
        response = requests.get(f"{BASE_URL}/api/v1/estimates?project_id={test_project}")
        assert response.status_code == 200
        estimates = response.json()
        assert isinstance(estimates, list)
        assert len(estimates) > 0
    
    def test_get_estimate(self, wait_for_backend, test_project):
        """Test retrieving a specific estimate"""
        # Create estimate first
        estimate_data = {
            "services": [
                {
                    "id": "service-1",
                    "service_type": "AmazonS3",
                    "region": "us-east-1",
                    "config": {
                        "storage_gb": 100,
                        "storage_class": "STANDARD",
                        "put_requests_per_month": 10000,
                        "get_requests_per_month": 100000
                    }
                }
            ]
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json=estimate_data
        )
        estimate_id = create_response.json()["id"]
        
        # Get estimate
        response = requests.get(f"{BASE_URL}/api/v1/estimates/{estimate_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == estimate_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
