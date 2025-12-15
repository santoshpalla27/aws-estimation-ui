"""
Pricing-Specific Exceptions for Hard-Fail Behavior

These exceptions enforce financial reliability by failing loudly
when pricing cannot be resolved.

NO FALLBACKS. NO DEFAULTS. NO SILENT FAILURES.
"""

class PricingResolutionError(Exception):
    """
    Raised when pricing cannot be resolved
    
    This is a CRITICAL error that must stop estimation.
    No fallback values. No defaults. Estimation aborted.
    """
    
    def __init__(self, service: str, key: str, region: str, available_keys: list = None):
        self.service = service
        self.key = key
        self.region = region
        self.available_keys = available_keys or []
        
        message = (
            f"PRICING RESOLUTION FAILED\n"
            f"  Service: {service}\n"
            f"  Key: {key}\n"
            f"  Region: {region}\n"
            f"  Status: NO FALLBACK. NO DEFAULT. ESTIMATION ABORTED.\n"
        )
        
        if available_keys:
            message += f"  Available keys: {', '.join(available_keys[:10])}"
            if len(available_keys) > 10:
                message += f" ... and {len(available_keys) - 10} more"
        
        super().__init__(message)


class PricingVersionMismatchError(Exception):
    """
    Raised when pricing version is incompatible with formula version
    
    This prevents using outdated pricing with new formulas or vice versa.
    """
    
    def __init__(self, formula_version: str, pricing_version: str, service: str):
        self.formula_version = formula_version
        self.pricing_version = pricing_version
        self.service = service
        
        message = (
            f"PRICING VERSION MISMATCH\n"
            f"  Service: {service}\n"
            f"  Formula Version: {formula_version}\n"
            f"  Pricing Version: {pricing_version}\n"
            f"  These versions are incompatible. Update pricing or formula."
        )
        
        super().__init__(message)


class MissingPricingDataError(Exception):
    """
    Raised when pricing data file doesn't exist for a service/region
    
    This indicates a configuration problem that must be fixed.
    """
    
    def __init__(self, service: str, region: str, expected_path: str = None):
        self.service = service
        self.region = region
        self.expected_path = expected_path
        
        message = (
            f"MISSING PRICING DATA\n"
            f"  Service: {service}\n"
            f"  Region: {region}\n"
        )
        
        if expected_path:
            message += f"  Expected path: {expected_path}\n"
        
        message += "  Pricing data must be ingested before estimation."
        
        super().__init__(message)


class PricingKeyNotDeclaredError(Exception):
    """
    Raised when a formula uses a pricing key that wasn't declared
    
    All pricing keys must be explicitly declared in pricing_keys list.
    """
    
    def __init__(self, service: str, key: str, declared_keys: list = None):
        self.service = service
        self.key = key
        self.declared_keys = declared_keys or []
        
        message = (
            f"PRICING KEY NOT DECLARED\n"
            f"  Service: {service}\n"
            f"  Key: {key}\n"
            f"  This key was used in formula but not declared in pricing_keys.\n"
        )
        
        if declared_keys:
            message += f"  Declared keys: {', '.join(declared_keys)}"
        
        super().__init__(message)


class HardcodedPricingDetectedError(Exception):
    """
    Raised when validation detects hardcoded pricing numbers
    
    This should be caught during development/CI, never in production.
    """
    
    def __init__(self, violations: list):
        self.violations = violations
        
        message = (
            f"HARDCODED PRICING DETECTED\n"
            f"  {len(violations)} violation(s) found.\n"
            f"  All pricing must use symbolic references.\n"
            f"  Run: python backend/scripts/validate_no_hardcoded_pricing.py"
        )
        
        super().__init__(message)
