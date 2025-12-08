import requests
import json
import os
import logging

logger = logging.getLogger(__name__)

REGION = 'us-east-1'
OFFER_INDEX_URL = 'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEFS/current/region_index.json'

def download():
    logger.info("EFS: Starting download...")
    try:
        response = requests.get(OFFER_INDEX_URL)
        response.raise_for_status()
        region_index = response.json()
        
        region_url_suffix = region_index.get('regions', {}).get(REGION, {}).get('currentVersionUrl')
        if not region_url_suffix:
            logger.error(f"EFS: Could not find URL for region {REGION}")
            return

        price_url = f"https://pricing.us-east-1.amazonaws.com{region_url_suffix}"
        
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'data', 'raw')
        output_file = os.path.join(output_dir, 'efs.json')
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"EFS: Downloading pricing from {price_url} to {output_file}")
        
        with requests.get(price_url, stream=True) as r:
            r.raise_for_status()
            with open(output_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
                    
        logger.info("EFS: Download complete.")
    except Exception as e:
        logger.error(f"EFS: Download failed: {e}")
