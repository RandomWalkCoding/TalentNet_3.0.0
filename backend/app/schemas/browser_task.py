from datetime import datetime

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BrowserTaskCreate(BaseModel):
    task_type: str
    query: str
    target_site: str
    candidate_id: str | None = None
    company_id: str | None = None


class EvidenceDraft(BaseModel):
    candidate_id: str | None = None
    company_id: str | None = None
    source: str
    title: str
    url: str | None = None
    screenshot_path: str | None = None
    summary: str
    raw_text: str | None = None
    confidence: float = 0.65


class EvidenceDraftUpdate(BaseModel):
    candidate_id: str | None = None
    company_id: str | None = None
    source: str | None = Field(default=None, min_length=1, max_length=60)
    title: str | None = Field(default=None, min_length=1, max_length=240)
    url: str | None = None
    screenshot_path: str | None = None
    summary: str | None = Field(default=None, min_length=1)
    raw_text: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="before")
    @classmethod
    def require_at_least_one_field(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data:
            raise ValueError("At least one draft field is required.")
        return data


class BrowserTaskRead(BaseModel):
    id: str
    user_id: str | None
    task_type: str
    query: str
    target_site: str
    status: str
    result_summary: str | None
    evidence_draft: EvidenceDraft | None
    execution_log: list[dict]
    page_title: str | None
    page_url: str | None
    screenshot_path: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
