import json
import os
from typing import List, Dict, Optional

# Constants
# registry.py is in backend/app/api/
# We want BASE_DIR to be 'backend' folder? Or Root? 
# If structure is root/backend/services
# BASE_DIR = root
# SERVICES_DIR = root/backend/services
# Let's verify levels:
# backend/app/api/registry.py (file)
# backend/app/api (dirname)
# backend/app (dirname)
# backend (dirname) -> This is where services is now.

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REGISTRY_PATH = os.path.join(BACKEND_DIR, 'services_registry.json')
SERVICES_DIR = os.path.join(BACKEND_DIR, 'services')

class ServiceRegistry:
    _instance = None
    _services: List[Dict] = []
    _service_map: Dict[str, Dict] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceRegistry, cls).__new__(cls)
            cls._instance._load_registry()
        return cls._instance

    def _load_registry(self):
        if not os.path.exists(REGISTRY_PATH):
            self._services = []
            return

        with open(REGISTRY_PATH, 'r') as f:
            self._services = json.load(f)
            self._service_map = {s['serviceId']: s for s in self._services}

    def get_all_services(self) -> List[Dict]:
        return self._services

    def get_service(self, service_id: str) -> Optional[Dict]:
        return self._service_map.get(service_id)

    def get_service_path(self, service_id: str) -> str:
        return os.path.join(SERVICES_DIR, service_id)

registry = ServiceRegistry()
