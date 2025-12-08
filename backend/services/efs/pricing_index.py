import json
import os
import logging

logger = logging.getLogger(__name__)

class PricingIndex:
    def __init__(self):
        self.data = []
        self._load_data()
        
    def _load_data(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        normalized_file = os.path.join(base_dir, 'data', 'normalized', 'efs.json')
        if os.path.exists(normalized_file):
            try:
                with open(normalized_file, 'r') as f:
                    content = json.load(f)
                    self.data = content.get('products', [])
            except Exception as e:
                logger.error(f"EFS PricingIndex load failed: {e}")
    
    def find_price(self, filters):
        for item in self.data:
            match = True
            for k, v in filters.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                return item
        return None
