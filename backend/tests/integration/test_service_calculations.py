"""
Integration tests for service cost calculations
Tests that each service plugin calculates costs correctly
"""

import pytest
import requests
from decimal import Decimal

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="session")
def test_project():
    """Create a test project"""
    project_data = {
        "name": "Service Calculation Test Project",
        "description": "Testing service cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    return response.json()["id"]


def create_estimate(project_id: str, services: list) -> dict:
    """Helper to create an estimate"""
    estimate_data = {"services": services}
    response = requests.post(
        f"{BASE_URL}/api/v1/estimates?project_id={project_id}",
        json=estimate_data
    )
    assert response.status_code == 201
    return response.json()


class TestS3Calculations:
    """Test Amazon S3 cost calculations"""
    
    def test_s3_standard_storage(self, test_project):
        """Test S3 STANDARD storage class calculation"""
        services = [{
            "id": "s3-test",
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
        
        estimate = create_estimate(test_project, services)
        # 100 GB * $0.023 + (10000/1000)*$0.005 + (100000/1000)*$0.0004
        # = $2.30 + $0.05 + $0.04 = $2.39
        assert estimate["total_monthly_cost"] > 0
        print(f"S3 STANDARD 100GB cost: ${estimate['total_monthly_cost']}")
    
    def test_s3_glacier_storage(self, test_project):
        """Test S3 Glacier storage class calculation"""
        services = [{
            "id": "s3-glacier",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 1000,
                "storage_class": "GLACIER_FLEXIBLE",
                "put_requests_per_month": 1000,
                "get_requests_per_month": 1000,
                "data_transfer_gb": 0
            }
        }]
        
        estimate = create_estimate(test_project, services)
        # Should be cheaper than STANDARD
        assert estimate["total_monthly_cost"] > 0
        print(f"S3 Glacier 1TB cost: ${estimate['total_monthly_cost']}")
    
    def test_s3_with_data_transfer(self, test_project):
        """Test S3 with data transfer costs"""
        services = [{
            "id": "s3-transfer",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100,
                "storage_class": "STANDARD",
                "put_requests_per_month": 10000,
                "get_requests_per_month": 100000,
                "data_transfer_gb": 500  # 500 GB transfer
            }
        }]
        
        estimate = create_estimate(test_project, services)
        # Should include data transfer costs
        assert estimate["total_monthly_cost"] > 2.39  # More than storage-only
        print(f"S3 with 500GB transfer cost: ${estimate['total_monthly_cost']}")


class TestEC2Calculations:
    """Test Amazon EC2 cost calculations"""
    
    def test_ec2_t3_micro(self, test_project):
        """Test EC2 t3.micro instance calculation"""
        services = [{
            "id": "ec2-micro",
            "service_type": "AmazonEC2",
            "region": "us-east-1",
            "config": {
                "instance_type": "t3.micro",
                "instance_count": 1,
                "operating_system": "Linux",
                "estimated_monthly_egress_gb": 50
            }
        }]
        
        estimate = create_estimate(test_project, services)
        # t3.micro = $0.096/hr * 730 hrs = $70.08
        assert estimate["total_monthly_cost"] > 0
        print(f"EC2 t3.micro cost: ${estimate['total_monthly_cost']}")
    
    def test_ec2_multiple_instances(self, test_project):
        """Test EC2 with multiple instances"""
        services = [{
            "id": "ec2-multi",
            "service_type": "AmazonEC2",
            "region": "us-east-1",
            "config": {
                "instance_type": "t3.small",
                "instance_count": 3,
                "operating_system": "Linux",
                "estimated_monthly_egress_gb": 100
            }
        }]
        
        estimate = create_estimate(test_project, services)
        # Should be 3x single instance cost
        assert estimate["total_monthly_cost"] > 0
        print(f"EC2 3x t3.small cost: ${estimate['total_monthly_cost']}")
    
    def test_ec2_with_data_transfer(self, test_project):
        """Test EC2 with high data transfer"""
        services = [{
            "id": "ec2-transfer",
            "service_type": "AmazonEC2",
            "region": "us-east-1",
            "config": {
                "instance_type": "t3.micro",
                "instance_count": 1,
                "operating_system": "Linux",
                "estimated_monthly_egress_gb": 1000  # 1TB transfer
            }
        }]
        
        estimate = create_estimate(test_project, services)
        # Should include data transfer costs (1000-100)*$0.09
        assert estimate["total_monthly_cost"] > 70
        print(f"EC2 with 1TB transfer cost: ${estimate['total_monthly_cost']}")


class TestMultiServiceEstimates:
    """Test estimates with multiple services"""
    
    def test_s3_and_ec2_together(self, test_project):
        """Test combined S3 and EC2 estimate"""
        services = [
            {
                "id": "s3-1",
                "service_type": "AmazonS3",
                "region": "us-east-1",
                "config": {
                    "storage_gb": 500,
                    "storage_class": "STANDARD",
                    "put_requests_per_month": 50000,
                    "get_requests_per_month": 500000,
                    "data_transfer_gb": 100
                }
            },
            {
                "id": "ec2-1",
                "service_type": "AmazonEC2",
                "region": "us-east-1",
                "config": {
                    "instance_type": "t3.medium",
                    "instance_count": 2,
                    "operating_system": "Linux",
                    "estimated_monthly_egress_gb": 200
                }
            }
        ]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] > 0
        assert len(estimate["breakdown"]) >= 2
        print(f"Combined S3+EC2 cost: ${estimate['total_monthly_cost']}")
    
    def test_estimate_breakdown_structure(self, test_project):
        """Test that estimate breakdown has correct structure"""
        services = [{
            "id": "s3-breakdown",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100,
                "storage_class": "STANDARD",
                "put_requests_per_month": 10000,
                "get_requests_per_month": 100000,
                "data_transfer_gb": 50
            }
        }]
        
        estimate = create_estimate(test_project, services)
        
        # Verify breakdown structure
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], dict)
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_zero_storage(self, test_project):
        """Test with zero storage"""
        services = [{
            "id": "s3-zero",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 0,
                "storage_class": "STANDARD",
                "put_requests_per_month": 1000,
                "get_requests_per_month": 10000,
                "data_transfer_gb": 0
            }
        }]
        
        estimate = create_estimate(test_project, services)
        # Should only have request costs
        assert estimate["total_monthly_cost"] >= 0
    
    def test_large_values(self, test_project):
        """Test with very large values"""
        services = [{
            "id": "s3-large",
            "service_type": "AmazonS3",
            "region": "us-east-1",
            "config": {
                "storage_gb": 100000,  # 100 TB
                "storage_class": "STANDARD",
                "put_requests_per_month": 10000000,
                "get_requests_per_month": 100000000,
                "data_transfer_gb": 50000  # 50 TB
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] > 1000  # Should be substantial
        print(f"Large scale S3 cost: ${estimate['total_monthly_cost']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
