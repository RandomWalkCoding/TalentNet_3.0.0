from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LLMMemory(Base):
    __tablename__ = "llm_memories"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("candidates.id"), nullable=True
    )
    scope: Mapped[str] = mapped_column(String(60), default="candidate")
    kind: Mapped[str] = mapped_column(String(60), default="preference")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(60), default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    candidate = relationship("Candidate")
