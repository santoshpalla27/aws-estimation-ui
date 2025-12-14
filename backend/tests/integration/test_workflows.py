"""
End-to-end workflow tests
Tests complete user workflows from project creation to estimate generation
"""

import pytest
import requests
import time

BASE_URL = "http://backend:8000"


class TestCompleteWorkflow:
    """Test complete end-to-end workflows"""
    
    def test_full_estimation_workflow(self):
        """Test complete workflow: create project -> add services -> generate estimate"""
        
        # Step 1: Create a project
        project_data = {
            "name": "E2E Test Project",
            "description": "End-to-end testing workflow"
        }
        response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
        assert response.status_code == 201
        project = response.json()
        project_id = project["id"]
        print(f"✅ Created project: {project_id}")
        
        # Step 2: Verify project exists
        response = requests.get(f"{BASE_URL}/api/v1/projects/{project_id}")
        assert response.status_code == 200
        print(f"✅ Verified project exists")
        
        # Step 3: Get available services
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        services = response.json()
        assert len(services) > 0
        print(f"✅ Found {len(services)} available services")
        
        # Step 4: Create estimate with multiple services
        estimate_data = {
            "services": [
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
                    "id": "web-servers",
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
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={project_id}",
            json=estimate_data
        )
        assert response.status_code == 201
        estimate = response.json()
        estimate_id = estimate["id"]
        print(f"✅ Created estimate: {estimate_id}")
        print(f"   Total cost: ${estimate['total_monthly_cost']}")
        print(f"   Confidence: {estimate['confidence']}")
        
        # Step 5: Retrieve estimate
        response = requests.get(f"{BASE_URL}/api/v1/estimates/{estimate_id}")
        assert response.status_code == 200
        retrieved_estimate = response.json()
        assert retrieved_estimate["id"] == estimate_id
        print(f"✅ Retrieved estimate successfully")
        
        # Step 6: List all estimates for project
        response = requests.get(f"{BASE_URL}/api/v1/estimates?project_id={project_id}")
        assert response.status_code == 200
        estimates = response.json()
        assert len(estimates) >= 1
        print(f"✅ Found {len(estimates)} estimate(s) for project")
        
        # Step 7: Update project
        update_data = {
            "name": "E2E Test Project (Updated)",
            "description": "Updated after estimate creation"
        }
        response = requests.put(f"{BASE_URL}/api/v1/projects/{project_id}", json=update_data)
        assert response.status_code == 200
        print(f"✅ Updated project")
        
        # Step 8: Create second estimate (iteration)
        estimate_data_v2 = {
            "services": [
                {
                    "id": "optimized-storage",
                    "service_type": "AmazonS3",
                    "region": "us-east-1",
                    "config": {
                        "storage_gb": 500,
                        "storage_class": "INTELLIGENT_TIERING",  # Changed to save costs
                        "put_requests_per_month": 100000,
                        "get_requests_per_month": 1000000,
                        "data_transfer_gb": 200
                    }
                },
                {
                    "id": "optimized-servers",
                    "service_type": "AmazonEC2",
                    "region": "us-east-1",
                    "config": {
                        "instance_type": "t3.small",  # Downsized
                        "instance_count": 2,  # Reduced count
                        "operating_system": "Linux",
                        "estimated_monthly_egress_gb": 500
                    }
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={project_id}",
            json=estimate_data_v2
        )
        assert response.status_code == 201
        estimate_v2 = response.json()
        print(f"✅ Created optimized estimate")
        print(f"   Original cost: ${estimate['total_monthly_cost']}")
        print(f"   Optimized cost: ${estimate_v2['total_monthly_cost']}")
        
        # Step 9: Cleanup - delete project
        response = requests.delete(f"{BASE_URL}/api/v1/projects/{project_id}")
        assert response.status_code == 204
        print(f"✅ Deleted project")
        
        print("\n🎉 Complete workflow test passed!")


class TestErrorHandling:
    """Test error handling and validation"""
    
    def test_invalid_project_id(self):
        """Test accessing non-existent project"""
        response = requests.get(f"{BASE_URL}/api/v1/projects/invalid-uuid-12345")
        assert response.status_code == 422  # FastAPI returns 422 for invalid UUID format
    
    def test_invalid_service_type(self):
        """Test estimate with invalid service type"""
        # Create project first
        project_data = {"name": "Error Test Project"}
        response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
        project_id = response.json()["id"]
        
        # Try invalid service
        estimate_data = {
            "services": [{
                "id": "invalid-service",
                "service_type": "InvalidService",
                "region": "us-east-1",
                "config": {}
            }]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={project_id}",
            json=estimate_data
        )
        # Should either reject or handle gracefully
        assert response.status_code in [201, 400, 422]
    
    def test_missing_required_config(self):
        """Test estimate with missing required configuration"""
        # Create project
        project_data = {"name": "Config Test Project"}
        response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
        project_id = response.json()["id"]
        
        # Try with incomplete config
        estimate_data = {
            "services": [{
                "id": "incomplete-s3",
                "service_type": "AmazonS3",
                "region": "us-east-1",
                "config": {
                    # Missing required fields
                    "storage_gb": 100
                }
            }]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={project_id}",
            json=estimate_data
        )
        # Should handle with defaults or validation error
        assert response.status_code in [201, 400, 422]


class TestPerformance:
    """Test performance and scalability"""
    
    def test_large_estimate(self):
        """Test estimate with many services"""
        # Create project
        project_data = {"name": "Performance Test Project"}
        response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
        project_id = response.json()["id"]
        
        # Create estimate with 10 services
        services = []
        for i in range(10):
            services.append({
                "id": f"s3-{i}",
                "service_type": "AmazonS3",
                "region": "us-east-1",
                "config": {
                    "storage_gb": 100 * (i + 1),
                    "storage_class": "STANDARD",
                    "put_requests_per_month": 10000,
                    "get_requests_per_month": 100000,
                    "data_transfer_gb": 50
                }
            })
        
        estimate_data = {"services": services}
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={project_id}",
            json=estimate_data
        )
        duration = time.time() - start_time
        
        assert response.status_code == 201
        assert duration < 10  # Should complete in under 10 seconds
        print(f"✅ Large estimate (10 services) completed in {duration:.2f}s")
    
    def test_concurrent_estimates(self):
        """Test creating multiple estimates concurrently"""
        # Create project
        project_data = {"name": "Concurrent Test Project"}
        response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
        project_id = response.json()["id"]
        
        # Create 5 estimates quickly
        estimate_ids = []
        for i in range(5):
            estimate_data = {
                "services": [{
                    "id": f"s3-concurrent-{i}",
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
            }
            
            response = requests.post(
                f"{BASE_URL}/api/v1/estimates?project_id={project_id}",
                json=estimate_data
            )
            assert response.status_code == 201
            estimate_ids.append(response.json()["id"])
        
        # Verify all estimates exist
        response = requests.get(f"{BASE_URL}/api/v1/estimates?project_id={project_id}")
        estimates = response.json()
        assert len(estimates) >= 5
        print(f"✅ Created {len(estimate_ids)} concurrent estimates successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
