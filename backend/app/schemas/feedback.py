from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FeedbackCreate(BaseModel):
    candidate_id: str
    outcome: str
    contact_channel: str | None = None
    note: str | None = None
    contacted_at: datetime | None = None


class FeedbackRead(BaseModel):
    id: str
    candidate_id: str
    user_id: str | None
    outcome: str
    contact_channel: str | None
    note: str | None
    contacted_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BadcaseRead(BaseModel):
    id: str
    candidate_id: str
    score_id: str | None
    feedback_id: str
    error_type: str
    user_reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
