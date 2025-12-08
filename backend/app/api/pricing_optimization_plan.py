import time
from collections import defaultdict

class PricingIndex:
    def __init__(self, data):
        self.data = data
        self.indices = {} # key -> { val -> [item_indices] }
        
        # Always index by region
        self.build_index("region")
        
        # Auto-detect other high-cardinality fields?
        # For now, manually add common ones or heuristics
        sample = data[0] if data else {}
        if "instance" in sample: self.build_index("instance")
        if "engine" in sample: self.build_index("engine")
        if "description" in sample: pass # Too unique, not useful for range scan usually
        
    def build_index(self, field):
        print(f"Building index for {field}...")
        idx = defaultdict(list)
        for i, item in enumerate(self.data):
            # value lookup strategy: top-level -> attributes dict
            val = item.get(field)
            if val is None:
                attrs = item.get("attributes")
                if isinstance(attrs, dict):
                    val = attrs.get(field)
            
            if val:
                idx[str(val)].append(i)
        
        self.indices[field] = idx

    def query(self, filters):
        # 1. Pick best index
        candidate_indices = None
        
        # Sort filters by expected selectivity? 
        # Actually usually filtering by specific ID (instance) is best, then Region.
        # Check if any filter matches an index
        
        best_field = None
        smallest_set_size = float('inf')
        
        for k, v in filters.items():
            if k in self.indices:
                # Check size of result set result
                idx_lookup = self.indices[k].get(str(v))
                if idx_lookup:
                    size = len(idx_lookup)
                    if size < smallest_set_size:
                        smallest_set_size = size
                        best_field = k
                else:
                    # Index exists but value not found -> Return empty immediately
                    return []
        
        if best_field:
            # Use this index
            candidate_indices = self.indices[best_field][str(filters[best_field])]
        
        # If no index used, scan all
        if candidate_indices is None:
            candidates = self.data
        else:
            candidates = [self.data[i] for i in candidate_indices]
            
        # 2. Filter remaining
        results = []
        for item in candidates:
            match = True
            item_attrs = item.get("attributes", {})
            if not isinstance(item_attrs, dict): item_attrs = {} # handle flat
            
            for k, v in filters.items():
                if k == best_field: continue # Already handled
                
                # Lookup
                val = item.get(k)
                if val is None: val = item_attrs.get(k)
                
                if str(val) != str(v):
                    match = False
                    break
            
            if match:
                results.append(item)
                if len(results) >= 100: break
        
        return results
