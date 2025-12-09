from fastapi import APIRouter, HTTPException, Request
from .registry import registry
import importlib.util
import sys
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/{service_id}")
async def estimate(service_id: str, request: Request):
    from backend.app.core.estimator_logic import calculate_estimate
    
    try:
        payload_data = await request.json()
        result = await calculate_estimate(service_id, payload_data)
        return result

    except ValueError as ve:
        # User/Validation error
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        # Internal/Configuration error
        logger.error(f"Estimation error for {service_id}: {re}")
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        logger.error(f"Unexpected error for {service_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
