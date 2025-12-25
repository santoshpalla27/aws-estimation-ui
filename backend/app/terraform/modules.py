"""
Terraform module resolver.
Resolves and expands local modules.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional
from copy import deepcopy

from app.terraform.parser import TerraformParser
from app.config import settings

logger = logging.getLogger(__name__)


class ModuleResolverError(Exception):
    """Raised when module resolution fails."""
    pass


class ModuleResolver:
    """
    Resolves and expands Terraform modules.
    """
    
    def __init__(self, base_path: Path, max_depth: int = None):
        """
        Initialize module resolver.
        
        Args:
            base_path: Base path for resolving relative module sources
            max_depth: Maximum module nesting depth
        """
        self.base_path = base_path
        self.max_depth = max_depth or settings.max_module_depth
        self.parser = TerraformParser()
        self.resolved_modules = {}
    
    def is_local_module(self, source: str) -> bool:
        """
        Check if module source is local.
        
        Args:
            source: Module source string
        
        Returns:
            True if local module
        """
        # Local modules start with ./ or ../ or are absolute paths
        return (
            source.startswith("./") or
            source.startswith("../") or
            Path(source).is_absolute()
        )
    
    def resolve_module_path(self, source: str) -> Optional[Path]:
        """
        Resolve module source to filesystem path.
        
        Args:
            source: Module source string
        
        Returns:
            Resolved path or None if not local
        """
        if not self.is_local_module(source):
            logger.warning(f"Remote module not supported: {source}")
            return None
        
        # Resolve relative to base path
        if source.startswith("./") or source.startswith("../"):
            module_path = (self.base_path / source).resolve()
        else:
            module_path = Path(source).resolve()
        
        if not module_path.exists():
            raise ModuleResolverError(f"Module path does not exist: {module_path}")
        
        return module_path
    
    def parse_module(self, module_path: Path) -> Dict:
        """
        Parse a module directory.
        
        Args:
            module_path: Path to module directory
        
        Returns:
            Parsed module structure
        """
        if str(module_path) in self.resolved_modules:
            return self.resolved_modules[str(module_path)]
        
        logger.info(f"Parsing module: {module_path}")
        
        parsed = self.parser.parse(module_path)
        self.resolved_modules[str(module_path)] = parsed
        
        return parsed
    
    def expand_module(
        self,
        module_config: Dict,
        depth: int = 0
    ) -> List[Dict]:
        """
        Expand a module into its resources.
        
        Args:
            module_config: Module configuration
            depth: Current nesting depth
        
        Returns:
            List of expanded resources
        """
        if depth >= self.max_depth:
            logger.warning(f"Maximum module depth ({self.max_depth}) reached")
            return []
        
        source = module_config.get("source")
        if not source:
            logger.error("Module has no source")
            return []
        
        # Resolve module path
        module_path = self.resolve_module_path(source)
        if not module_path:
            # Remote module - skip
            return []
        
        # Parse module
        try:
            parsed_module = self.parse_module(module_path)
        except Exception as e:
            logger.error(f"Failed to parse module {source}: {e}")
            return []
        
        # Get module resources
        resources = parsed_module.get("resources", [])
        
        # Apply module variables to resources
        module_vars = {k: v for k, v in module_config.get("config", {}).items() if k != "source"}
        
        expanded_resources = []
        for resource in resources:
            # Create a copy and apply module prefix
            expanded_resource = deepcopy(resource)
            expanded_resource["name"] = f"{module_config['name']}.{resource['name']}"
            expanded_resource["module"] = module_config["name"]
            
            # TODO: Apply module variable substitution
            # This would require more complex variable resolution
            
            expanded_resources.append(expanded_resource)
        
        # Recursively expand nested modules
        nested_modules = parsed_module.get("modules", [])
        for nested_module in nested_modules:
            nested_resources = self.expand_module(nested_module, depth + 1)
            expanded_resources.extend(nested_resources)
        
        return expanded_resources
    
    def expand_all_modules(self, modules: List[Dict]) -> List[Dict]:
        """
        Expand all modules.
        
        Args:
            modules: List of module configurations
        
        Returns:
            List of all expanded resources
        """
        all_resources = []
        
        for module in modules:
            try:
                resources = self.expand_module(module)
                all_resources.extend(resources)
                logger.info(f"Expanded module '{module['name']}': {len(resources)} resources")
            except Exception as e:
                logger.error(f"Failed to expand module '{module.get('name')}': {e}")
                continue
        
        return all_resources
