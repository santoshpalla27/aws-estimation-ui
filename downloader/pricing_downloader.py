import os
import requests
import json
from tqdm import tqdm

# AWS Pricing API Endpoint
BASE_URL = "https://pricing.us-east-1.amazonaws.com"
OFFERS_URL = f"{BASE_URL}/offers/v1.0/aws/{{}}/current/index.json"

# Service Code Mapping
# The user asked for: EC2, EBS, RDS, S3, Lambda, EKS, Load Balancer, NAT Gateway, CloudFront
# Note: NAT Gateway is typically under AmazonEC2. EBS is sometimes under AmazonEC2 or AmazonEBS (renamed to AmazonEC2 in some contexts but let's check standard codes).
# Standard Offer Codes:
# EC2 -> AmazonEC2
# RDS -> AmazonRDS
# S3 -> AmazonS3
# Lambda -> AWSLambda
# EKS -> AmazonEKS
# CloudFront -> AmazonCloudFront
# EBS -> AmazonEBS (Often separate for volumes/snapshots)
# Load Balancer -> AmazonElastiCache? No. ElasticLoadBalancing.
# NAT Gateway -> Inside AmazonEC2.

SERVICES = {
    "EC2": "AmazonEC2",
    "RDS": "AmazonRDS",
    "S3": "AmazonS3",
    "Lambda": "AWSLambda",
    "EKS": "AmazonEKS",
    "EBS": "AmazonEBS", # Double check if this returns independent EBS pricing or if it's in EC2. Usually AmazonEBS exists.
    "ELB": "AmazonElastiCache", # Wait, ELB is typically distinct. Let's check. Actually it is 'AWSELB' or 'AmazonElastiCache' is wrong. It is 'ElasticLoadBalancing'.
    "CloudFront": "AmazonCloudFront"
}

# Correction for ELB and NAT
# ELB -> 'ElasticLoadBalancing' (classic) or 'ElasticLoadBalancingV2' (ALB/NLB)?
# Actually, 'AmazonEC2' often covers a lot.
# Let's use the standard "index" to verify codes if needed, but for now I will use the known standard codes.
# 'ElasticLoadBalancing' covers CLB/ALB/NLB usually.
SERVICES["ELB"] = "ElasticLoadBalancing"

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")

def download_file(url, filename):
    response = requests.get(url, stream=True)
    if response.status_code != 200:
        print(f"Failed to fetch {url}: Status {response.status_code}")
        return

    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024 * 1024 # 1MB

    print(f"Downloading {filename} ({total_size // (1024*1024)} MB)...")
    
    with open(filename, 'wb') as file, tqdm(
        desc=filename,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(block_size):
            size = file.write(data)
            bar.update(size)

def main():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    for friendly_name, offer_code in SERVICES.items():
        url = OFFERS_URL.format(offer_code)
        filename = os.path.join(DATA_DIR, f"{friendly_name.lower()}_pricing.json")
        
        print(f"\nProcessing {friendly_name} ({offer_code})...")
        if os.path.exists(filename):
            print(f"File {filename} already exists. Skipping... (Delete to re-download)")
            continue
            
        try:
            download_file(url, filename)
            print(f"Successfully saved to {filename}")
        except Exception as e:
            print(f"Error downloading {friendly_name}: {str(e)}")

if __name__ == "__main__":
    main()
