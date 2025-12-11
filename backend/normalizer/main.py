import json
import os
import importlib.util
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from backend.app.core.paths import SERVICES_REGISTRY_FILE, SERVICES_DIR, RAW_DIR, NORMALIZED_DIR
except ImportError:
    # Fallback
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from backend.app.core.paths import SERVICES_REGISTRY_FILE, SERVICES_DIR, RAW_DIR, NORMALIZED_DIR

REGISTRY_PATH = str(SERVICES_REGISTRY_FILE)
SERVICES_DIR_PATH = str(SERVICES_DIR)

DATA_RAW_DIR = str(RAW_DIR)
DATA_NORMALIZED_DIR = str(NORMALIZED_DIR)

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
    service_path = os.path.join(SERVICES_DIR_PATH, service_id, 'normalizer.py')
    if not os.path.exists(service_path):
        logger.error(f"Normalizer module not found for {service_id} at {service_path}")
        return

    try:
        spec = importlib.util.spec_from_file_location(f"services.{service_id}.normalizer", service_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"services.{service_id}.normalizer"] = module
        spec.loader.exec_module(module)
        
        if hasattr(module, 'normalize'):
            from backend.app.core.paths import PRICING_DB
            
            # The normalizers (ec2, s3, etc.) expect an output DB path as the second argument,
            # NOT a JSON file path. They write their own summaries.
            module.normalize(raw_file, str(PRICING_DB))
            logger.info(f"Successfully normalized {service_id}")
            
            # --- Populate SQLite ---
            try:
                from backend.app.core.pricing_db import PricingDB
                from backend.app.core.paths import PRICING_DB
                
                db = PricingDB(PRICING_DB)
                indexed_fields = service_info.get('indexedFields', [])
                
                if indexed_fields:
                    logger.info(f"Populating DB for {service_id}")
                    db.initialize_service_table(service_id, indexed_fields)
                    
                    # Read back valid JSON and insert
                    with open(output_file, 'r') as f:
                        data = json.load(f)
                        # data is list of dicts or dict with 'products'
                        items = data if isinstance(data, list) else data.get('products', [])
                        
                    db.insert_records(service_id, items, indexed_fields)
                    db.close()
                    logger.info(f"DB population complete for {service_id}")
            except Exception as e:
                logger.error(f"Failed to populate DB for {service_id}: {e}")
            # -----------------------
            
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
