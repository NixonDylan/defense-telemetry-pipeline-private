from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class TelemetryPayload(BaseModel):
    device_id: str = Field(..., examples=["EDGE-NODE-01A"])
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data_type: str = Field(..., examples=["meteorological", "oceanographic"])
    metrics: Dict[str, Any] = Field(..., examples=[{"wind_speed_knots": 24.5, "sea_temp_c": 18.2}])
    sensor_status: str = Field(default="OPERATIONAL", examples=["OPERATIONAL", "DEGRADED"])
    classification_level: str = Field(default="UNCLASSIFIED", examples=["UNCLASSIFIED", "RESTRICTED"])
