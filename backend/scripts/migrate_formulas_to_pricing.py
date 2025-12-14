"""
Bulk Pricing Migration Script
Migrates all remaining services from pricing_data.yaml to pricing.* references
Updates cost_formula.yaml files to use pricing context
"""

import yaml
import re
from pathlib import Path
from typing import Dict, List, Set
import structlog

logger = structlog.get_logger()


class FormulaPricingMigrator:
    """Migrate formulas from hardcoded pricing to pricing.* references"""
    
    # Patterns that indicate hardcoded pricing (4+ decimal places, value < 1.0)
    PRICING_PATTERN = re.compile(r'\b0\.\d{4,}\b')
    
    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir
        self.logger = logger.bind(component="formula_migrator")
    
    def migrate_all_services(self) -> Dict[str, int]:
        """Migrate all services to use pricing.* references"""
        stats = {
            'total_services': 0,
            'migrated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        for service_dir in self.plugins_dir.iterdir():
            if not service_dir.is_dir():
                continue
            
            stats['total_services'] += 1
            
            try:
                result = self.migrate_service(service_dir)
                if result:
                    stats['migrated'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                self.logger.error("migration_failed", service=service_dir.name, error=str(e))
                stats['errors'] += 1
        
        return stats
    
    def migrate_service(self, service_dir: Path) -> bool:
        """Migrate a single service"""
        service_id = service_dir.name
        formula_file = service_dir / "cost_formula.yaml"
        pricing_file = service_dir / "pricing_data.yaml"
        
        if not formula_file.exists():
            self.logger.warning("no_formula_file", service=service_id)
            return False
        
        if not pricing_file.exists():
            self.logger.warning("no_pricing_file", service=service_id)
            return False
        
        # Load files
        with open(formula_file, 'r') as f:
            formula_data = yaml.safe_load(f)
        
        with open(pricing_file, 'r') as f:
            pricing_data = yaml.safe_load(f)
        
        # Extract pricing keys from pricing_data.yaml
        pricing_keys = self._extract_pricing_keys(pricing_data)
        
        # Find and replace hardcoded pricing in formulas
        modified = False
        for step in formula_data.get('calculation_steps', []):
            original_formula = step.get('formula', '')
            new_formula = self._replace_hardcoded_pricing(original_formula, pricing_keys)
            
            if new_formula != original_formula:
                step['formula'] = new_formula
                modified = True
                self.logger.info(
                    "formula_updated",
                    service=service_id,
                    step=step['id'],
                    old=original_formula[:50],
                    new=new_formula[:50]
                )
        
        # Add pricing_keys section to formula
        if modified and 'pricing_keys' not in formula_data:
            formula_data['pricing_keys'] = self._generate_pricing_keys_mapping(pricing_keys)
        
        # Write updated formula
        if modified:
            with open(formula_file, 'w') as f:
                yaml.dump(formula_data, f, default_flow_style=False, sort_keys=False)
            
            self.logger.info("service_migrated", service=service_id)
            return True
        
        return False
    
    def _extract_pricing_keys(self, pricing_data: Dict) -> Set[str]:
        """Extract all pricing keys from pricing_data.yaml"""
        keys = set()
        
        for region_data in pricing_data.get('regions', {}).values():
            for key in region_data.keys():
                if key != 'free_tier' and not isinstance(region_data[key], dict):
                    keys.add(key)
        
        return keys
    
    def _replace_hardcoded_pricing(self, formula: str, pricing_keys: Set[str]) -> str:
        """Replace hardcoded pricing values with pricing.* references"""
        # Find all potential pricing values
        matches = self.PRICING_PATTERN.findall(formula)
        
        if not matches:
            return formula
        
        # Replace each match with pricing reference
        new_formula = formula
        for match in matches:
            # Try to infer pricing key from context
            pricing_key = self._infer_pricing_key(formula, match, pricing_keys)
            if pricing_key:
                new_formula = new_formula.replace(match, f"pricing.{pricing_key}")
        
        return new_formula
    
    def _infer_pricing_key(self, formula: str, value: str, available_keys: Set[str]) -> str:
        """Infer which pricing key corresponds to a hardcoded value"""
        # Simple heuristic: look for keywords in formula near the value
        formula_lower = formula.lower()
        
        if 'gb' in formula_lower and 'second' in formula_lower:
            return 'gb_second'
        elif 'request' in formula_lower:
            return 'request'
        elif 'storage' in formula_lower:
            return 'storage_gb_month'
        elif 'instance' in formula_lower or 'hour' in formula_lower:
            return 'instance_hour'
        
        # Return first available key as fallback
        return list(available_keys)[0] if available_keys else 'rate'
    
    def _generate_pricing_keys_mapping(self, pricing_keys: Set[str]) -> Dict[str, str]:
        """Generate pricing_keys mapping for plugin.yaml"""
        mapping = {}
        for key in pricing_keys:
            # Generate internal key name
            internal_key = key.replace('.', '_')
            mapping[internal_key] = f"aws.{key}"
        
        return mapping


def main():
    """Run bulk migration"""
    plugins_dir = Path("backend/plugins")
    
    migrator = FormulaPricingMigrator(plugins_dir)
    stats = migrator.migrate_all_services()
    
    print(f"\n📊 Migration Complete:")
    print(f"   Total Services: {stats['total_services']}")
    print(f"   Migrated: {stats['migrated']}")
    print(f"   Skipped: {stats['skipped']}")
    print(f"   Errors: {stats['errors']}")


if __name__ == "__main__":
    main()
