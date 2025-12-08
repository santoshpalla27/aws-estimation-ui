import boto3
import json
import os
import sys

# Output Directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")

# Comprehensive List from Downloader (for manifest generation)
SERVICE_CODES = [
    "AmazonEC2", "AmazonES", "ACM", "AmazonApiGateway", "AmazonCloudFront",
    "AmazonCloudWatch", "AWSCloudTrail", "AmazonDynamoDB", "AmazonECR",
    "AmazonECRPublic", "AmazonECS", "AmazonEFS", "AmazonEKS", "AmazonElastiCache",
    "AmazonMQ", "AmazonMSK", "AmazonRDS", "AmazonRoute53", "AmazonS3",
    "AmazonS3GlacierDeepArchive", "AmazonSNS", "AmazonStates", "AmazonVPC",
    "AWSCloudFormation", "AWSCodeArtifact", "CodeBuild", "AWSCodeCommit",
    "AWSCodeDeploy", "AWSCodePipeline", "AWSConfig", "AWSELB",
    "AWSElasticDisasterRecovery", "AWSEvents", "awskms", "AWSLambda",
    "AWSQueueService", "AWSSecretsManager", "AWSServiceCatalog", "AWSShield",
    "AWSSystemsManager", "AWSXRay", "awswaf", "AmazonSES", "AmazonPinpoint",
    "AmazonKinesis", "AmazonFSx", "AWSBackup", "AWSDataTransfer",
    "AWSGlobalAccelerator", "AWSFMS"
]

def save_json(data, filename):
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Saved {filename}")

def get_regions():
    print("Fetching Regions...")
    try:
        ec2 = boto3.client('ec2', region_name='us-east-1')
        regions = ec2.describe_regions()
        return [r['RegionName'] for r in regions['Regions']]
    except Exception as e:
        print(f"Error fetching regions: {e}")
        return ["us-east-1", "us-west-2", "eu-west-1"] 

def get_instance_types():
    print("Fetching EC2 Instance Types...")
    try:
        ec2 = boto3.client('ec2', region_name='us-east-1')
        paginator = ec2.get_paginator('describe_instance_types')
        items = []
        for page in paginator.paginate():
            for it in page['InstanceTypes']:
                items.append({
                    "type": it['InstanceType'],
                    "vcpus": it.get('VCpuInfo', {}).get('DefaultVCpus'),
                    "memory": it.get('MemoryInfo', {}).get('SizeInMiB', 0) / 1024,
                    "storage": it.get('InstanceStorageInfo', "EBS Only"),
                    "arch": it.get('ProcessorInfo', {}).get('SupportedArchitectures')
                })
        return items
    except Exception as e:
        print(f"Error fetching EC2 types: {e}")
        return []

def get_rds_engines():
    print("Fetching RDS Engines...")
    try:
        rds = boto3.client('rds', region_name='us-east-1')
        paginator = rds.get_paginator('describe_db_engine_versions')
        engines = {}
        for page in paginator.paginate():
            for engine in page['DBEngineVersions']:
                eng_name = engine['Engine']
                if eng_name not in engines:
                    engines[eng_name] = []
                engines[eng_name].append(engine['EngineVersion'])
        return engines
    except Exception as e:
        print(f"Error fetching RDS engines: {e}")
        return {}

def get_elasticache_types():
    print("Fetching ElastiCache Node Types...")
    try:
        # No direct 'describe_node_types', use 'describe_reserved_cache_nodes_offerings' 
        # or 'describe_orderable_cache_cluster_options'? Orderable is better.
        client = boto3.client('elasticache', region_name='us-east-1')
        paginator = client.get_paginator('describe_orderable_cache_cluster_options')
        types = set()
        for page in paginator.paginate():
            for item in page['OrderableCacheClusterOptions']:
                types.add(item['CacheNodeType'])
        return sorted(list(types))
    except Exception as e:
        print(f"Error fetching ElastiCache types: {e}")
        return []

def get_opensearch_types():
    print("Fetching OpenSearch Instance Types...")
    try:
        client = boto3.client('opensearch', region_name='us-east-1')
        # list_versions -> list_instance_types
        # Actually 'list_instance_type_details' is preferred if available 
        # or just hardcode/extract from valid versions
        # Let's try describe_instance_type_limits or list_versions
        versions = client.list_versions(MaxResults=1)['Versions']
        if not versions:
            return []
        ver = versions[0] # Latest
        # Need to know instance types supported.
        # usually parsing pricing is better. Boto3 support here is spotty for generating a catalog of ALL types.
        return [] 
    except Exception as e:
        print(f"Error fetching OpenSearch types (Skipping): {e}")
        return []

def main():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    # 0. Service List
    save_json(sorted(list(set(SERVICE_CODES))), "services_manifest.json")

    # 1. Regions
    regions = get_regions()
    save_json(regions, "regions.json")

    # 2. EC2 Metadata
    ec2_data = get_instance_types()
    if ec2_data:
        save_json(ec2_data, "ec2_metadata.json")

    # 3. RDS Metadata
    rds_data = get_rds_engines()
    if rds_data:
        save_json(rds_data, "rds_metadata.json")

    # 4. ElastiCache
    ec_data = get_elasticache_types()
    if ec_data:
        save_json(ec_data, "elasticache_metadata.json")

    print("\nMetadata Extraction Complete.")

if __name__ == "__main__":
    main()
