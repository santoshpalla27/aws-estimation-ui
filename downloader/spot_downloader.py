
import boto3
import json
import os
import sys
import time
from datetime import datetime, timedelta

# Configuration
# Usually run as a separate job or cron
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SPOT_FILE = os.path.join(DATA_DIR, "spot_pricing.json")

# Regions to check (could be dynamic)
REGIONS = ["us-east-1", "us-west-2", "eu-central-1", "ap-south-1"]

# Instance types to check (to avoid throttling, we might want to check only popular ones or all)
# Checking ALL is heavy. Let's start with common ones.
# Or fetch all by not specifying instance types (if API allows, it does, but heavily paginated)
TARGET_INSTANCES = [
    "t3.micro", "t3.small", "t3.medium",
    "m5.large", "m5.xlarge", 
    "c5.large", "c5.xlarge",
    "r5.large", "r5.xlarge"
]

def fetch_spot_prices():
    print("Starting Spot Price Download...")
    
    spot_data = {}
    
    if os.path.exists(SPOT_FILE):
        try:
            with open(SPOT_FILE, 'r') as f:
                spot_data = json.load(f)
        except:
            spot_data = {}

    for region in REGIONS:
        print(f"Fetching {region}...")
        try:
            # Requires AWS Credentials in environment
            session = boto3.Session(region_name=region)
            ec2 = session.client('ec2')
            
            # Fetch history for last hour
            # We want current price.
            start_time = datetime.utcnow() - timedelta(minutes=60)
            
            # describe_spot_price_history paginates
            paginator = ec2.get_paginator('describe_spot_price_history')
            
            # Filter by ProductDescription='Linux/UNIX' usually
            response_iterator = paginator.paginate(
                InstanceTypes=TARGET_INSTANCES,
                ProductDescriptions=['Linux/UNIX'],
                StartTime=start_time
            )
            
            for page in response_iterator:
                for item in page['SpotPriceHistory']:
                    instance = item['InstanceType']
                    az = item['AvailabilityZone']
                    price = float(item['SpotPrice'])
                    
                    # Store cheapest price in region for simplicity (Naive)
                    # Or store per AZ. Backend usually just wants a representative price.
                    # We'll store: region -> instance -> price
                    
                    if region not in spot_data:
                        spot_data[region] = {}
                    
                    # Keep the lowest price found (most optimized strategy) or average?
                    # Spot users usually bid or check logic. Let's take the latest seen.
                    # Price history is list. Logic:
                    current = spot_data[region].get(instance, float('inf'))
                    if price < current:
                        spot_data[region][instance] = price
                        
        except Exception as e:
            print(f"Error fetching {region}: {e}")
            if "NoCredentialsError" in str(e):
                print("Skipping remaining regions due to missing credentials.")
                break

    # Save
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    with open(SPOT_FILE, 'w') as f:
        json.dump(spot_data, f, indent=2)
        
    print(f"Saved spot prices to {SPOT_FILE}")

if __name__ == "__main__":
    fetch_spot_prices()
