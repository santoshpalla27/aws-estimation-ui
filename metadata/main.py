import json
import os
import importlib.util
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(BASE_DIR, 'services_registry.json')
SERVICES_DIR = os.path.join(BASE_DIR, 'services')
DATA_NORMALIZED_DIR = os.path.join(BASE_DIR, 'data', 'normalized')
METADATA_OUTPUT = os.path.join(BASE_DIR, 'service_metadata.json')

def load_registry():
    with open(REGISTRY_PATH, 'r') as f:
        return json.load(f)

def run_service_metadata_extractor(service_info):
    service_id = service_info['serviceId']
    if not service_info.get('hasMetadata'):
        return None

    normalized_file = os.path.join(DATA_NORMALIZED_DIR, f"{service_id}.json")
    
    if not os.path.exists(normalized_file):
        logger.warning(f"Normalized data for {service_id} not found. skipping metadata.")
        return None

    # Load normalized data
    # Note: In production with huge files, we might pass the path, 
    # but the requirement says 'extract_metadata(normalized_data)' implies data object or maybe path.
    # Given 'Large pricing file handling via streaming' constraint, passing path is safer, 
    # but let's stick to the interface or pass the data if it's not huge, or load it inside.
    # The requirement says "extract_metadata(normalized_data)". 
    # For now, let's load it, but be mindful. 
    # Actually, for 'streaming', passing the path to the service and letting it stream read is better.
    # I will pass the LOADED dict for now as per "normalized_data" implication, 
    # but strictly I should probably pass the path for performance.
    # Let's try to pass the data object, assuming it fits in memory for this stage, or the service handles it.
    
    try:
        with open(normalized_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error reading {normalized_file}: {e}")
        return None

    # Dynamic import
    service_path = os.path.join(SERVICES_DIR, service_id, 'metadata.py')
    if not os.path.exists(service_path):
        logger.error(f"Metadata module not found for {service_id}")
        return None

    try:
        spec = importlib.util.spec_from_file_location(f"services.{service_id}.metadata", service_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"services.{service_id}.metadata"] = module
        spec.loader.exec_module(module)
        
        if hasattr(module, 'extract_metadata'):
            return {service_id: module.extract_metadata(data)}
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
