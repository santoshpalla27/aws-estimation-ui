from fastapi import APIRouter, HTTPException
import json
import os

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw") # Metadata is in raw for now, or normalized?
# Step 2 saved metadata to raw/ec2_metadata.json and raw/regions.json.

@router.get("/")
def get_services():
    # Hardcoded or dynamic?
    return [
        {"id": "ec2", "name": "EC2", "icon": "server"},
        {"id": "rds", "name": "RDS", "icon": "database"},
        {"id": "s3", "name": "S3", "icon": "bucket"}
    ]

@router.get("/regions")
def get_regions():
    try:
        with open(os.path.join(DATA_DIR, "regions.json"), "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return ["us-east-1", "us-west-2", "eu-central-1"] # Fallback

@router.get("/rds/engines")
def get_rds_engines():
    try:
        with open(os.path.join(DATA_DIR, "rds_metadata.json"), "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
