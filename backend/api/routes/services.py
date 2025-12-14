"""
Service catalog endpoints
"""

from fastapi import APIRouter, HTTPException, status
from typing import List
import structlog

from models.schemas import ServiceDefinition, ServiceMetadata
from services.plugin_loader import PluginLoader

router = APIRouter()
logger = structlog.get_logger()


@router.get("", response_model=List[ServiceMetadata])
async def list_services(category: str = None):
    """
    List all available AWS services
    Optionally filter by category
    """
    plugin_loader = PluginLoader()
    services = await plugin_loader.list_services(category=category)
    return services


@router.get("/{service_id}", response_model=ServiceDefinition)
async def get_service(service_id: str):
    """Get service definition by ID"""
    plugin_loader = PluginLoader()
    
    try:
        service_def = await plugin_loader.load_service(service_id)
        return service_def
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found"
        )
    except Exception as e:
        logger.error("service_load_failed", service_id=service_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load service: {str(e)}"
        )


@router.get("/{service_id}/schema")
async def get_service_schema(service_id: str):
    """Get JSON schema for service configuration"""
    plugin_loader = PluginLoader()
    
    try:
        service_def = await plugin_loader.load_service(service_id)
        # Return the config schema from the service definition
        return service_def.config_schema if hasattr(service_def, 'config_schema') else {"type": "object", "properties": {}}
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found"
        )
    except Exception as e:
        logger.error("schema_load_failed", service_id=service_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load schema: {str(e)}"
        )


@router.get("/{service_id}/ui-schema")
async def get_service_ui_schema(service_id: str):
    """Get UI schema for service configuration form"""
    plugin_loader = PluginLoader()
    
    try:
        service_def = await plugin_loader.load_service(service_id)
        return service_def.ui_schema
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found"
        )
