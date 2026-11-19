from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class TelemetryPayload(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100, examples=["EDGE-NODE-01A"])
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_type: str = Field(..., min_length=1, max_length=50, examples=["meteorological", "oceanographic"])
    metrics: dict[str, Any] = Field(
        ...,
        examples=[
            {
                "latitude": 29.5,
                "longitude": -89.2,
                "wind_speed_knots": 24.5,
                "sea_temp_c": 18.2,
            }
        ],
    )
    sensor_status: str = Field(
        default="OPERATIONAL", max_length=50, examples=["OPERATIONAL", "DEGRADED"]
    )
    classification_level: str = Field(
        default="UNCLASSIFIED", max_length=50, examples=["UNCLASSIFIED", "RESTRICTED"]
    )
