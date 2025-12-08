from pydantic import BaseModel
from typing import Optional

class RDSEstimatePayload(BaseModel):
    instanceType: str
    databaseEngine: str
    deploymentOption: Optional[str] = "Single-AZ"
    location: str
    hours: Optional[float] = 730
