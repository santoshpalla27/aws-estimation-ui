"""
Plugin Loader - Loads AWS service definitions from plugin files
Supports hot-reloading and caching
"""

from typing import List, Dict, Any, Optional
import yaml
import json
from pathlib import Path
import structlog

from models.schemas import ServiceDefinition, ServiceMetadata
from core.config import settings

logger = structlog.get_logger()


class PluginLoader:
    """
    Loads and caches AWS service plugins
    """
    
    def __init__(self):
        self.logger = logger.bind(component="plugin_loader")
        self.plugin_path = Path(settings.PLUGIN_STORAGE_PATH)
        self._cache: Dict[str, ServiceDefinition] = {}
    
    async def list_services(self, category: Optional[str] = None) -> List[ServiceMetadata]:
        """
        List all available services
        Optionally filter by category
        """
        services = []
        
        # Scan plugin directory
        if not self.plugin_path.exists():
            self.logger.warning("plugin_directory_not_found", path=str(self.plugin_path))
            return []
        
        for service_dir in self.plugin_path.iterdir():
            if not service_dir.is_dir():
                continue
            
            plugin_file = service_dir / "plugin.yaml"
            if not plugin_file.exists():
                continue
            
            try:
                with open(plugin_file, 'r') as f:
                    plugin_data = yaml.safe_load(f)
                
                metadata_dict = plugin_data.get("metadata", {})
                
                # Filter by category if specified
                if category and metadata_dict.get("category") != category:
                    continue
                
                # Load UI schema
                ui_schema = self._load_ui_schema(service_dir)
                
                # Add ui_schema to metadata
                metadata_dict["ui_schema"] = ui_schema
                
                metadata = ServiceMetadata(**metadata_dict)
                services.append(metadata)
                
            except Exception as e:
                self.logger.error(
                    "failed_to_load_service_metadata",
                    service_dir=service_dir.name,
                    error=str(e)
                )
        
        return services
    
    async def load_service(self, service_id: str) -> ServiceDefinition:
        """
        Load service definition by ID
        Uses cache if available
        """
        # Check cache
        if service_id in self._cache:
            return self._cache[service_id]
        
        # Load from file
        service_dir = self.plugin_path / service_id
        if not service_dir.exists():
            raise FileNotFoundError(f"Service plugin not found: {service_id}")
        
        plugin_file = service_dir / "plugin.yaml"
        if not plugin_file.exists():
            raise FileNotFoundError(f"Plugin file not found: {plugin_file}")
        
        try:
            with open(plugin_file, 'r') as f:
                plugin_data = yaml.safe_load(f)
            
            # Load additional files
            cost_formula = self._load_cost_formula(service_dir)
            ui_schema = self._load_ui_schema(service_dir)
            
            service_def = ServiceDefinition(
                service_id=plugin_data["service_id"],
                version=plugin_data.get("version", "1.0.0"),
                category=plugin_data["category"],
                metadata=ServiceMetadata(**plugin_data["metadata"]),
                dependencies=plugin_data.get("dependencies", {}),
                cost_formula=cost_formula,
                validation_rules=plugin_data.get("validation_rules", []),
                ui_schema=ui_schema
            )
            
            # Cache it
            self._cache[service_id] = service_def
            
            self.logger.info("service_loaded", service_id=service_id)
            return service_def
            
        except Exception as e:
            self.logger.error("failed_to_load_service", service_id=service_id, error=str(e))
            raise
    
    def _load_cost_formula(self, service_dir: Path) -> Dict[str, Any]:
        """Load cost formula from YAML file"""
        formula_file = service_dir / "cost_formula.yaml"
        if not formula_file.exists():
            return {}
        
        with open(formula_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_ui_schema(self, service_dir: Path) -> Dict[str, Any]:
        """Load UI schema from JSON file"""
        schema_file = service_dir / "ui_schema.json"
        if not schema_file.exists():
            return {}
        
        with open(schema_file, 'r') as f:
            return json.load(f)
    
    def clear_cache(self):
        """Clear plugin cache (for hot-reloading)"""
        self._cache.clear()
        self.logger.info("plugin_cache_cleared")
