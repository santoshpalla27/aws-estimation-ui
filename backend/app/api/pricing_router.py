from fastapi import APIRouter, HTTPException, Query, Request
from .registry import registry
from backend.app.core.paths import METADATA_FILE
import os
import json
import logging
import importlib.util
import sys

router = APIRouter()
logger = logging.getLogger(__name__)

# Cache for loaded classes
_pricing_indices = {}

def get_pricing_index(service_id: str):
    """
    Dynamically loads the PricingIndex class for a service.
    """
    if service_id in _pricing_indices:
        return _pricing_indices[service_id]
        
    service_path = registry.get_service_path(service_id)
    module_path = os.path.join(service_path, 'pricing_index.py')
    
    if not os.path.exists(module_path):
        # Fallback: Use BasePricingIndex if module doesn't exist? 
        # But we need allowed_filters. 
        # For now, require the module.
        logger.warning(f"No pricing_index.py found for {service_id}")
        return None
        
    try:
        spec = importlib.util.spec_from_file_location(f"services.{service_id}.pricing_index", module_path)
        module = importlib.util.module_from_spec(spec)
        # sys.modules needed for some relative imports if they exist
        sys.modules[f"services.{service_id}.pricing_index"] = module 
        spec.loader.exec_module(module)
        
        if hasattr(module, 'PricingIndex'):
            idx_class = module.PricingIndex
            instance = idx_class() # Initialize
            _pricing_indices[service_id] = instance
            return instance
        else:
            logger.error(f"Module {service_id} does not have PricingIndex class")
            return None
            
    except Exception as e:
        logger.error(f"Failed to load PricingIndex for {service_id}: {e}")
        return None

@router.get("/catalog/{service_id}")
async def get_catalog(
    service_id: str, 
    request: Request,
    page: int = Query(1, ge=1), 
    pageSize: int = Query(50, ge=1, le=100),
    sortBy: str = Query(None)
):
    """
    Returns paginated pricing data from the database.
    Query parameters are treated as filters (e.g. ?location=US East&instanceType=t3.micro).
    """
    service_info = registry.get_service(service_id)
    if not service_info:
        raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

    index = get_pricing_index(service_id)
    if not index:
        raise HTTPException(status_code=500, detail=f"Pricing index not available for {service_id}")
        
    # Extract filters from query params
    filters = dict(request.query_params)
    # Remove pagination/sort params from filters
    filters.pop('page', None)
    filters.pop('pageSize', None)
    filters.pop('sortBy', None)
    
    # Run query
    items, total = index.query(filters, page=page, per_page=pageSize, sort_by=sortBy)
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "pageSize": pageSize
    }

@router.get("/metadata/{service_id}")
async def get_metadata(service_id: str):
    """
    Returns metadata for dropdowns (locations, instanceTypes, etc.).
    Uses the pre-computed service_metadata.json for speed.
    """
    if not os.path.exists(METADATA_FILE):
         raise HTTPException(status_code=404, detail="Metadata not yet generated. Please wait for pipeline.")
         
    try:
        with open(METADATA_FILE, 'r') as f:
            data = json.load(f)
            
        service_meta = data.get(service_id)
        if not service_meta:
            # Try to fetch global metadata or return empty?
            # If service exists but no metadata, maybe it failed.
            return {}
            
        return service_meta
        
    except Exception as e:
        logger.error(f"Failed to read metadata: {e}")
        raise HTTPException(status_code=500, detail="Internal server error reading metadata")

@router.get("/{service_id}/raw")
async def get_raw_pricing(service_id: str):
    """
    Legacy endpoint for downloading the full raw JSON.
    """
    # ... existing logic ...
    service_info = registry.get_service(service_id)
    if not service_info:
        raise HTTPException(status_code=404, detail=f"Service {service_id} not found")
        
    from backend.app.core.paths import NORMALIZED_DIR
    normalized_path = NORMALIZED_DIR / f"{service_id}.json"
        
    if not normalized_path.exists():
        raise HTTPException(status_code=404, detail="Pricing data not available")
        
    from fastapi.responses import FileResponse
    return FileResponse(normalized_path)
