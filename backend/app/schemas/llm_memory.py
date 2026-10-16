from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LLMMemoryCreate(BaseModel):
    candidate_id: str | None = None
    scope: str = Field(default="candidate", min_length=1, max_length=60)
    kind: str = Field(default="preference", min_length=1, max_length=60)
    content: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    weight: float = Field(default=1.0, ge=0, le=5)
    source: str = Field(default="user", min_length=1, max_length=60)


class LLMMemoryRead(BaseModel):
    id: str
    candidate_id: str | None
    scope: str
    kind: str
    content: str
    evidence_ids: list[str]
    weight: float
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemoryBuildResponse(BaseModel):
    created: int
    memories: list[LLMMemoryRead]
