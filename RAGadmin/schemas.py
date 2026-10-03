from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Report(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)
    report_id: int = Field(gt=0, strict=True)
    incident_id: int | None = Field(default=None, gt=0, strict=True)
    raw_text: str = Field(min_length=1, max_length=10000)
    category: Literal["NETWORK", "ELEVATOR", "PROJECTOR", "FACILITY", "OTHER", "ELECTRICAL", "SANITATION", "SECURITY", "STUDENT_SERVICE"]
    building: str = Field(min_length=1, max_length=20)
    floor: str | None = None
    room: str | None = None
    report_status: Literal["ACTIVE", "DELETED"] = "ACTIVE"
    incident_status: Literal["EMERGING", "CONFIRMED", "IN_PROGRESS", "RESOLVED"] | None = None
    created_at: datetime

    @field_validator("building")
    @classmethod
    def uppercase(cls, value):
        return value.upper()

    @field_validator("created_at")
    @classmethod
    def aware_time(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at phải kèm múi giờ, ví dụ +07:00")
        return value

    @model_validator(mode="after")
    def incident_pair(self):
        if self.incident_id is None and self.incident_status is not None:
            raise ValueError("Có incident_status thì phải có incident_id")
        return self


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)
