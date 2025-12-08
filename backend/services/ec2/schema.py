from pydantic import BaseModel
from typing import Optional

class EC2EstimatePayload(BaseModel):
    instanceType: str
    location: str
    operatingSystem: Optional[str] = "Linux"
    hours: Optional[float] = 730
    count: Optional[int] = 1
