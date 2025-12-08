from pydantic import BaseModel
from typing import Optional

class S3EstimatePayload(BaseModel):
    storageGB: float
    storageClass: Optional[str] = "General Purpose"
    location: str
