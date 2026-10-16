from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BrowserTask(Base):
    __tablename__ = "browser_tasks"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    task_type: Mapped[str] = mapped_column(String(60), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    target_site: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(60), default="pending")
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_draft: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    execution_log: Mapped[list[dict]] = mapped_column(JSON, default=list)
    page_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
