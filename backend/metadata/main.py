import json
import os
import importlib.util
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from backend.app.core.paths import SERVICES_REGISTRY_FILE, SERVICES_DIR, NORMALIZED_DIR, METADATA_FILE
except ImportError:
    # Fallback
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    from backend.app.core.paths import SERVICES_REGISTRY_FILE, SERVICES_DIR, NORMALIZED_DIR, METADATA_FILE

REGISTRY_PATH = str(SERVICES_REGISTRY_FILE)
SERVICES_DIR_PATH = str(SERVICES_DIR)
DATA_NORMALIZED_DIR = str(NORMALIZED_DIR)
METADATA_OUTPUT = str(METADATA_FILE)

def load_registry():
    with open(REGISTRY_PATH, 'r') as f:
        return json.load(f)

def run_service_metadata_extractor(service_info):
    service_id = service_info['serviceId']
    if not service_info.get('hasMetadata'):
        return None

    # Dynamic import
    service_path = os.path.join(SERVICES_DIR_PATH, service_id, 'metadata.py')
    if not os.path.exists(service_path):
        logger.error(f"Metadata module not found for {service_id}")
        return None

    try:
        spec = importlib.util.spec_from_file_location(f"services.{service_id}.metadata", service_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"services.{service_id}.metadata"] = module
        spec.loader.exec_module(module)
        
        if hasattr(module, 'extract_metadata'):
            # Optimization: We no longer pass the huge normalized_data blob.
            # The service metadata module is responsible for fetching what it needs (e.g. from DB).
            return {service_id: module.extract_metadata()}
        else:
            logger.error(f"Module {service_id} does not have extract_metadata()")
            return None
            
    except Exception as e:
        logger.error(f"Failed to extract metadata for {service_id}: {str(e)}")
        return None

def main():
    logger.info("Starting Global Metadata Orchestrator")
    registry = load_registry()
    
    global_metadata = {}
    
    for service_info in registry:
        meta = run_service_metadata_extractor(service_info)
        if meta:
            global_metadata.update(meta)
            
    with open(METADATA_OUTPUT, 'w') as f:
        json.dump(global_metadata, f, indent=2)
            
    logger.info(f"Global Metadata saved to {METADATA_OUTPUT}")

if __name__ == "__main__":
    main()
