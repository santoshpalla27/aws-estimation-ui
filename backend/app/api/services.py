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

from app.api.pricing import load_pricing

@router.get("/{service}/metadata")
def get_service_metadata(service: str):
    """
    Get detailed metadata (attributes keys) for a service to build UI filters.
    Optimized to return only high-value filterable attributes.
    """
    # Use PricingIndex to determine real Variance/Cardinality
    index = load_pricing(service)
    if not index:
         # Fallback to static meta
         if os.path.exists(METADATA_FILE):
             with open(METADATA_FILE, "r") as f:
                meta = json.load(f)
                return meta.get(service, {"regions": [], "attributes": []})
         return {"regions": [], "attributes": []}
         
    # Smart filtering
    # 1. Blocklist
    blocklist = {
        "sku", "servicecode", "servicename", "location", "locationtype", 
        "operation", "usagetype", "currency", "priceperunit", "unit", 
        "region", "id", "prices", "attributes" # internal keys
    }
    
    # 2. Priority List (Always top)
    priority = [
        "productFamily", "instanceType", "storageClass", "volumeType", 
        "databaseEngine", "deploymentOption", "group"
    ]
    
    valid_attrs = []
    
    # Get all potential keys from index indices
    # (Index builds indices for all keys it finds interesting, or we scan sample)
    
    # We can scan the first few items to find keys, then check cardinality using index
    if not index.data:
        return {"regions": [], "attributes": []}
        
    sample_keys = set()
    for i in range(min(50, len(index.data))):
        item = index.data[i]
        # Main keys
        for k in item.keys():
            if k not in blocklist and isinstance(item[k], (str, int, float, bool)):
                sample_keys.add(k)
        # Attributes dict
        attrs = item.get("attributes", {})
        if isinstance(attrs, dict):
            for k in attrs.keys():
                if k not in blocklist:
                     sample_keys.add(k)
                     
    # Calculate Cardinality
    # We want fields with > 1 AND < 100 values usually
    for k in sample_keys:
        # Check index if available, else scan?
        # Index.build_index is lazy. We can force it or check unique values.
        # Check cached indices first? 
        # Actually PricingIndex only auto-indexes specific fields.
        # But get_unique_values uses the index OR scan.
        
        unique = index.get_unique_values(k)
        count = len(unique)
        
        if 1 < count < 60:
            valid_attrs.append(k)
        elif k in priority and count > 1: # Priority fields allow more values
            valid_attrs.append(k)

    # Sort: Priority first, then alpha
    valid_attrs.sort(key=lambda x: (0 if x in priority else 1, x))
    
    # Get Regions (Standard)
    regions = index.get_unique_values("region")
    
    return {
        "regions": regions, 
        "attributes": valid_attrs
    }
