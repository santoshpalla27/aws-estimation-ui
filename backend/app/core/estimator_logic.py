import os
import sys
import importlib.util
import logging
from fastapi import HTTPException
from backend.app.api.registry import registry

logger = logging.getLogger(__name__)

async def calculate_estimate(service_id: str, payload_data: dict) -> dict:
    """
    Calculates the estimate for a given service and payload.
    Contains the core logic extracted from the router.
    """
    service_info = registry.get_service(service_id)
    if not service_info:
        raise ValueError(f"Service {service_id} not found")

    if not service_info.get('hasEstimator'):
        raise ValueError(f"Service {service_id} does not support estimation")

    # Load service estimator dynamically
    service_dir = registry.get_service_path(service_id)
    estimator_path = os.path.join(service_dir, "estimator.py")
    
    if not os.path.exists(estimator_path):
        raise RuntimeError(f"Estimator module not found for {service_id}")

    try:
        # Import the module
        spec = importlib.util.spec_from_file_location(f"services.{service_id}.estimator", estimator_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"services.{service_id}.estimator"] = module
        spec.loader.exec_module(module)

        if not hasattr(module, 'estimate'):
            raise RuntimeError(f"Service {service_id} estimator missing estimate() function")

        # Schema Validation
        payload = payload_data
        schema_path = os.path.join(service_dir, "schema.py")
        if os.path.exists(schema_path):
            try:
                schema_spec = importlib.util.spec_from_file_location(f"services.{service_id}.schema", schema_path)
                schema_module = importlib.util.module_from_spec(schema_spec)
                sys.modules[f"services.{service_id}.schema"] = schema_module
                schema_spec.loader.exec_module(schema_module)
                
                schema_name = f"{service_id.upper()}EstimatePayload"
                
                if hasattr(schema_module, schema_name):
                    ModelClass = getattr(schema_module, schema_name)
                    # Validate
                    try:
                        validated_model = ModelClass(**payload_data)
                        payload = validated_model.dict()
                    except Exception as ve:
                         # Re-raise as ValueError to be caught by caller as client error
                         raise ValueError(f"Validation Error: {str(ve)}")
                else:
                    logger.warning(f"Schema model {schema_name} not found in {schema_path}")
            except Exception as e:
                # If validation error (ValueError), re-raise. Else log and proceed.
                if isinstance(e, ValueError):
                    raise
                logger.error(f"Schema loading failed for {service_id}: {e}")
        
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

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Estimation failed for {service_id}: {str(e)}")
        raise RuntimeError(str(e))
