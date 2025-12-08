from fastapi import APIRouter, Request, HTTPException
import json
import os
import time
from typing import List, Optional, Dict, Any
from collections import defaultdict

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Ensure we look in the Docker mounted path
NORM_DIR = "/app/data/normalized"

class PricingIndex:
    def __init__(self, data: List[Dict]):
        self.data = data
        self.indices = {} # field -> { value_str -> [list_of_indices] }
        
        # Build default indices
        # Region is mandatory for this app architecture basically
        self.build_index("region")
        
        # Auto-index common selectivity headers if they exist in first few items
        if data:
            sample = data[0]
            # EC2 / RDS / Common keys
            candidates = ["instance", "instanceType", "engine", "productFamily", "storageClass"]
            for field in candidates:
                if self._get_val(sample, field) is not None:
                    self.build_index(field)

    def _get_val(self, item, key):
        """Helper to safely get value from top-level or 'attributes' dict"""
        val = item.get(key)
        if val is None:
            attrs = item.get("attributes")
            if isinstance(attrs, dict):
                val = attrs.get(key)
        return val

    def build_index(self, field):
        # Optimization: Don't re-index
        if field in self.indices: return
        
        print(f"  Indexing {field}...")
        idx = defaultdict(list)
        for i, item in enumerate(self.data):
            val = self._get_val(item, field)
            if val:
                idx[str(val)].append(i)
        
        self.indices[field] = idx

    def query(self, filters: Dict[str, str], offset: int = 0, limit: int = 20) -> tuple[List[Dict], int]:
        """
        Memory-efficient pagination. Returns (page_items, total_count).
        Iterates through candidates to count matches but only stores 'limit' items.
        """
        # 1. Select best index
        best_field = None
        candidate_indices = None
        smallest_count = float('inf')

        for key, value in filters.items():
            if key in self.indices:
                matches = self.indices[key].get(value)
                if matches is None:
                    return [], 0
                
                if len(matches) < smallest_count:
                    smallest_count = len(matches)
                    candidate_indices = matches
                    best_field = key
        
        # 2. Iterate candidates
        page_items = []
        total_count = 0
        
        iterable = range(len(self.data)) if candidate_indices is None else candidate_indices
        
        # Upper bound for iteration if we don't need total count? 
        # But we usually need total_count for pagination UI.
        # We must iterate all matches to count them.
        
        for i in iterable:
            item = self.data[i]
            match = True
            
            for k, v in filters.items():
                if k == best_field: continue 
                
                val = self._get_val(item, k)
                if str(val) != v:
                    match = False
                    break
            
            if match:
                if total_count >= offset and len(page_items) < limit:
                    page_items.append(item)
                total_count += 1
                
        return page_items, total_count

    def get_unique_values(self, field, filters=None):
        # If no filters, and field is indexed, use keys directly O(1)
        if not filters and field in self.indices:
            return sorted(self.indices[field].keys())
            
        # Otherwise, query and collect
        # This supports cascade filtering (e.g. get instance types for region=us-east-1)
        # Otherwise, query and collect
        # This supports cascade filtering (e.g. get instance types for region=us-east-1)
        # Use high limit, offset 0
        dataset, _ = self.query(filters or {}, offset=0, limit=100000)
        values = set()
        for item in dataset:
            val = self._get_val(item, field)
            if val: values.add(val)
        return sorted(list(values), key=lambda x: str(x))

# Global Cache: service_name -> PricingIndex
PRICING_CACHE: Dict[str, PricingIndex] = {}

def load_pricing(service: str) -> Optional[PricingIndex]:
    if service in PRICING_CACHE:
        return PRICING_CACHE[service]
    
    # Locate file
    target_file = None
    if os.path.exists(NORM_DIR):
        for f in os.listdir(NORM_DIR):
            if f.lower() == f"{service.lower()}.json":
                target_file = os.path.join(NORM_DIR, f)
                break
    
    if not target_file:
        return None
        
    print(f"Loading and Indexing {service}...")
    start_t = time.time()
    try:
        with open(target_file, "r") as f:
            data = json.load(f)
            
        index = PricingIndex(data)
        PRICING_CACHE[service] = index
        print(f"Loaded {len(data)} items for {service} in {time.time() - start_t:.2f}s")
        return index
    except Exception as e:
        print(f"Error loading {service}: {e}")
        return None

@router.get("/{service}")
def get_pricing_options(
    service: str, 
    request: Request,
    page: int = 1,
    page_size: int = 20
):
    """
    Optimized pricing endpoint with server-side pagination.
    """
    index = load_pricing(service)
    if not index:
        return {
            "items": [],
            "total_items": 0,
            "total_pages": 0,
            "current_page": page
        }

    params = dict(request.query_params)
    # Remove pagination params from filters
    params.pop('page', None)
    params.pop('page_size', None)
    
    # Query creates the full filtered list (which is fast thanks to indexing)
    # Note: query() had a limit included which we should ideally remove or increase significantly for pagination to work correctly 
    # if total result set is large. But for now, let's assume query() returns candidates.
    # To properly support large datasets, query() limit should be removed or handled.
    # With index, we get candididates.
    
    # Optimized query
    start = (page - 1) * page_size
    paginated_items, total_items = index.query(params, offset=start, limit=page_size)
    
    total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 1
    
    return {
        "items": paginated_items,
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page
    }

@router.get("/{service}/attributes/{attribute_name}")
def get_unique_attribute_values(service: str, attribute_name: str, request: Request):
    """
    Get unique values for a specific attribute (e.g. 'group' or 'instanceType').
    Supports filtering (e.g. ?region=us-east-1).
    """
    index = load_pricing(service)
    if not index:
        return []
    
    # Allow filtering by other params (e.g. get engines available in us-east-1)
    filters = dict(request.query_params)
    
    return index.get_unique_values(attribute_name, filters)
