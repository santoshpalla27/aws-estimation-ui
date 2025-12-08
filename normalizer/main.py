import json
import os
import importlib.util
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(BASE_DIR, 'services_registry.json')
SERVICES_DIR = os.path.join(BASE_DIR, 'services')
DATA_RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
DATA_NORMALIZED_DIR = os.path.join(BASE_DIR, 'data', 'normalized')

def load_registry():
    with open(REGISTRY_PATH, 'r') as f:
        return json.load(f)

def run_service_normalizer(service_info):
    service_id = service_info['serviceId']
    if not service_info.get('hasNormalizer'):
        logger.info(f"Skipping normalizer for {service_id}")
        return

    raw_file = os.path.join(DATA_RAW_DIR, f"{service_id}.json")
    output_file = os.path.join(DATA_NORMALIZED_DIR, f"{service_id}.json")

    if not os.path.exists(raw_file):
        logger.warning(f"Raw data file for {service_id} not found: {raw_file}")
        return

    logger.info(f"Starting normalizer for {service_id}")
    
    # Dynamic import
    service_path = os.path.join(SERVICES_DIR, service_id, 'normalizer.py')
    if not os.path.exists(service_path):
        logger.error(f"Normalizer module not found for {service_id} at {service_path}")
        return

    try:
        spec = importlib.util.spec_from_file_location(f"services.{service_id}.normalizer", service_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"services.{service_id}.normalizer"] = module
        spec.loader.exec_module(module)
        
        if hasattr(module, 'normalize'):
            module.normalize(raw_file, output_file)
            logger.info(f"Successfully normalized {service_id}")
        else:
            logger.error(f"Module {service_id} does not have a normalize(raw_file, output_file) function")
            
    except Exception as e:
        logger.error(f"Failed to normalize {service_id}: {str(e)}")
        # Log stack trace in real implementation

def main():
    logger.info("Starting Global Normalizer Orchestrator")
    registry = load_registry()
    
    # Ensure data directories exist
    os.makedirs(DATA_NORMALIZED_DIR, exist_ok=True)
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_service_normalizer, service) for service in registry]
        
        for future in as_completed(futures):
            future.result()
            
    logger.info("Global Normalizer Finished")

if __name__ == "__main__":
    main()
