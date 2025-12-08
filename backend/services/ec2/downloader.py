import requests
import json
import os
import logging

logger = logging.getLogger(__name__)

# Constants
# For demo purposes, we fetch a specific region to avoid massive downloads
REGION = 'us-east-1'
# This is the Offer Index URL
OFFER_INDEX_URL = 'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/region_index.json'

def download():
    """
    Downloads EC2 pricing data.
    """
    logger.info("EC2: Starting download...")
    
    # 1. Fetch region index
    try:
        logger.info(f"EC2: Fetching region index from {OFFER_INDEX_URL}")
        response = requests.get(OFFER_INDEX_URL)
        response.raise_for_status()
        region_index = response.json()
        
        # 2. Get URL for the specific region
        region_url_suffix = region_index.get('regions', {}).get(REGION, {}).get('currentVersionUrl')
        if not region_url_suffix:
            logger.error(f"EC2: Could not find URL for region {REGION}")
            return

        price_url = f"https://pricing.us-east-1.amazonaws.com{region_url_suffix}"
        
        # 3. Stream download the pricing file
        # Output path: data/raw/ec2.json
        # Note: In a real system, we might save as ec2_us-east-1.json or merge.
        # For this requirement, "Output to /data/raw/{service}.json"
        
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'raw')
        output_file = os.path.join(output_dir, 'ec2.json')
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"EC2: Downloading pricing from {price_url} to {output_file}")
        
        with requests.get(price_url, stream=True) as r:
            r.raise_for_status()
            with open(output_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
                    
        logger.info("EC2: Download complete.")
        
    except Exception as e:
        logger.error(f"EC2: Download failed: {e}")
