from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.evidence import EvidenceRead


class CandidateScoreRead(BaseModel):
    id: str
    candidate_id: str
    risk_score: int
    confidence_score: int
    risk_level: str
    recommended_window: str | None
    reason_codes: list[str]
    input_snapshot: dict
    explanation: str | None
    limitations: list[str]
    model_version: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateListItem(BaseModel):
    id: str
    name: str
    current_company_id: str
    company_name: str
    title: str
    department: str | None
    location: str | None
    domain: str | None
    follow_status: str
    risk_level: str | None = None
    risk_score: int | None = None
    confidence_score: int | None = None


class CandidateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    current_company_id: str
    title: str = Field(min_length=1, max_length=160)
    department: str | None = Field(default=None, max_length=160)
    location: str | None = Field(default=None, max_length=120)
    domain: str | None = Field(default=None, max_length=120)
    profile_summary: str | None = None
    source_type: str = Field(default="manual", max_length=40)
    follow_status: str = Field(default="new", max_length=40)


class CandidateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    current_company_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    department: str | None = Field(default=None, max_length=160)
    location: str | None = Field(default=None, max_length=120)
    domain: str | None = Field(default=None, max_length=120)
    profile_summary: str | None = None
    source_type: str | None = Field(default=None, max_length=40)
    follow_status: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def required_fields_cannot_be_cleared(self):
        for field in ("name", "current_company_id", "title", "source_type", "follow_status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class CandidateImportResult(BaseModel):
    created_count: int
    duplicate_count: int
    failed_count: int
    created_candidate_ids: list[str]
    errors: list[str]


class CandidateDetail(BaseModel):
    id: str
    name: str
    current_company_id: str
    company_name: str
    title: str
    department: str | None
    location: str | None
    domain: str | None
    profile_summary: str | None
    source_type: str
    follow_status: str
    created_at: datetime
    updated_at: datetime
    latest_score: CandidateScoreRead | None
    evidence: list[EvidenceRead]
