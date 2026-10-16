from pydantic import BaseModel, Field


class AISummaryResponse(BaseModel):
    candidate_id: str
    summary: str
    risk_explanation: str
    conflict_notes: list[str] = Field(default_factory=list)
    cited_evidence_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    model_provider: str = "local"
    model_name: str = "local-structured-v1"
    used_fallback: bool = True


class OutreachVariant(BaseModel):
    tone: str
    message: str
    evidence_ids: list[str] = Field(default_factory=list)


class OutreachResponse(BaseModel):
    candidate_id: str
    variants: list[OutreachVariant]
    compliance_note: str
    model_provider: str = "local"
    model_name: str = "local-structured-v1"
    used_fallback: bool = True


class LLMStatusResponse(BaseModel):
    provider: str
    model: str
    configured: bool
    base_url: str | None = None
    fallback_model: str = "local-structured-v1"
    last_error: str | None = None
