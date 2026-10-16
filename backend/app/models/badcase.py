from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Badcase(Base):
    __tablename__ = "badcases"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"))
    score_id: Mapped[str | None] = mapped_column(ForeignKey("candidate_scores.id"), nullable=True)
    feedback_id: Mapped[str] = mapped_column(ForeignKey("feedback.id"))
    error_type: Mapped[str] = mapped_column(String(80), default="wrong_reason")
    user_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
