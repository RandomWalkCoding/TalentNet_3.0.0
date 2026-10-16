from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LLMEvalCase(Base):
    __tablename__ = "llm_eval_cases"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(40), nullable=False)
    task_type: Mapped[str] = mapped_column(String(60), nullable=False)
    expected_evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    required_terms: Mapped[list[str]] = mapped_column(JSON, default=list)
    forbidden_terms: Mapped[list[str]] = mapped_column(JSON, default=list)
    min_citations: Mapped[int] = mapped_column(default=1)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class LLMEvalRun(Base):
    __tablename__ = "llm_eval_runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), default="completed")
    total_cases: Mapped[int] = mapped_column(default=0)
    passed_cases: Mapped[int] = mapped_column(default=0)
    failed_cases: Mapped[int] = mapped_column(default=0)
    average_score: Mapped[float] = mapped_column(Float, default=0)
    model_provider: Mapped[str] = mapped_column(String(60), default="local")
    model_name: Mapped[str] = mapped_column(String(120), default="local-structured-v1")
    used_fallback: Mapped[bool] = mapped_column(default=True)
    results: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
