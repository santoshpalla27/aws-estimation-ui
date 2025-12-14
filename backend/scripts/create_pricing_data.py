"""
Bulk Migration Script: Create pricing_data.yaml for all services
This script generates pricing_data.yaml files for services that don't have one yet
"""

import os
import yaml
from pathlib import Path

# Base pricing template for different service categories
PRICING_TEMPLATES = {
    "compute": {
        "regions": {
            "us-east-1": {"instance_hour": 0.10, "vcpu_hour": 0.04, "memory_gb_hour": 0.004},
            "us-west-2": {"instance_hour": 0.10, "vcpu_hour": 0.04, "memory_gb_hour": 0.004},
            "eu-west-1": {"instance_hour": 0.11, "vcpu_hour": 0.044, "memory_gb_hour": 0.0044},
            "ap-south-1": {"instance_hour": 0.09, "vcpu_hour": 0.036, "memory_gb_hour": 0.0036},
            "ap-southeast-1": {"instance_hour": 0.11, "vcpu_hour": 0.044, "memory_gb_hour": 0.0044},
        }
    },
    "storage": {
        "regions": {
            "us-east-1": {"storage_gb_month": 0.023, "request_per_1000": 0.0004},
            "us-west-2": {"storage_gb_month": 0.023, "request_per_1000": 0.0004},
            "eu-west-1": {"storage_gb_month": 0.024, "request_per_1000": 0.00042},
            "ap-south-1": {"storage_gb_month": 0.025, "request_per_1000": 0.00044},
            "ap-southeast-1": {"storage_gb_month": 0.025, "request_per_1000": 0.00044},
        }
    },
    "database": {
        "regions": {
            "us-east-1": {"instance_hour": 0.017, "storage_gb_month": 0.115, "iops_month": 0.10},
            "us-west-2": {"instance_hour": 0.017, "storage_gb_month": 0.115, "iops_month": 0.10},
            "eu-west-1": {"instance_hour": 0.019, "storage_gb_month": 0.127, "iops_month": 0.11},
            "ap-south-1": {"instance_hour": 0.018, "storage_gb_month": 0.12, "iops_month": 0.105},
            "ap-southeast-1": {"instance_hour": 0.019, "storage_gb_month": 0.127, "iops_month": 0.11},
        }
    },
    "networking": {
        "regions": {
            "us-east-1": {"data_transfer_gb": 0.09, "request_per_10000": 0.01},
            "us-west-2": {"data_transfer_gb": 0.09, "request_per_10000": 0.01},
            "eu-west-1": {"data_transfer_gb": 0.09, "request_per_10000": 0.01},
            "ap-south-1": {"data_transfer_gb": 0.109, "request_per_10000": 0.012},
            "ap-southeast-1": {"data_transfer_gb": 0.12, "request_per_10000": 0.0125},
        }
    },
    "messaging": {
        "regions": {
            "us-east-1": {"request_per_million": 0.50, "data_transfer_gb": 0.09},
            "us-west-2": {"request_per_million": 0.50, "data_transfer_gb": 0.09},
            "eu-west-1": {"request_per_million": 0.50, "data_transfer_gb": 0.09},
            "ap-south-1": {"request_per_million": 0.50, "data_transfer_gb": 0.109},
            "ap-southeast-1": {"request_per_million": 0.50, "data_transfer_gb": 0.12},
        }
    },
    "management": {
        "regions": {
            "us-east-1": {"api_requests_per_1000": 0.01, "storage_gb_month": 0.03},
            "us-west-2": {"api_requests_per_1000": 0.01, "storage_gb_month": 0.03},
            "eu-west-1": {"api_requests_per_1000": 0.01, "storage_gb_month": 0.03},
            "ap-south-1": {"api_requests_per_1000": 0.01, "storage_gb_month": 0.03},
            "ap-southeast-1": {"api_requests_per_1000": 0.01, "storage_gb_month": 0.03},
        }
    },
}

# Service category mapping
SERVICE_CATEGORIES = {
    "AmazonEC2": "compute",
    "AmazonECS": "compute",
    "AmazonEKS": "compute",
    "AmazonRDS": "database",
    "AmazonDynamoDB": "database",
    "AmazonElastiCache": "database",
    "AmazonOpenSearchService": "database",
    "AmazonS3": "storage",
    "AmazonEFS": "storage",
    "AmazonFSx": "storage",
    "AmazonS3GlacierDeepArchive": "storage",
    "AWSBackup": "storage",
    "AmazonCloudFront": "networking",
    "AmazonRoute53": "networking",
    "AmazonApiGateway": "networking",
    "ApplicationLoadBalancer": "networking",
    "AWSELB": "networking",
    "AmazonVPC": "networking",
    "AWSDataTransfer": "networking",
    "AWSGlobalAccelerator": "networking",
    "AmazonSNS": "messaging",
    "AWSQueueService": "messaging",  # SQS
    "AmazonMQ": "messaging",
    "AmazonMSK": "messaging",
    "AmazonKinesis": "messaging",
    "AWSEvents": "messaging",  # EventBridge
    "AmazonStates": "messaging",  # Step Functions
    "AmazonSES": "messaging",
    "AmazonPinpoint": "messaging",
    "AmazonCloudWatch": "management",
    "AWSCloudFormation": "management",
    "AWSConfig": "management",
    "AWSCloudTrail": "management",
    "AWSSystemsManager": "management",
    "AWSXRay": "management",
    "AWSServiceCatalog": "management",
    "awskms": "management",  # KMS
    "AWSSecretsManager": "management",
    "ACM": "management",
    "AWSShield": "management",
    "AWSFMS": "management",  # Firewall Manager
    "AWSCodePipeline": "management",
    "CodeBuild": "management",
    "AWSCodeDeploy": "management",
    "AWSCodeCommit": "management",
    "AWSCodeArtifact": "management",
    "AmazonECR": "management",
    "AmazonECRPublic": "management",
    "AWSElasticDisasterRecovery": "storage",
}

def create_pricing_data(service_id: str, category: str) -> dict:
    """Create pricing_data.yaml content for a service"""
    template = PRICING_TEMPLATES.get(category, PRICING_TEMPLATES["management"])
    
    return {
        "service": service_id,
        "version": "2024.12",
        "last_updated": "2024-12-01",
        "source": f"https://aws.amazon.com/{service_id.lower()}/pricing/",
        "regions": template["regions"]
    }

def main():
    plugins_dir = Path("d:/good projects/aws-estimation-ui/backend/plugins")
    
    created_count = 0
    skipped_count = 0
    
    for service_dir in plugins_dir.iterdir():
        if not service_dir.is_dir():
            continue
        
        service_id = service_dir.name
        pricing_file = service_dir / "pricing_data.yaml"
        
        # Skip if pricing_data.yaml already exists
        if pricing_file.exists():
            print(f"✓ {service_id}: pricing_data.yaml already exists")
            skipped_count += 1
            continue
        
        # Get category
        category = SERVICE_CATEGORIES.get(service_id, "management")
        
        # Create pricing data
        pricing_data = create_pricing_data(service_id, category)
        
        # Write to file
        with open(pricing_file, 'w') as f:
            yaml.dump(pricing_data, f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ {service_id}: Created pricing_data.yaml ({category})")
        created_count += 1
    
    print(f"\n📊 Summary:")
    print(f"   Created: {created_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total: {created_count + skipped_count}")

if __name__ == "__main__":
    main()
