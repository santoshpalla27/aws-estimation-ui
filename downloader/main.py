import json
import os
import importlib.util
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

REGISTRY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'services_registry.json')
SERVICES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'services')

def load_registry():
    with open(REGISTRY_PATH, 'r') as f:
        return json.load(f)

def run_service_downloader(service_info):
    service_id = service_info['serviceId']
    if not service_info.get('hasDownloader'):
        logger.info(f"Skipping downloader for {service_id}")
        return

    logger.info(f"Starting download for {service_id}")
    
    # Dynamic import
    service_path = os.path.join(SERVICES_DIR, service_id, 'downloader.py')
    if not os.path.exists(service_path):
        logger.error(f"Downloader module not found for {service_id} at {service_path}")
        return

    try:
        spec = importlib.util.spec_from_file_location(f"services.{service_id}.downloader", service_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"services.{service_id}.downloader"] = module
        spec.loader.exec_module(module)
        
        if hasattr(module, 'download'):
            module.download()
            logger.info(f"Successfully downloaded {service_id}")
        else:
            logger.error(f"Module {service_id} does not have a download() function")
            
    except Exception as e:
        logger.error(f"Failed to download {service_id}: {str(e)}")

def main():
    logger.info("Starting Global Downloader Orchestrator")
    registry = load_registry()
    
    # Ensure data directories exist
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw'), exist_ok=True)
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_service_downloader, service) for service in registry]
        
        for future in as_completed(futures):
            future.result()
            
    logger.info("Global Downloader Finished")

if __name__ == "__main__":
    main()
