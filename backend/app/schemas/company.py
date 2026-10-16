from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    industry: str = Field(min_length=1, max_length=120)
    website: str | None = Field(default=None, max_length=240)
    monitor_status: str = Field(default="active", max_length=40)


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    industry: str | None = Field(default=None, min_length=1, max_length=120)
    website: str | None = Field(default=None, max_length=240)
    monitor_status: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def required_fields_cannot_be_cleared(self):
        for field in ("name", "industry", "monitor_status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class CompanyRead(BaseModel):
    id: str
    name: str
    industry: str
    website: str | None
    monitor_status: str
    last_scanned_at: datetime | None
    candidate_count: int = 0
    high_risk_count: int = 0

    model_config = ConfigDict(from_attributes=True)
