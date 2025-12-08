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
    service_info = registry.get_service(service_id)
    if not service_info:
        raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

    if not service_info.get('hasEstimator'):
        raise HTTPException(status_code=400, detail=f"Service {service_id} does not support estimation")

    # Load service estimator dynamically
    service_dir = registry.get_service_path(service_id)
    estimator_path = os.path.join(service_dir, "estimator.py")
    
    if not os.path.exists(estimator_path):
        raise HTTPException(status_code=500, detail=f"Estimator module not found for {service_id}")

    try:
        # Import the module
        spec = importlib.util.spec_from_file_location(f"services.{service_id}.estimator", estimator_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"services.{service_id}.estimator"] = module
        spec.loader.exec_module(module)

        if not hasattr(module, 'estimate'):
            raise HTTPException(status_code=500, detail=f"Service {service_id} estimator missing estimate() function")

        # Get payload
        payload = await request.json()
        
        # Calculate estimate
        # Note: Pricing index should be loaded/passed here. 
        # For now, we assume the estimator handles its own pricing index loading or we pass a reference.
        # Requirement: "Each service defines: estimate(payload, pricing_index)"
        # We need to implement the pricing index loading mechanism later or mock it now.
        # Let's try to load/mock it.
        
        # Load pricing index if exists
        pricing_index = None
        index_path = os.path.join(service_dir, "pricing_index.py")
        if os.path.exists(index_path):
             # Load index module
            idx_spec = importlib.util.spec_from_file_location(f"services.{service_id}.pricing_index", index_path)
            idx_module = importlib.util.module_from_spec(idx_spec)
            sys.modules[f"services.{service_id}.pricing_index"] = idx_module
            idx_spec.loader.exec_module(idx_module)
            # Instantiate or get index
            if hasattr(idx_module, 'PricingIndex'):
                pricing_index = idx_module.PricingIndex()
            
        result = module.estimate(payload, pricing_index)
        return result

    except Exception as e:
        logger.error(f"Estimation failed for {service_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
