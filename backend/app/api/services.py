from fastapi import APIRouter, HTTPException
import json
import os

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
METADATA_FILE = os.path.join(BASE_DIR, "data", "service_metadata.json") # Created by normalizer
MANIFEST_FILE = os.path.join(DATA_DIR, "services_manifest.json") # Created by extractor

@router.get("/")
def get_services():
    """
    Returns list of available services based on metadata.
    """
    services_list = []
    
    # 1. Try reading manifest first (list of supported codes)
    supported_codes = []
    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, "r") as f:
            supported_codes = json.load(f)
            
    # 2. Try reading metadata summary (shows what we actually have data for)
    # If Metadata file exists, it's the source of truth for "Available" services
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as f:
            meta = json.load(f)
            for code, details in meta.items():
                services_list.append({
                    "id": code,
                    "name": code, # Friendly name? usually code is readable enough e.g. AmazonEC2
                    "regions": details.get("regions", []),
                    "available_attributes": details.get("attributes", [])
                })
    
    # If metadata is empty (downloader hasn't run), fallback to manifest
    if not services_list and supported_codes:
        for code in supported_codes:
            services_list.append({
                "id": code,
                "name": code,
                "regions": ["us-east-1"], # Default
                "available_attributes": []
            })
            
    # Sort
    services_list.sort(key=lambda x: x["name"])
    
    return services_list

@router.get("/regions")
def get_regions():
    try:
        with open(os.path.join(DATA_DIR, "regions.json"), "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return ["us-east-1", "us-west-2", "eu-central-1"] 

@router.get("/{service}/metadata")
def get_service_metadata(service: str):
    """
    Get detailed metadata (attributes keys) for a service to build UI filters.
    """
    if os.path.exists(METADATA_FILE):
         with open(METADATA_FILE, "r") as f:
            meta = json.load(f)
            if service in meta:
                return meta[service]
    return {"regions": [], "attributes": []}
