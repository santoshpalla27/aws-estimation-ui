from fastapi import APIRouter, Query, HTTPException
import json
import os
from typing import List, Optional

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NORM_DIR = os.path.join(BASE_DIR, "data", "normalized")

# Simple in-memory cache
PRICING_CACHE = {}

def load_pricing(service: str):
    if service in PRICING_CACHE:
        return PRICING_CACHE[service]
    
    file_path = os.path.join(NORM_DIR, f"{service}.json")
    if not os.path.exists(file_path):
        return []
        
    print(f"Loading {service} pricing...")
    with open(file_path, "r") as f:
        data = json.load(f)
        PRICING_CACHE[service] = data
        return data

@router.get("/{service}")
def get_pricing_options(
    service: str, 
    region: str = Query(..., description="Region Code"),
    instance_type: Optional[str] = None
):
    data = load_pricing(service)
    
    # Filter
    filtered = [
        item for item in data 
        if item.get("region") == region
    ]
    
    if instance_type:
        filtered = [
            item for item in filtered 
            if item.get("instance") == instance_type or item.get("instance_type") == instance_type
        ]
        
    return filtered[:100] # Limit results

@router.get("/ec2/types")
def get_ec2_types(region: str):
    # distinct instance types for region
    data = load_pricing("ec2")
    types = set()
    for item in data:
        if item.get("region") == region:
            types.add(item.get("instance"))
    return sorted(list(types))
