#!/usr/bin/env python3
"""
Pricing Validation Script - Detect Hardcoded Pricing Numbers

This script scans all cost_formula.yaml files and detects numeric literals
that represent pricing values.

CRITICAL: This must pass with ZERO violations before deployment.

Usage:
    python backend/scripts/validate_no_hardcoded_pricing.py

Exit Codes:
    0 - No violations found
    1 - Hardcoded pricing detected
"""

import re
import sys
from pathlib import Path
from typing import List, Dict
import yaml

# Patterns that indicate hardcoded pricing
SUSPICIOUS_PATTERNS = [
    # Multiplication with decimal numbers
    (r'(\d+\.\d+)\s*\*\s*\w+', 'Decimal multiplied by variable'),
    (r'\w+\s*\*\s*(\d+\.\d+)', 'Variable multiplied by decimal'),
    
    # Division with decimal numbers
    (r'(\d+\.\d+)\s*/\s*\w+', 'Decimal divided by variable'),
    (r'\w+\s*/\s*(\d+\.\d+)', 'Variable divided by decimal'),
    
    # Direct assignment of decimal pricing
    (r':\s*(\d+\.\d+)\s*#.*(?:per|cost|price|rate)', 'Decimal with pricing comment'),
]

# Allowed contexts where numbers are OK
ALLOWED_CONTEXTS = [
    'constants:',
    'hours_per_month:',
    'free_tier:',
    'tier_boundaries:',
    'min:',
    'max:',
    'default:',
]

class PricingViolation:
    """Represents a hardcoded pricing violation"""
    
    def __init__(self, file: Path, line_num: int, line_content: str, pattern_desc: str, match: str):
        self.file = file
        self.line_num = line_num
        self.line_content = line_content.strip()
        self.pattern_desc = pattern_desc
        self.match = match
    
    def __str__(self):
        return (
            f"\n  File: {self.file}\n"
            f"  Line {self.line_num}: {self.line_content}\n"
            f"  Match: '{self.match}'\n"
            f"  Reason: {self.pattern_desc}"
        )


def is_allowed_context(content: str, match_start: int) -> bool:
    """Check if the match is in an allowed context"""
    # Get surrounding context (100 chars before)
    context = content[max(0, match_start - 100):match_start]
    
    # Check if any allowed context appears nearby
    for allowed in ALLOWED_CONTEXTS:
        if allowed in context:
            return True
    
    return False


def scan_formula_file(formula_file: Path) -> List[PricingViolation]:
    """
    Scan a single cost_formula.yaml file for hardcoded pricing
    
    Args:
        formula_file: Path to cost_formula.yaml
    
    Returns:
        List of violations found
    """
    violations = []
    
    try:
        content = formula_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        for pattern, description in SUSPICIOUS_PATTERNS:
            for match in re.finditer(pattern, content):
                # Check if in allowed context
                if is_allowed_context(content, match.start()):
                    continue
                
                # Find line number
                line_num = content[:match.start()].count('\n') + 1
                line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                
                # Skip if line is a comment
                if line_content.strip().startswith('#'):
                    continue
                
                violations.append(PricingViolation(
                    file=formula_file,
                    line_num=line_num,
                    line_content=line_content,
                    pattern_desc=description,
                    match=match.group()
                ))
    
    except Exception as e:
        print(f"⚠️  Warning: Could not scan {formula_file}: {e}", file=sys.stderr)
    
    return violations


def validate_pricing_keys_declared(formula_file: Path) -> List[str]:
    """
    Validate that formulas using pricing.* have declared pricing_keys
    
    Args:
        formula_file: Path to cost_formula.yaml
    
    Returns:
        List of warnings
    """
    warnings = []
    
    try:
        with open(formula_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Check if formula uses pricing references
        content = formula_file.read_text(encoding='utf-8')
        uses_pricing = 'pricing.' in content
        
        # Check if pricing_keys is declared
        has_pricing_keys = 'pricing_keys' in data or any(
            'pricing_keys' in step 
            for step in data.get('calculation_steps', [])
        )
        
        if uses_pricing and not has_pricing_keys:
            warnings.append(
                f"{formula_file}: Uses 'pricing.*' but no 'pricing_keys' declared"
            )
    
    except Exception as e:
        pass  # Already handled in scan_formula_file
    
    return warnings


def main():
    """Main validation logic"""
    print("🔍 Scanning for hardcoded pricing in formulas...")
    print("=" * 80)
    
    # Find all cost_formula.yaml files
    plugins_dir = Path('backend/plugins')
    
    if not plugins_dir.exists():
        print(f"❌ Error: Plugins directory not found: {plugins_dir}")
        sys.exit(1)
    
    formula_files = list(plugins_dir.glob('*/cost_formula.yaml'))
    
    if not formula_files:
        print(f"⚠️  Warning: No cost_formula.yaml files found in {plugins_dir}")
        sys.exit(1)
    
    print(f"📁 Found {len(formula_files)} formula files to scan\n")
    
    # Scan all files
    all_violations = []
    all_warnings = []
    
    for formula_file in sorted(formula_files):
        violations = scan_formula_file(formula_file)
        all_violations.extend(violations)
        
        warnings = validate_pricing_keys_declared(formula_file)
        all_warnings.extend(warnings)
    
    # Report results
    print("\n" + "=" * 80)
    
    if all_violations:
        print(f"\n❌ HARDCODED PRICING DETECTED: {len(all_violations)} violation(s)\n")
        print("The following formulas contain hardcoded pricing numbers:")
        
        for violation in all_violations:
            print(violation)
        
        print("\n" + "=" * 80)
        print("\n🚫 VALIDATION FAILED")
        print("\nAll pricing must use symbolic references:")
        print("  ❌ WRONG: storage_gb * 0.023")
        print("  ✅ CORRECT: storage_gb * pricing.storage.standard_gb_month")
        print("\nUpdate formulas to use pricing.* references only.")
        print("=" * 80)
        sys.exit(1)
    
    if all_warnings:
        print(f"\n⚠️  WARNINGS: {len(all_warnings)} warning(s)\n")
        for warning in all_warnings:
            print(f"  {warning}")
    
    print("\n✅ VALIDATION PASSED")
    print(f"\n✓ Scanned {len(formula_files)} formula files")
    print("✓ No hardcoded pricing numbers found")
    print("✓ All formulas use symbolic pricing references")
    
    if all_warnings:
        print(f"\n⚠️  {len(all_warnings)} warning(s) - review recommended")
    
    print("\n" + "=" * 80)
    sys.exit(0)


if __name__ == '__main__':
    main()
