import requests
import json
import os
import sys
import logging
from pathlib import Path

# Try to import robust_downloader, adding project root to path if needed
try:
    from backend.app.core.robust_downloader import download_file
except ImportError:
    # Add project root (4 levels up from services/ec2/downloader.py)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if project_root not in sys.path:
        sys.path.append(project_root)
    from backend.app.core.robust_downloader import download_file

logger = logging.getLogger(__name__)

# Constants
REGION = 'us-east-1'
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
        
        # 3. Download using robust downloader
        if 'backend.app.core.paths' in sys.modules:
            from backend.app.core.paths import RAW_DIR
            output_dir = str(RAW_DIR)
        else:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'data', 'raw')

        output_file = Path(output_dir) / 'ec2.json'
        
        logger.info(f"EC2: Downloading pricing from {price_url} to {output_file}")
        
        if download_file(price_url, output_file):
            logger.info("EC2: Download complete.")
        else:
            logger.error("EC2: Download failed.")
        
    except Exception as e:
        logger.error(f"EC2: Download failed: {e}")
