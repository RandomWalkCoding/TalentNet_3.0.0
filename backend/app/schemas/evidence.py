from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceRead(BaseModel):
    id: str
    candidate_id: str
    company_id: str | None
    source: str
    title: str
    url: str | None
    screenshot_path: str | None
    observed_at: datetime
    event_time: datetime | None
    summary: str
    confidence: float
    confirmed_by_user: bool

    model_config = ConfigDict(from_attributes=True)


class EvidenceDocumentUploadResponse(BaseModel):
    evidence: EvidenceRead
    filename: str
    content_type: str | None = None
    extracted_characters: int
    confirmed: bool


class ExtractedCandidateDraft(BaseModel):
    name: str | None = None
    company_name: str | None = None
    title: str | None = None
    department: str | None = None
    location: str | None = None
    domain: str | None = None
    profile_summary: str
    confidence: float = 0.6
    source_excerpt: str


class DocumentCandidateExtractionResponse(BaseModel):
    filename: str
    content_type: str | None = None
    extracted_characters: int
    candidate_count: int
    candidates: list[ExtractedCandidateDraft]


class EvidenceCreate(BaseModel):
    candidate_id: str
    company_id: str | None = None
    source: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=1, max_length=240)
    url: str | None = Field(default=None, max_length=500)
    screenshot_path: str | None = Field(default=None, max_length=500)
    observed_at: datetime | None = None
    event_time: datetime | None = None
    summary: str = Field(min_length=1)
    raw_text: str | None = None
    confidence: float = Field(default=0.7, ge=0, le=1)
    confirmed_by_user: bool = False


class EvidenceUpdate(BaseModel):
    company_id: str | None = None
    source: str | None = Field(default=None, min_length=1, max_length=60)
    title: str | None = Field(default=None, min_length=1, max_length=240)
    url: str | None = Field(default=None, max_length=500)
    screenshot_path: str | None = Field(default=None, max_length=500)
    observed_at: datetime | None = None
    event_time: datetime | None = None
    summary: str | None = Field(default=None, min_length=1)
    raw_text: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    confirmed_by_user: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def require_at_least_one_field(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data:
            raise ValueError("At least one evidence field is required.")
        return data
