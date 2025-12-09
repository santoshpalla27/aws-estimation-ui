import logging
# Import from project root if needed, or relative
try:
    from backend.app.core.pricing_index_base import BasePricingIndex
except ImportError:
    import sys
    import os
    # Add project root
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    from backend.app.core.pricing_index_base import BasePricingIndex

logger = logging.getLogger(__name__)

class PricingIndex(BasePricingIndex):
    def __init__(self):
        super().__init__('s3', allowed_filters=[
            'productFamily', 'storageClass', 'volumeType', 'dataTransferType', 
            'fromLocation', 'toLocation', 'usagetype', 'operation'
        ])
