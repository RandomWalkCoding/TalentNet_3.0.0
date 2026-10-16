from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LLMEvalCaseRead(BaseModel):
    id: str
    candidate_id: str
    task_type: str
    expected_evidence_ids: list[str]
    required_terms: list[str]
    forbidden_terms: list[str]
    min_citations: int
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LLMEvalResult(BaseModel):
    case_id: str
    candidate_id: str
    task_type: str
    passed: bool
    score: float
    checks: dict[str, bool]
    citations: list[str] = Field(default_factory=list)
    model_provider: str
    model_name: str
    used_fallback: bool
    output_preview: str


class LLMEvalRunRead(BaseModel):
    id: str
    status: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    average_score: float
    model_provider: str
    model_name: str
    used_fallback: bool
    results: list[LLMEvalResult]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetSeedResponse(BaseModel):
    created_cases: int
    cases: list[LLMEvalCaseRead]
