"""
AWS Pricing API ingestion module.
Downloads pricing data from official AWS Pricing API endpoints.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class PricingIngestionError(Exception):
    """Raised when pricing ingestion fails."""
    pass


class AWSPricingIngestion:
    """
    AWS Pricing API client for downloading pricing data.
    
    Uses the AWS Price List API to download bulk pricing files.
    """
    
    def __init__(self):
        self.base_url = settings.aws_pricing_api_base
        self.bulk_url = settings.aws_bulk_pricing_base
        self.data_dir = Path(settings.pricing_data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # HTTP client with retry logic
        self.client = httpx.Client(
            timeout=300.0,  # 5 minutes for large files
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            transport=httpx.HTTPTransport(retries=3)
        )
    
    def get_service_index(self) -> Dict:
        """
        Get the index of all available pricing files.
        
        Returns:
            Dictionary mapping service codes to pricing file URLs
        """
        try:
            # AWS provides a JSON index of all pricing files
            index_url = f"{self.bulk_url}/offers/v1.0/aws/index.json"
            logger.info(f"Fetching pricing index from {index_url}")
            
            response = self.client.get(index_url)
            response.raise_for_status()
            
            index_data = response.json()
            return index_data.get("offers", {})
        
        except httpx.HTTPError as e:
            raise PricingIngestionError(f"Failed to fetch pricing index: {e}")
    
    def download_service_pricing(self, service_code: str) -> Optional[Path]:
        """
        Download pricing data for a specific service.
        
        Args:
            service_code: AWS service code (e.g., 'AmazonEC2')
        
        Returns:
            Path to downloaded pricing file, or None if not available
        """
        try:
            # Get service index
            index = self.get_service_index()
            
            if service_code not in index:
                logger.warning(f"Service {service_code} not found in pricing index")
                return None
            
            service_info = index[service_code]
            current_version = service_info.get("currentVersion")
            
            if not current_version:
                logger.warning(f"No current version for service {service_code}")
                return None
            
            # Build pricing file URL
            pricing_url = f"{self.bulk_url}{current_version}"
            
            logger.info(f"Downloading pricing for {service_code} from {pricing_url}")
            
            # Download pricing file
            response = self.client.get(pricing_url)
            response.raise_for_status()
            
            # Save to file
            output_file = self.data_dir / f"{service_code}_{datetime.now().strftime('%Y%m%d')}.json"
            output_file.write_bytes(response.content)
            
            logger.info(f"Downloaded {service_code} pricing to {output_file}")
            return output_file
        
        except httpx.HTTPError as e:
            raise PricingIngestionError(f"Failed to download pricing for {service_code}: {e}")
    
    def download_all_supported_services(self) -> Dict[str, Path]:
        """
        Download pricing for all supported services.
        
        Returns:
            Dictionary mapping service codes to downloaded file paths
        """
        results = {}
        
        for service_code in settings.supported_services:
            try:
                logger.info(f"Processing service: {service_code}")
                file_path = self.download_service_pricing(service_code)
                
                if file_path:
                    results[service_code] = file_path
                    logger.info(f"Successfully downloaded {service_code}")
                else:
                    logger.warning(f"Skipped {service_code} - not available")
            
            except Exception as e:
                logger.error(f"Error downloading {service_code}: {e}")
                continue
        
        return results
    
    def load_pricing_file(self, file_path: Path) -> Dict:
        """
        Load and parse a pricing JSON file.
        
        Args:
            file_path: Path to pricing file
        
        Returns:
            Parsed pricing data
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise PricingIngestionError(f"Failed to load pricing file {file_path}: {e}")
    
    def close(self):
        """Close HTTP client."""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def download_pricing_data() -> Dict[str, Path]:
    """
    Convenience function to download all pricing data.
    
    Returns:
        Dictionary mapping service codes to downloaded file paths
    """
    with AWSPricingIngestion() as ingestion:
        return ingestion.download_all_supported_services()
