from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CandidateScore(Base):
    __tablename__ = "candidate_scores"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"))
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(40), default="needs_review")
    recommended_window: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    input_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list)
    model_version: Mapped[str] = mapped_column(String(40), default="seed-v1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    candidate = relationship("Candidate", back_populates="scores")
