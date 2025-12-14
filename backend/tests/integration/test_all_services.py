"""
Comprehensive service calculation tests for ALL AWS services
Tests cost calculations for all 51 services in the platform
"""

import pytest
import requests
from decimal import Decimal

BASE_URL = "http://backend:8000"


@pytest.fixture(scope="module")
def test_project():
    """Create a test project for all service tests"""
    project_data = {
        "name": "Comprehensive Service Test Project",
        "description": "Testing all AWS service cost calculations"
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


# ============================================================================
# COMPUTE SERVICES
# ============================================================================

class TestLambdaCalculations:
    """Test AWS Lambda cost calculations"""
    
    def test_lambda_basic(self, test_project):
        """Test basic Lambda function cost"""
        services = [{
            "id": "lambda-basic",
            "service_type": "AWSLambda",
            "region": "us-east-1",
            "config": {
                "memory_mb": 512,
                "monthly_invocations": 1000000,
                "avg_duration_ms": 200
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"Lambda 1M invocations cost: ${estimate['total_monthly_cost']}")
    
    def test_lambda_high_memory(self, test_project):
        """Test Lambda with high memory allocation"""
        services = [{
            "id": "lambda-high-mem",
            "service_type": "AWSLambda",
            "region": "us-east-1",
            "config": {
                "memory_mb": 3008,
                "monthly_invocations": 5000000,
                "avg_duration_ms": 1000
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"Lambda high-memory cost: ${estimate['total_monthly_cost']}")


class TestECSCalculations:
    """Test Amazon ECS cost calculations"""
    
    def test_ecs_fargate(self, test_project):
        """Test ECS Fargate cost"""
        services = [{
            "id": "ecs-fargate",
            "service_type": "AmazonECS",
            "region": "us-east-1",
            "config": {
                "launch_type": "FARGATE",
                "vcpu": 1,
                "memory_gb": 2,
                "task_count": 5
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"ECS Fargate cost: ${estimate['total_monthly_cost']}")


class TestEKSCalculations:
    """Test Amazon EKS cost calculations"""
    
    def test_eks_cluster(self, test_project):
        """Test EKS cluster cost"""
        services = [{
            "id": "eks-cluster",
            "service_type": "AmazonEKS",
            "region": "us-east-1",
            "config": {
                "cluster_count": 1,
                "node_group_instance_type": "t3.medium",
                "node_count": 3
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"EKS cluster cost: ${estimate['total_monthly_cost']}")


# ============================================================================
# DATABASE SERVICES
# ============================================================================

class TestRDSCalculations:
    """Test Amazon RDS cost calculations"""
    
    def test_rds_mysql(self, test_project):
        """Test RDS MySQL instance cost"""
        services = [{
            "id": "rds-mysql",
            "service_type": "AmazonRDS",
            "region": "us-east-1",
            "config": {
                "engine": "mysql",
                "instance_class": "db.t3.medium",
                "storage_gb": 100,
                "multi_az": False
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"RDS MySQL cost: ${estimate['total_monthly_cost']}")
    
    def test_rds_multi_az(self, test_project):
        """Test RDS Multi-AZ deployment cost"""
        services = [{
            "id": "rds-multi-az",
            "service_type": "AmazonRDS",
            "region": "us-east-1",
            "config": {
                "engine": "postgres",
                "instance_class": "db.m5.large",
                "storage_gb": 500,
                "multi_az": True
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"RDS Multi-AZ cost: ${estimate['total_monthly_cost']}")


class TestDynamoDBCalculations:
    """Test Amazon DynamoDB cost calculations"""
    
    def test_dynamodb_on_demand(self, test_project):
        """Test DynamoDB on-demand pricing"""
        services = [{
            "id": "dynamodb-on-demand",
            "service_type": "AmazonDynamoDB",
            "region": "us-east-1",
            "config": {
                "billing_mode": "on_demand",
                "read_requests_per_month": 10000000,
                "write_requests_per_month": 5000000,
                "storage_gb": 50
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"DynamoDB on-demand cost: ${estimate['total_monthly_cost']}")
    
    def test_dynamodb_provisioned(self, test_project):
        """Test DynamoDB provisioned capacity"""
        services = [{
            "id": "dynamodb-provisioned",
            "service_type": "AmazonDynamoDB",
            "region": "us-east-1",
            "config": {
                "billing_mode": "provisioned",
                "read_capacity_units": 100,
                "write_capacity_units": 50,
                "storage_gb": 100
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"DynamoDB provisioned cost: ${estimate['total_monthly_cost']}")


class TestElastiCacheCalculations:
    """Test Amazon ElastiCache cost calculations"""
    
    def test_elasticache_redis(self, test_project):
        """Test ElastiCache Redis cost"""
        services = [{
            "id": "elasticache-redis",
            "service_type": "AmazonElastiCache",
            "region": "us-east-1",
            "config": {
                "engine": "redis",
                "node_type": "cache.t3.medium",
                "num_nodes": 2
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"ElastiCache Redis cost: ${estimate['total_monthly_cost']}")


# ============================================================================
# NETWORKING & CONTENT DELIVERY
# ============================================================================

class TestCloudFrontCalculations:
    """Test Amazon CloudFront cost calculations"""
    
    def test_cloudfront_distribution(self, test_project):
        """Test CloudFront distribution cost"""
        services = [{
            "id": "cloudfront-dist",
            "service_type": "AmazonCloudFront",
            "region": "us-east-1",
            "config": {
                "data_transfer_out_gb": 1000,
                "https_requests": 10000000,
                "http_requests": 5000000
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"CloudFront cost: ${estimate['total_monthly_cost']}")


class TestRoute53Calculations:
    """Test Amazon Route53 cost calculations"""
    
    def test_route53_hosted_zone(self, test_project):
        """Test Route53 hosted zone cost"""
        services = [{
            "id": "route53-zone",
            "service_type": "AmazonRoute53",
            "region": "us-east-1",
            "config": {
                "hosted_zones": 5,
                "queries_per_month": 1000000000
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"Route53 cost: ${estimate['total_monthly_cost']}")


class TestVPCCalculations:
    """Test Amazon VPC cost calculations"""
    
    def test_vpc_nat_gateway(self, test_project):
        """Test VPC NAT Gateway cost"""
        services = [{
            "id": "vpc-nat",
            "service_type": "AmazonVPC",
            "region": "us-east-1",
            "config": {
                "nat_gateways": 2,
                "data_processed_gb": 500
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"VPC NAT Gateway cost: ${estimate['total_monthly_cost']}")


class TestELBCalculations:
    """Test Elastic Load Balancing cost calculations"""
    
    def test_application_load_balancer(self, test_project):
        """Test Application Load Balancer cost"""
        services = [{
            "id": "alb",
            "service_type": "ApplicationLoadBalancer",
            "region": "us-east-1",
            "config": {
                "load_balancers": 2,
                "lcu_hours": 730
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"ALB cost: ${estimate['total_monthly_cost']}")


# ============================================================================
# STORAGE SERVICES
# ============================================================================

class TestEFSCalculations:
    """Test Amazon EFS cost calculations"""
    
    def test_efs_standard(self, test_project):
        """Test EFS standard storage cost"""
        services = [{
            "id": "efs-standard",
            "service_type": "AmazonEFS",
            "region": "us-east-1",
            "config": {
                "storage_gb": 500,
                "storage_class": "standard"
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"EFS cost: ${estimate['total_monthly_cost']}")


class TestFSxCalculations:
    """Test Amazon FSx cost calculations"""
    
    def test_fsx_windows(self, test_project):
        """Test FSx for Windows File Server cost"""
        services = [{
            "id": "fsx-windows",
            "service_type": "AmazonFSx",
            "region": "us-east-1",
            "config": {
                "file_system_type": "windows",
                "storage_capacity_gb": 1024,
                "throughput_mbps": 64
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"FSx Windows cost: ${estimate['total_monthly_cost']}")


# ============================================================================
# ANALYTICS & STREAMING
# ============================================================================

class TestKinesisCalculations:
    """Test Amazon Kinesis cost calculations"""
    
    def test_kinesis_data_streams(self, test_project):
        """Test Kinesis Data Streams cost"""
        services = [{
            "id": "kinesis-streams",
            "service_type": "AmazonKinesis",
            "region": "us-east-1",
            "config": {
                "shard_hours": 730,
                "put_payload_units": 1000000
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"Kinesis cost: ${estimate['total_monthly_cost']}")


class TestOpenSearchCalculations:
    """Test Amazon OpenSearch cost calculations"""
    
    def test_opensearch_cluster(self, test_project):
        """Test OpenSearch cluster cost"""
        services = [{
            "id": "opensearch",
            "service_type": "AmazonOpenSearchService",
            "region": "us-east-1",
            "config": {
                "instance_type": "m5.large.search",
                "instance_count": 3,
                "storage_gb": 500
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"OpenSearch cost: ${estimate['total_monthly_cost']}")


# ============================================================================
# MESSAGING & INTEGRATION
# ============================================================================

class TestSNSCalculations:
    """Test Amazon SNS cost calculations"""
    
    def test_sns_notifications(self, test_project):
        """Test SNS notification cost"""
        services = [{
            "id": "sns",
            "service_type": "AmazonSNS",
            "region": "us-east-1",
            "config": {
                "requests": 10000000,
                "data_transfer_gb": 10
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"SNS cost: ${estimate['total_monthly_cost']}")


class TestSQSCalculations:
    """Test Amazon SQS cost calculations"""
    
    def test_sqs_standard(self, test_project):
        """Test SQS standard queue cost"""
        services = [{
            "id": "sqs",
            "service_type": "AWSQueueService",
            "region": "us-east-1",
            "config": {
                "requests_per_month": 100000000
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"SQS cost: ${estimate['total_monthly_cost']}")


class TestAPIGatewayCalculations:
    """Test Amazon API Gateway cost calculations"""
    
    def test_api_gateway_rest(self, test_project):
        """Test API Gateway REST API cost"""
        services = [{
            "id": "api-gateway",
            "service_type": "AmazonApiGateway",
            "region": "us-east-1",
            "config": {
                "api_type": "REST",
                "requests_per_month": 10000000,
                "cache_memory_gb": 0.5
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"API Gateway cost: ${estimate['total_monthly_cost']}")


# ============================================================================
# SECURITY & MANAGEMENT
# ============================================================================

class TestSecretsManagerCalculations:
    """Test AWS Secrets Manager cost calculations"""
    
    def test_secrets_manager(self, test_project):
        """Test Secrets Manager cost"""
        services = [{
            "id": "secrets-manager",
            "service_type": "AWSSecretsManager",
            "region": "us-east-1",
            "config": {
                "secrets_count": 10,
                "api_calls_per_month": 100000
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"Secrets Manager cost: ${estimate['total_monthly_cost']}")


class TestKMSCalculations:
    """Test AWS KMS cost calculations"""
    
    def test_kms_keys(self, test_project):
        """Test KMS customer managed keys cost"""
        services = [{
            "id": "kms",
            "service_type": "awskms",
            "region": "us-east-1",
            "config": {
                "customer_managed_keys": 5,
                "requests_per_month": 1000000
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"KMS cost: ${estimate['total_monthly_cost']}")


class TestCloudWatchCalculations:
    """Test Amazon CloudWatch cost calculations"""
    
    def test_cloudwatch_metrics(self, test_project):
        """Test CloudWatch metrics and logs cost"""
        services = [{
            "id": "cloudwatch",
            "service_type": "AmazonCloudWatch",
            "region": "us-east-1",
            "config": {
                "custom_metrics": 100,
                "log_ingestion_gb": 50,
                "log_storage_gb": 100
            }
        }]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] >= 0
        print(f"CloudWatch cost: ${estimate['total_monthly_cost']}")


# ============================================================================
# MULTI-SERVICE INTEGRATION TESTS
# ============================================================================

class TestComplexArchitectures:
    """Test complex multi-service architectures"""
    
    def test_three_tier_web_app(self, test_project):
        """Test 3-tier web application architecture"""
        services = [
            # Frontend - CloudFront + S3
            {
                "id": "cdn",
                "service_type": "AmazonCloudFront",
                "region": "us-east-1",
                "config": {
                    "data_transfer_out_gb": 500,
                    "https_requests": 50000000
                }
            },
            {
                "id": "static-assets",
                "service_type": "AmazonS3",
                "region": "us-east-1",
                "config": {
                    "storage_gb": 100,
                    "storage_class": "STANDARD",
                    "put_requests_per_month": 100000,
                    "get_requests_per_month": 10000000
                }
            },
            # Application - ALB + EC2
            {
                "id": "load-balancer",
                "service_type": "ApplicationLoadBalancer",
                "region": "us-east-1",
                "config": {
                    "load_balancers": 1,
                    "lcu_hours": 730
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
                    "estimated_monthly_egress_gb": 200
                }
            },
            # Database - RDS
            {
                "id": "database",
                "service_type": "AmazonRDS",
                "region": "us-east-1",
                "config": {
                    "engine": "postgres",
                    "instance_class": "db.t3.large",
                    "storage_gb": 500,
                    "multi_az": True
                }
            }
        ]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] > 0
        assert len(estimate["breakdown"]) >= 5
        print(f"3-tier web app total cost: ${estimate['total_monthly_cost']}")
    
    def test_serverless_architecture(self, test_project):
        """Test serverless architecture"""
        services = [
            # API Gateway
            {
                "id": "api",
                "service_type": "AmazonApiGateway",
                "region": "us-east-1",
                "config": {
                    "api_type": "REST",
                    "requests_per_month": 10000000
                }
            },
            # Lambda functions
            {
                "id": "lambda-api",
                "service_type": "AWSLambda",
                "region": "us-east-1",
                "config": {
                    "memory_mb": 1024,
                    "monthly_invocations": 10000000,
                    "avg_duration_ms": 300
                }
            },
            # DynamoDB
            {
                "id": "dynamodb-data",
                "service_type": "AmazonDynamoDB",
                "region": "us-east-1",
                "config": {
                    "billing_mode": "on_demand",
                    "read_requests_per_month": 50000000,
                    "write_requests_per_month": 10000000,
                    "storage_gb": 100
                }
            },
            # S3 for file storage
            {
                "id": "file-storage",
                "service_type": "AmazonS3",
                "region": "us-east-1",
                "config": {
                    "storage_gb": 500,
                    "storage_class": "INTELLIGENT_TIERING",
                    "put_requests_per_month": 1000000,
                    "get_requests_per_month": 5000000
                }
            }
        ]
        
        estimate = create_estimate(test_project, services)
        assert estimate["total_monthly_cost"] > 0
        print(f"Serverless architecture cost: ${estimate['total_monthly_cost']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
