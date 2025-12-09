import logging
try:
    from backend.app.core.pricing_index_base import BasePricingIndex
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    from backend.app.core.pricing_index_base import BasePricingIndex

logger = logging.getLogger(__name__)

class PricingIndex(BasePricingIndex):
    def __init__(self):
        super().__init__('rds', allowed_filters=[
            'instanceType', 'databaseEngine', 'databaseEdition', 'deploymentOption', 
            'storage', 'licenseModel', 'vcpu', 'memory'
        ])
