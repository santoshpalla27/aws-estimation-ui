from fastapi import APIRouter, HTTPException
from .registry import registry
import os
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# backend/app/api/pricing_router.py
# We want BACKEND_DIR
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@router.get("/{service_id}")
async def get_pricing(service_id: str):
    service_info = registry.get_service(service_id)
    if not service_info:
        raise HTTPException(status_code=404, detail=f"Service {service_id} not found")
        
    # Serve normalized data? Or raw? Or indexed?
    # Requirement: "GET /api/pricing/{service}"
    # Usually this would return the normalized pricing or a subset.
    # Let's return the normalized JSON if it exists.
    # Data is usually at root/data, but let's see. 
    # If we moved everything to backend, maybe data should vary?
    # The prompt said "Move services normalizer metada may go under backend folder".
    # It didn't say "data". But downloader output is usually relative.
    # Let's check where downloader puts it. 
    # Dockerfile creates /app/data.
    # docker-compose maps ./data:/app/data.
    # So inside container, /app/data is root/data.
    # If app is running from /app/backend/app/main.py...
    # let's try to keep data at root for persistence outside of backend code.
    # But wait, if BACKEND_DIR is /app/backend.
    # Then root is dirname(BACKEND_DIR).
    
    ROOT_DIR = os.path.dirname(BACKEND_DIR)
    normalized_path = os.path.join(ROOT_DIR, 'data', 'normalized', f"{service_id}.json")
    if not os.path.exists(normalized_path):
        # Fallback check if data is in backend/data (unlikely but possible if moved)
        normalized_path = os.path.join(BACKEND_DIR, 'data', 'normalized', f"{service_id}.json")
        
    if not os.path.exists(normalized_path):
        raise HTTPException(status_code=404, detail="Pricing data not available")
        
    # Streaming response for large files would be better
    from fastapi.responses import FileResponse
    return FileResponse(normalized_path)
