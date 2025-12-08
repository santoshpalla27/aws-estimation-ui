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
    data_transfer_gb: float = 0

class S3EstimateRequest(BaseModel):
    region: str
    storage_gb: float
    requests: int = 0
    
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
    
    # EBS Storage (Generic $0.10/GB for gp3 as estimate if not specified)
    # Ideally should use EBS pricing file.
    ebs_rate = 0.08 # us-east-1 gp3 roughly
    storage_cost = req.storage_gb * ebs_rate
    
    total = compute_cost + storage_cost
    
    return {
        "monthly_cost": round(total, 2),
        "details": {
            "compute": round(compute_cost, 2),
            "storage": round(storage_cost, 2)
        }
    }

@router.post("/s3", response_model=EstimateResponse)
def estimate_s3(req: S3EstimateRequest):
    # Standard $0.023/GB
    rate = 0.023
    storage_cost = req.storage_gb * rate
    
    return {
        "monthly_cost": round(storage_cost, 2),
        "details": {
            "storage": round(storage_cost, 2)
        }
    }
