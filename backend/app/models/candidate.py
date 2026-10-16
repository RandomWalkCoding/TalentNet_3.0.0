from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    current_company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    department: Mapped[str | None] = mapped_column(String(160), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(120), nullable=True)
    profile_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(40), default="imported")
    follow_status: Mapped[str] = mapped_column(String(40), default="new")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    current_company = relationship("Company", back_populates="candidates")
    evidence_items = relationship("Evidence", back_populates="candidate")
    scores = relationship("CandidateScore", back_populates="candidate")
    pool_items = relationship("TalentPoolItem", back_populates="candidate")
    feedback_items = relationship("Feedback", back_populates="candidate")
