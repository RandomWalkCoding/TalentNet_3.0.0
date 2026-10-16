from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"))
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    confirmed_by_user: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    candidate = relationship("Candidate", back_populates="evidence_items")
    company = relationship("Company", back_populates="evidence_items")
