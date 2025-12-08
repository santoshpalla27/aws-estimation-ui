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
    index = load_pricing("ec2")
    if not index:
         raise HTTPException(status_code=500, detail="Pricing data not available")

    # Use O(1) query instead of iteration
    # Default to Linux / Shared tenancy if finding multiple matches
    results, _ = index.query({"region": req.region, "instance": req.instance_type}, limit=100)
    
    match = None
    # Refine match (prefer Linux + Shared)
    for item in results:
        attrs = item.get("attributes", {})
        # Check OS (some data might not have 'operatingSystem' if it's generic, but usually it does)
        os_type = attrs.get("operatingSystem", "Linux")
        tenancy = attrs.get("tenancy", "Shared")
        
        if os_type == "Linux" and tenancy == "Shared":
            match = item
            break
    
    # Fallback: take first result if specific Linux/Shared not found but instance/region matched
    if not match and results:
        match = results[0]

    if not match:
        raise HTTPException(status_code=404, detail=f"Instance {req.instance_type} not found in {req.region}")
    
    # Cost
    # Normalized data stores prices as strings, ensuring precision
    hourly_rate = float(match.get("ondemand", 0)) 
    
    hours = req.hours_per_month
    if req.term == "reserved_1yr":
        # Check for reserved price in data or apply standard discount heuristic
        # For now, MVP applies heuristic if real reserved data missing
        rs_rate = float(match.get("reserved_1yr", 0))
        if rs_rate > 0:
            hourly_rate = rs_rate
        else:
            hourly_rate *= 0.6 # Fallback ~40% discount
            
    compute_cost = hourly_rate * hours
    
    # EBS Storage Calculation
    ebs_index = load_pricing("amazonebs")
    
    ebs_rate = 0.08 # Fallback (gp3 us-east-1 approx)
    if ebs_index:
        # Use query for region first
        ebs_items, _ = ebs_index.query({"region": req.region}, limit=1000)
        
        target_vol = (req.ebs_volume_type or 'gp3').lower()
        
        for item in ebs_items:
            attrs = item.get("attributes", {})
            api_name = attrs.get("volumeApiName", "").lower()
            
            if target_vol in api_name:
                 rate_str = item.get("price") or item.get("ondemand")
                 if rate_str:
                     ebs_rate = float(rate_str)
                     break
                         
    storage_cost = req.storage_gb * ebs_rate
    
    total = compute_cost + storage_cost
    
    return {
        "monthly_cost": round(total, 2),
        "details": {
            "compute_hourly": round(hourly_rate, 6),
            "compute_monthly": round(compute_cost, 2),
            "storage_monthly": round(storage_cost, 2),
            "storage_rate": ebs_rate,
            "storage_type": req.ebs_volume_type or 'gp3'
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
    # AWS Data Transfer Tiering
    # 1. Query for "Data Transfer" in this region
    # 2. Filter for transferType="AWS Outbound" (Internet)
    # 3. Sort by beginRange
    
    dt_gb = getattr(req, 'data_transfer_gb', 0)
    dt_cost = 0.0
    
    # We need to find all tiers
    # Use index.query to find all candidates
    dt_items, _ = index.query({"region": region, "family": "Data Transfer"}, limit=1000)
    
    # Filter for AWS Outbound
    outbound_tiers = []
    for item in dt_items:
        if item.get("transferType") == "AWS Outbound":
            outbound_tiers.append(item)
    
    # Sort by range
    # Tiers might be: 0-0.097GB ($0), 0.097-10TB, etc. Or just 0-100GB ($0).
    # Normalized beginRange is string, convert carefully.
    
    def get_range_start(i):
        try:
            return float(i.get("beginRange", 0))
        except:
            return 0.0

    outbound_tiers.sort(key=get_range_start)
    
    remaining_gb = dt_gb
    previous_max = 0
    
    # Logic: AWS tiers are usually defined as:
    # Tier 1: 0 - 100 GB (Price $0)
    # Tier 2: 100 GB - 10 TB ...
    
    # However, Pricing API sometimes returns them weirdly.
    # We will iterate through sorted tiers and fill the bucket.
    
    # If no tiers found (e.g. metadata missing), fallback to simple $0.09
    if not outbound_tiers:
        dt_cost = dt_gb * 0.09
    else:
        for tier in outbound_tiers:
            if remaining_gb <= 0: break
            
            try:
                begin = float(tier.get("beginRange", 0))
                end = float(tier.get("endRange", "inf") if tier.get("endRange") != "Inf" else float("inf"))
                price = float(tier.get("price", 0))
                
                # AWS API ranges are cumulative usually? No, they are bands.
                # Band size = end - begin
                # But notice begin starts at 0 sometimes for multiple tiers? No.
                # US-East-1 S3 Data Transfer:
                # 0 - 100 GB: $0
                # 100 GB - 10 TB: $0.09
                # ...
                
                # Check if this tier is applicable to current usage segment
                # We need to check gaps? Assuming sorted contiguous.
                
                # If tier starts after our previous max, gap?
                # Actually, simpler logic:
                # Capacity of this tier = end - begin
                # But 'begin' is absolute.
                
                # Effective capacity for this step:
                # We are filling from 0 up to dt_gb.
                
                tier_capacity = end - begin
                
                # How much of our total usage falls into this [begin, end] bucket?
                # Intersection of [0, dt_gb] and [begin, end]
                
                overlap_start = max(0, begin)
                overlap_end = min(dt_gb, end)
                
                if overlap_end > overlap_start:
                    usage_in_tier = overlap_end - overlap_start
                    dt_cost += usage_in_tier * price
            except Exception as e:
                print(f"Error calculating tier {tier}: {e}")
                continue

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
