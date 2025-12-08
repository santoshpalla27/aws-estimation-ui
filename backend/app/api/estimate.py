from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict

router = APIRouter()

class EC2EstimateRequest(BaseModel):
    region: str
    instance_type: str
    hours_per_month: float = 730
    term: str = "ondemand" # ondemand, reserved_1yr
    storage_gb: float = 30
    ebs_volume_type: str = "gp3"
    data_transfer_gb: float = 0

class S3EstimateRequest(BaseModel):
    region: str
    storage_gb: float
    storage_class: str = "Standard"
    requests: int = 0
    data_transfer_gb: float = 0
    
class EstimateResponse(BaseModel):
    monthly_cost: float
    details: Dict[str, float]

# Mock pricing lookup (in real app, import from pricing.py or use shared cache)
# For now, we assume frontend sends the Unit Price? 
# Better: Backend looks up price to ensure accuracy.
from app.api.pricing import load_pricing

@router.post("/ec2", response_model=EstimateResponse)
def estimate_ec2(req: EC2EstimateRequest):
    pricing = load_pricing("ec2")
    
    # Find price
    # Naive search
    match = None
    for item in pricing:
        if item.get("region") == req.region and item.get("instance") == req.instance_type:
            match = item
            break
            
    if not match:
        raise HTTPException(status_code=404, detail="Instance type not found in region")
    
    # Cost
    hourly_rate = float(match.get("ondemand", 0)) # default ondemand
    compute_cost = hourly_rate * req.hours_per_month
    
    # EBS Storage Calculation
    # Load EBS pricing (Generic Normalizer output -> amazonebs.json)
    ebs_pricing = load_pricing("amazonebs")
    
    ebs_rate = 0.08 # Fallback (gp3 us-east-1 approx)
    if ebs_pricing:
        # Find price for Region + Volume Type
        # EBS attributes often use 'volumeApiName' (gp2, io1) or 'volumeType' (General Purpose SSD)
        # We will try to match req.ebs_volume_type (e.g. 'gp3') against volumeApiName or abbr.
        
        target_vol = req.ebs_volume_type.lower() if hasattr(req, 'ebs_volume_type') else 'gp3'
        
        for item in ebs_pricing:
            if item.get("region") != req.region:
                continue
                
            attrs = item.get("attributes", {})
            if not isinstance(attrs, dict): attrs = {}
            
            # Check for API Name (gp2, gp3, io1, sc1, st1, standard)
            # AWS often puts 'gp2' in 'volumeApiName'
            api_name = attrs.get("volumeApiName", "").lower()
            
            # Or check description or name
            name = attrs.get("usagetype", "").lower() # sometimes helpful
            
            # Heuristic match
            if target_vol in api_name:
                # Found it. Check unit (GB-Mo)
                if "GB-Mo" in str(item.get("unit", "")):
                     rate_str = item.get("price") or item.get("ondemand")
                     if rate_str:
                         ebs_rate = float(rate_str)
                         break
                         
    storage_cost = req.storage_gb * ebs_rate
    
    total = compute_cost + storage_cost
    
    return {
        "monthly_cost": round(total, 2),
        "details": {
            "compute": round(compute_cost, 2),
            "storage": round(storage_cost, 2),
            "storage_rate": ebs_rate,
            "storage_type": req.ebs_volume_type if hasattr(req, 'ebs_volume_type') else 'gp3'
        }
    }

@router.post("/s3", response_model=EstimateResponse)
def estimate_s3(req: S3EstimateRequest):
    pricing = load_pricing("s3")
    if not pricing:
        # Fallback constants if data missing
        storage_c = req.storage_gb * 0.023
        req_c = (req.requests / 1000) * 0.005
        return {"monthly_cost": round(storage_c + req_c, 2), "details": {"storage": storage_c, "requests": req_c}}

    # Filters
    region = req.region
    
    # 1. Storage Cost
    # Look for family="Storage", class=req.storage_class (default "General Purpose")
    # Need to map Frontend 'Standard' -> AWS 'General Purpose' or 'Standard'
    storage_rate = 0.023 # fallback
    
    # We will look for direct matches in the pricing index/list
    # Since pricing is list (or index), we search
    # Optimization: Use the index query if available!
    
    # Heuristic mapping for Storage Class
    s_class_map = {
        "Standard": "General Purpose",
        "Intelligent-Tiering": "Intelligent-Tiering",
        "Glacier": "Glacier",
        "Deep Archive": "Deep Archive",
        "One Zone-IA": "One Zone-IA",
        "Standard-IA": "Standard-IA"
    }
    target_class = s_class_map.get(req.storage_class, req.storage_class)
    
    # Find Storage Rate
    for item in pricing:
        if item.get("region") != region: continue
        if item.get("family") != "Storage": continue
        
        # Check class
        i_class = item.get("class")
        if i_class == target_class:
            price = float(item.get("price") or 0)
            if price > 0:
                storage_rate = price
                break
                
    storage_cost = req.storage_gb * storage_rate
    
    # 2. Request Cost
    # Simplified: Tier 1 (PUT/COPY/POST/LIST) vs Tier 2 (GET/SELECT)
    # req.requests comes in as total? Or split?
    # Request model usually has separate fields. For now assume generic 'requests' input covers everything?
    # Or frontend sends specifics.
    # Frontend sends 'requests' (int). Let's assume split 50/50 or just charge high tier for safety/margin.
    # Or updated input model.
    # Let's assume input 'requests_tier1' and 'requests_tier2' if model supports, else use single 'requests' as Tier 1.
    
    requests_count = req.requests
    req_rate = 0.005 # per 1000
    
    # Find request rate
    # group = "S3-API-Tier1" or "S3-API-Tier2"
    for item in pricing:
        if item.get("region") != region: continue
        if item.get("family") != "API Request": continue
        
        grp = item.get("group")
        if grp == "S3-API-Tier1":
             price = float(item.get("price") or 0)
             if price > 0:
                 req_rate = price # Price per unit (usually 1000)
                 break
                 
    # Price is usually per 1,000 requests
    request_cost = (requests_count / 1000) * req_rate
    
    # 3. Data Transfer (Out)
    # AWS Data Transfer is complex (first 100GB free, etc).
    # Simple approx: $0.09/GB for generic internet out
    dt_cost = getattr(req, 'data_transfer_gb', 0) * 0.09
    
    total = storage_cost + request_cost + dt_cost
    
    return {
        "monthly_cost": round(total, 2),
        "details": {
            "storage": round(storage_cost, 2),
            "requests": round(request_cost, 2),
            "data_transfer": round(dt_cost, 2),
            "storage_rate": storage_rate
        }
    }
