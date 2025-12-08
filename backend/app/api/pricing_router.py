from fastapi import APIRouter, HTTPException
from .registry import registry
import os
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

@router.get("/{service_id}")
async def get_pricing(service_id: str):
    service_info = registry.get_service(service_id)
    if not service_info:
        raise HTTPException(status_code=404, detail=f"Service {service_id} not found")
        
    # Serve normalized data? Or raw? Or indexed?
    # Requirement: "GET /api/pricing/{service}"
    # Usually this would return the normalized pricing or a subset.
    # Let's return the normalized JSON if it exists.
    
    normalized_path = os.path.join(BASE_DIR, 'data', 'normalized', f"{service_id}.json")
    if not os.path.exists(normalized_path):
        raise HTTPException(status_code=404, detail="Pricing data not available")
        
    # Streaming response for large files would be better
    from fastapi.responses import FileResponse
    return FileResponse(normalized_path)
