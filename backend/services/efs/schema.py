from pydantic import BaseModel
from typing import Optional

class EFSEstimatePayload(BaseModel):
    storageGB: float
    storageClass: Optional[str] = "Standard"
    location: str
