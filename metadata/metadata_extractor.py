import boto3
import json
import os
import sys

# Output Directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")

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
        return ["us-east-1", "us-west-2", "eu-west-1"] # Fallback

def get_instance_types(regions):
    # Just get from one region to save time, or all? The prompt says "Pull Regions, Instance Types".
    # Usually instance types are global in definition but availability varies.
    # We will pull from us-east-1 as a reference.
    print("Fetching Instance Types (us-east-1)...")
    try:
        ec2 = boto3.client('ec2', region_name='us-east-1')
        paginator = ec2.get_paginator('describe_instance_types')
        instance_types = []
        for page in paginator.paginate():
            instance_types.extend(page['InstanceTypes'])
        return instance_types
    except Exception as e:
        print(f"Error fetching instance types: {e}")
        return []

def get_rds_engines():
    print("Fetching RDS Engines...")
    try:
        rds = boto3.client('rds', region_name='us-east-1')
        # This can be heavy. describe_db_engine_versions
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

def main():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    # 1. Regions
    regions = get_regions()
    save_json(regions, "regions.json")

    # 2. Instance Types (Metadata)
    instance_types = get_instance_types(regions)
    # Simplify for metadata file
    simple_instances = []
    for it in instance_types:
        simple_instances.append({
            "type": it['InstanceType'],
            "vcpus": it['VCpuInfo']['DefaultVCpus'],
            "memory": it['MemoryInfo']['SizeInMiB'] / 1024,
            "storage": it.get('InstanceStorageInfo', "EBS Only"),
            "arch": it['ProcessorInfo']['SupportedArchitectures']
        })
    save_json(simple_instances, "ec2_metadata.json")

    # 3. RDS Metadata
    rds_engines = get_rds_engines()
    save_json(rds_engines, "rds_metadata.json")

    print("\nMetadata Extraction Complete.")

if __name__ == "__main__":
    main()
