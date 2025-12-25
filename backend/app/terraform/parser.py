"""
Terraform HCL parser.
Parses .tf files using python-hcl2.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional
import hcl2
import json

logger = logging.getLogger(__name__)


class TerraformParseError(Exception):
    """Raised when Terraform parsing fails."""
    pass


class TerraformParser:
    """
    Parses Terraform HCL files.
    """
    
    def __init__(self):
        self.parsed_files = {}
        self.resources = []
        self.variables = {}
        self.locals = {}
        self.modules = []
    
    def parse_file(self, file_path: Path) -> Dict:
        """
        Parse a single .tf file.
        
        Args:
            file_path: Path to .tf file
        
        Returns:
            Parsed HCL as dictionary
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse HCL
            parsed = hcl2.loads(content)
            
            logger.info(f"Parsed {file_path}")
            return parsed
        
        except Exception as e:
            raise TerraformParseError(f"Failed to parse {file_path}: {e}")
    
    def parse_directory(self, directory: Path) -> Dict:
        """
        Parse all .tf files in a directory.
        
        Args:
            directory: Path to directory containing .tf files
        
        Returns:
            Combined parsed HCL
        """
        tf_files = list(directory.glob("*.tf"))
        
        if not tf_files:
            raise TerraformParseError(f"No .tf files found in {directory}")
        
        logger.info(f"Found {len(tf_files)} .tf files in {directory}")
        
        # Parse all files and merge
        combined = {
            "resource": [],
            "variable": [],
            "locals": [],
            "module": [],
            "output": [],
            "data": []
        }
        
        for tf_file in tf_files:
            try:
                parsed = self.parse_file(tf_file)
                self.parsed_files[str(tf_file)] = parsed
                
                # Merge into combined structure
                for key in combined.keys():
                    if key in parsed:
                        if isinstance(parsed[key], list):
                            combined[key].extend(parsed[key])
                        else:
                            combined[key].append(parsed[key])
            
            except Exception as e:
                logger.error(f"Error parsing {tf_file}: {e}")
                continue
        
        return combined
    
    def extract_resources(self, parsed: Dict) -> List[Dict]:
        """
        Extract resource blocks from parsed HCL.
        
        Args:
            parsed: Parsed HCL dictionary
        
        Returns:
            List of resource dictionaries
        """
        resources = []
        
        resource_blocks = parsed.get("resource", [])
        
        for resource_block in resource_blocks:
            # Resource block structure: {resource_type: {resource_name: {attributes}}}
            for resource_type, resource_instances in resource_block.items():
                for resource_name, attributes in resource_instances.items():
                    resources.append({
                        "type": resource_type,
                        "name": resource_name,
                        "attributes": attributes
                    })
        
        logger.info(f"Extracted {len(resources)} resources")
        return resources
    
    def extract_variables(self, parsed: Dict) -> Dict:
        """
        Extract variable definitions from parsed HCL.
        
        Args:
            parsed: Parsed HCL dictionary
        
        Returns:
            Dictionary of variable definitions
        """
        variables = {}
        
        variable_blocks = parsed.get("variable", [])
        
        for variable_block in variable_blocks:
            for var_name, var_def in variable_block.items():
                variables[var_name] = {
                    "default": var_def.get("default"),
                    "type": var_def.get("type"),
                    "description": var_def.get("description")
                }
        
        logger.info(f"Extracted {len(variables)} variables")
        return variables
    
    def extract_locals(self, parsed: Dict) -> Dict:
        """
        Extract locals from parsed HCL.
        
        Args:
            parsed: Parsed HCL dictionary
        
        Returns:
            Dictionary of local values
        """
        locals_dict = {}
        
        locals_blocks = parsed.get("locals", [])
        
        for locals_block in locals_blocks:
            if isinstance(locals_block, dict):
                locals_dict.update(locals_block)
        
        logger.info(f"Extracted {len(locals_dict)} locals")
        return locals_dict
    
    def extract_modules(self, parsed: Dict) -> List[Dict]:
        """
        Extract module blocks from parsed HCL.
        
        Args:
            parsed: Parsed HCL dictionary
        
        Returns:
            List of module dictionaries
        """
        modules = []
        
        module_blocks = parsed.get("module", [])
        
        for module_block in module_blocks:
            for module_name, module_config in module_block.items():
                modules.append({
                    "name": module_name,
                    "source": module_config.get("source"),
                    "config": module_config
                })
        
        logger.info(f"Extracted {len(modules)} modules")
        return modules
    
    def parse(self, path: Path) -> Dict:
        """
        Parse Terraform files from a path.
        
        Args:
            path: Path to .tf file or directory
        
        Returns:
            Dictionary with parsed Terraform structure
        """
        if path.is_file():
            parsed = self.parse_file(path)
        elif path.is_dir():
            parsed = self.parse_directory(path)
        else:
            raise TerraformParseError(f"Invalid path: {path}")
        
        # Extract components
        self.resources = self.extract_resources(parsed)
        self.variables = self.extract_variables(parsed)
        self.locals = self.extract_locals(parsed)
        self.modules = self.extract_modules(parsed)
        
        return {
            "resources": self.resources,
            "variables": self.variables,
            "locals": self.locals,
            "modules": self.modules
        }
