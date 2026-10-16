from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TalentPoolItem(Base):
    __tablename__ = "talent_pool_items"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"))
    owner_user_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    priority: Mapped[str] = mapped_column(String(40), default="medium")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="watching")
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    candidate = relationship("Candidate", back_populates="pool_items")
