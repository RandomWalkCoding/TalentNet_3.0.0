from pydantic import BaseModel, Field

from app.schemas.browser_task import BrowserTaskRead


class TalentSourcingRequest(BaseModel):
    talent_profile: str = Field(min_length=1)
    company_id: str | None = None
    candidate_id: str | None = None
    target_count: int = Field(default=20, ge=1, le=200)
    public_site_scope: str | None = None
    max_tasks: int = Field(default=2, ge=1, le=6)


class CandidateLead(BaseModel):
    full_name: str | None = None
    current_company: str | None = None
    title: str | None = None
    education: str | None = None
    profile_links: list[str] = Field(default_factory=list)
    source_snippet: str | None = None
    evidence: str | None = None
    query: str | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    task_id: str | None = None
    candidate_id: str | None = None


class CandidateLeadSaveRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    current_company: str | None = Field(default=None, max_length=120)
    title: str | None = Field(default=None, max_length=160)
    education: str | None = Field(default=None, max_length=240)
    profile_links: list[str] = Field(default_factory=list)
    source_snippet: str | None = None
    confidence: float = Field(default=0.65, ge=0, le=1)


class CandidateLeadSaveResponse(BaseModel):
    candidate_id: str
    company_id: str


class TalentSourcingResponse(BaseModel):
    query_plan: list[dict]
    tasks: list[BrowserTaskRead]
    extracted_candidates: list[CandidateLead] = Field(default_factory=list)
    compliance_note: str
    model_provider: str = "local"
    model_name: str = "local-structured-v1"
    llm_used: bool = False
    used_fallback_plan: bool = True
