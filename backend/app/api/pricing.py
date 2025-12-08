from fastapi import APIRouter, Request, HTTPException
import json
import os
from typing import List, Optional, Dict, Any

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Ensure we look in the Docker mounted path
NORM_DIR = "/app/data/normalized"

# Simple in-memory cache
PRICING_CACHE = {}

def load_pricing(service: str):
    # Normalize service name (case sensitive in file system?)
    # usually stored as AmazonEC2.json
    if service in PRICING_CACHE:
        return PRICING_CACHE[service]
    
    # Case insensitive search
    target_file = None
    if os.path.exists(NORM_DIR):
        for f in os.listdir(NORM_DIR):
            if f.lower() == f"{service.lower()}.json":
                target_file = os.path.join(NORM_DIR, f)
                break
    
    if not target_file:
        return []
        
    print(f"Loading {service} pricing...")
    try:
        with open(target_file, "r") as f:
            data = json.load(f)
            PRICING_CACHE[service] = data
            return data
    except Exception as e:
        print(f"Error loading {service}: {e}")
        return []

@router.get("/{service}")
def get_pricing_options(
    service: str, 
    request: Request
):
    """
    Generic pricing endpoint.
    Filters data based on ALL query parameters provided.
    Examples: ?region=us-east-1&instanceType=t3.micro
    """
    data = load_pricing(service)
    if not data:
        return []

    # Get all filter params
    params = dict(request.query_params)
    
    results = []
    
    # Optimize: If no params, return limited set?
    # Usually we require at least region
    target_region = params.get("region")
    
    for item in data:
        match = True
        
        # 1. Filter by Region (Standard field)
        if target_region:
            if item.get("region") != target_region:
                continue
        
        # 2. Filter by other params
        # Attributes can be flat (old normalizer) or in 'attributes' dict (generic)
        item_attrs = item.get("attributes", {})
        if not isinstance(item_attrs, dict):
             # Fallback if flat
             item_attrs = item 
        
        for key, value in params.items():
            if key == "region": continue
            
            # Check in flat item or attributes dict
            # Value matching: exact match for now
            # Handle potential type mismatch (string vs int)? 
            # API query params are strings. JSON might have numbers.
            
            # Check Generic Attributes
            attr_val = item_attrs.get(key)
            if attr_val is None:
                # Check flat item keys (e.g. 'instance' in EC2)
                attr_val = item.get(key)
                
            if str(attr_val) != value:
                match = False
                break
        
        if match:
            results.append(item)
            if len(results) >= 100: # Pagination limit
                break
    
    return results

@router.get("/{service}/attributes/{attribute_name}")
def get_unique_attribute_values(service: str, attribute_name: str, region: str = "us-east-1"):
    """
    Get all unique values for a specific attribute (e.g. 'group' or 'instanceType')
    to populate dropdowns in frontend.
    """
    data = load_pricing(service)
    values = set()
    
    for item in data:
        if item.get("region") != region:
            continue
            
        # Check 'attributes' dict first, then flat
        val = None
        if "attributes" in item and isinstance(item["attributes"], dict):
            val = item["attributes"].get(attribute_name)
        
        if val is None:
            val = item.get(attribute_name)
            
        if val:
            values.add(val)
            
    return sorted(list(values), key=lambda x: str(x))
