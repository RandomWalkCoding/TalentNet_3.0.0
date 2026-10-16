from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TalentPoolItemRead(BaseModel):
    id: str
    candidate_id: str
    candidate_name: str
    owner_user_id: str | None
    company_id: str
    company_name: str
    title: str
    department: str | None
    domain: str | None
    location: str | None
    priority: str
    status: str
    note: str | None
    risk_level: str | None
    risk_score: int | None
    confidence_score: int | None
    recommended_window: str | None
    added_at: datetime


class TalentPoolUpdate(BaseModel):
    priority: str | None = None
    status: str | None = None
    note: str | None = None


class TalentPoolItemModel(BaseModel):
    id: str
    candidate_id: str
    owner_user_id: str | None
    priority: str
    note: str | None
    status: str
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)
