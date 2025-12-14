"""
Service: Amazon EC2
Category: Compute
Pricing Model: Instance hours + EBS storage + Data transfer
Key Cost Drivers: Instance type, instance count, hours, EBS volumes, data transfer
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for EC2 tests"""
    project_data = {
        "name": "EC2 Test Project",
        "description": "Testing Amazon EC2 cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_ec2_config():
    """Base EC2 service configuration"""
    return {
        "id": "test-ec2",
        "service_type": "AmazonEC2",
        "region": "us-east-1",
        "config": {
            "instance_type": "t3.micro",
            "instance_count": 1,
            "operating_system": "Linux",
            "estimated_monthly_egress_gb": 100
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


class TestEC2ServiceDiscovery:
    """Test EC2 service registration and metadata"""
    
    def test_ec2_in_service_catalog(self):
        """Verify EC2 appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        ec2_service = next((s for s in services if s["service_id"] == "AmazonEC2"), None)
        
        assert ec2_service is not None
        assert ec2_service["display_name"] == "Amazon EC2"
        assert ec2_service["category"] == "Compute"


class TestEC2BasicCostCalculation:
    """Test basic EC2 cost calculations"""
    
    def test_ec2_t3_micro_cost(self, test_project, base_ec2_config):
        """Test t3.micro instance cost"""
        estimate = create_estimate(test_project, [base_ec2_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
        assert isinstance(estimate["breakdown"], list)
    
    def test_ec2_cost_deterministic(self, test_project, base_ec2_config):
        """Test EC2 cost calculation is deterministic"""
        estimate1 = create_estimate(test_project, [base_ec2_config])
        estimate2 = create_estimate(test_project, [base_ec2_config])
        
        assert estimate1["total_monthly_cost"] == estimate2["total_monthly_cost"]


class TestEC2InstanceTypes:
    """Test different EC2 instance types"""
    
    @pytest.mark.parametrize("instance_type", [
        "t3.micro", "t3.small", "t3.medium", "t3.large",
        "m5.large", "m5.xlarge", "c5.large"
    ])
    def test_instance_type_pricing(self, test_project, instance_type):
        """Test different instance type pricing"""
        service = {
            "id": f"ec2-{instance_type}",
            "service_type": "AmazonEC2",
            "region": "us-east-1",
            "config": {
                "instance_type": instance_type,
                "instance_count": 1,
                "operating_system": "Linux",
                "estimated_monthly_egress_gb": 0
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


class TestEC2Scaling:
    """Test EC2 instance scaling"""
    
    def test_multiple_instances_scale_linearly(self, test_project):
        """Test cost scales with instance count"""
        service_1 = {
            "id": "ec2-single",
            "service_type": "AmazonEC2",
            "region": "us-east-1",
            "config": {
                "instance_type": "t3.medium",
                "instance_count": 1,
                "operating_system": "Linux",
                "estimated_monthly_egress_gb": 0
            }
        }
        
        service_3 = {
            "id": "ec2-triple",
            "service_type": "AmazonEC2",
            "region": "us-east-1",
            "config": {
                "instance_type": "t3.medium",
                "instance_count": 3,
                "operating_system": "Linux",
                "estimated_monthly_egress_gb": 0
            }
        }
        
        estimate_1 = create_estimate(test_project, [service_1])
        estimate_3 = create_estimate(test_project, [service_3])
        
        # 3 instances should cost approximately 3x more
        if estimate_1["total_monthly_cost"] > 0:
            ratio = estimate_3["total_monthly_cost"] / estimate_1["total_monthly_cost"]
            assert 2.5 <= ratio <= 3.5


class TestEC2DataTransfer:
    """Test EC2 data transfer pricing"""
    
    def test_data_transfer_cost(self, test_project):
        """Test data transfer adds to cost"""
        service_no_transfer = {
            "id": "ec2-no-transfer",
            "service_type": "AmazonEC2",
            "region": "us-east-1",
            "config": {
                "instance_type": "t3.micro",
                "instance_count": 1,
                "operating_system": "Linux",
                "estimated_monthly_egress_gb": 0
            }
        }
        
        service_with_transfer = {
            "id": "ec2-with-transfer",
            "service_type": "AmazonEC2",
            "region": "us-east-1",
            "config": {
                "instance_type": "t3.micro",
                "instance_count": 1,
                "operating_system": "Linux",
                "estimated_monthly_egress_gb": 1000
            }
        }
        
        estimate_no_transfer = create_estimate(test_project, [service_no_transfer])
        estimate_with_transfer = create_estimate(test_project, [service_with_transfer])
        
        assert estimate_with_transfer["total_monthly_cost"] >= estimate_no_transfer["total_monthly_cost"]


class TestEC2EdgeCases:
    """Test EC2 edge cases"""
    
    def test_zero_instances(self, test_project):
        """Test zero instances"""
        service = {
            "id": "ec2-zero",
            "service_type": "AmazonEC2",
            "region": "us-east-1",
            "config": {
                "instance_type": "t3.micro",
                "instance_count": 0,
                "operating_system": "Linux",
                "estimated_monthly_egress_gb": 0
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/estimates?project_id={test_project}",
            json={"services": [service]}
        )
        assert response.status_code in [201, 400, 422]
    
    def test_maximum_instances(self, test_project):
        """Test large number of instances"""
        service = {
            "id": "ec2-max",
            "service_type": "AmazonEC2",
            "region": "us-east-1",
            "config": {
                "instance_type": "t3.micro",
                "instance_count": 1000,
                "operating_system": "Linux",
                "estimated_monthly_egress_gb": 0
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] > 0


class TestEC2ConfidenceScoring:
    """Test EC2 confidence scoring"""
    
    def test_confidence_in_range(self, test_project, base_ec2_config):
        """Test confidence score is valid"""
        estimate = create_estimate(test_project, [base_ec2_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
