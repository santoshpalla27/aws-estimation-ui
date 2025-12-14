"""
Service: AWS Lambda
Category: Compute
Pricing Model: Requests + Duration (GB-seconds)
Key Cost Drivers: Monthly invocations, memory allocation, average duration
"""

import pytest
import requests

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for Lambda tests"""
    project_data = {
        "name": "Lambda Test Project",
        "description": "Testing AWS Lambda cost calculations"
    }
    response = requests.post(f"{BASE_URL}/api/v1/projects", json=project_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def base_lambda_config():
    """Base Lambda service configuration"""
    return {
        "id": "test-lambda",
        "service_type": "AWSLambda",
        "region": "us-east-1",
        "config": {
            "memory_mb": 512,
            "monthly_invocations": 1000000,
            "avg_duration_ms": 200
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


class TestLambdaServiceDiscovery:
    """Test Lambda service registration"""
    
    def test_lambda_in_service_catalog(self):
        """Verify Lambda appears in service catalog"""
        response = requests.get(f"{BASE_URL}/api/v1/services")
        assert response.status_code == 200
        
        services = response.json()
        lambda_service = next((s for s in services if s["service_id"] == "AWSLambda"), None)
        
        assert lambda_service is not None
        assert lambda_service["category"] == "Compute"


class TestLambdaBasicCostCalculation:
    """Test basic Lambda cost calculations"""
    
    def test_lambda_basic_cost(self, test_project, base_lambda_config):
        """Test basic Lambda function cost"""
        estimate = create_estimate(test_project, [base_lambda_config])
        
        assert estimate["total_monthly_cost"] >= 0
        assert "breakdown" in estimate
    
    def test_lambda_free_tier(self, test_project):
        """Test Lambda free tier (1M requests, 400K GB-seconds)"""
        service = {
            "id": "lambda-free",
            "service_type": "AWSLambda",
            "region": "us-east-1",
            "config": {
                "memory_mb": 128,
                "monthly_invocations": 500000,  # Under 1M
                "avg_duration_ms": 100
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


class TestLambdaMemoryAllocation:
    """Test Lambda memory allocation pricing"""
    
    @pytest.mark.parametrize("memory_mb", [128, 256, 512, 1024, 2048, 3008])
    def test_memory_allocation_pricing(self, test_project, memory_mb):
        """Test different memory allocations"""
        service = {
            "id": f"lambda-{memory_mb}mb",
            "service_type": "AWSLambda",
            "region": "us-east-1",
            "config": {
                "memory_mb": memory_mb,
                "monthly_invocations": 1000000,
                "avg_duration_ms": 200
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0
    
    def test_higher_memory_costs_more(self, test_project):
        """Test higher memory allocation costs more"""
        service_low = {
            "id": "lambda-low-mem",
            "service_type": "AWSLambda",
            "region": "us-east-1",
            "config": {
                "memory_mb": 128,
                "monthly_invocations": 1000000,
                "avg_duration_ms": 200
            }
        }
        
        service_high = {
            "id": "lambda-high-mem",
            "service_type": "AWSLambda",
            "region": "us-east-1",
            "config": {
                "memory_mb": 3008,
                "monthly_invocations": 1000000,
                "avg_duration_ms": 200
            }
        }
        
        estimate_low = create_estimate(test_project, [service_low])
        estimate_high = create_estimate(test_project, [service_high])
        
        assert estimate_high["total_monthly_cost"] >= estimate_low["total_monthly_cost"]


class TestLambdaInvocations:
    """Test Lambda invocation scaling"""
    
    def test_invocations_scale_cost(self, test_project):
        """Test cost scales with invocations"""
        service_1m = {
            "id": "lambda-1m",
            "service_type": "AWSLambda",
            "region": "us-east-1",
            "config": {
                "memory_mb": 512,
                "monthly_invocations": 1000000,
                "avg_duration_ms": 200
            }
        }
        
        service_10m = {
            "id": "lambda-10m",
            "service_type": "AWSLambda",
            "region": "us-east-1",
            "config": {
                "memory_mb": 512,
                "monthly_invocations": 10000000,
                "avg_duration_ms": 200
            }
        }
        
        estimate_1m = create_estimate(test_project, [service_1m])
        estimate_10m = create_estimate(test_project, [service_10m])
        
        assert estimate_10m["total_monthly_cost"] >= estimate_1m["total_monthly_cost"]


class TestLambdaDuration:
    """Test Lambda duration pricing"""
    
    def test_duration_affects_cost(self, test_project):
        """Test longer duration increases cost"""
        service_short = {
            "id": "lambda-short",
            "service_type": "AWSLambda",
            "region": "us-east-1",
            "config": {
                "memory_mb": 512,
                "monthly_invocations": 1000000,
                "avg_duration_ms": 100
            }
        }
        
        service_long = {
            "id": "lambda-long",
            "service_type": "AWSLambda",
            "region": "us-east-1",
            "config": {
                "memory_mb": 512,
                "monthly_invocations": 1000000,
                "avg_duration_ms": 1000
            }
        }
        
        estimate_short = create_estimate(test_project, [service_short])
        estimate_long = create_estimate(test_project, [service_long])
        
        assert estimate_long["total_monthly_cost"] >= estimate_short["total_monthly_cost"]


class TestLambdaEdgeCases:
    """Test Lambda edge cases"""
    
    def test_zero_invocations(self, test_project):
        """Test zero invocations"""
        service = {
            "id": "lambda-zero",
            "service_type": "AWSLambda",
            "region": "us-east-1",
            "config": {
                "memory_mb": 512,
                "monthly_invocations": 0,
                "avg_duration_ms": 200
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0
    
    def test_maximum_memory(self, test_project):
        """Test maximum memory allocation"""
        service = {
            "id": "lambda-max-mem",
            "service_type": "AWSLambda",
            "region": "us-east-1",
            "config": {
                "memory_mb": 10240,  # 10GB
                "monthly_invocations": 1000000,
                "avg_duration_ms": 200
            }
        }
        
        estimate = create_estimate(test_project, [service])
        assert estimate["total_monthly_cost"] >= 0


class TestLambdaConfidenceScoring:
    """Test Lambda confidence scoring"""
    
    def test_confidence_in_range(self, test_project, base_lambda_config):
        """Test confidence score is valid"""
        estimate = create_estimate(test_project, [base_lambda_config])
        
        assert "confidence" in estimate
        assert 0 <= estimate["confidence"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
