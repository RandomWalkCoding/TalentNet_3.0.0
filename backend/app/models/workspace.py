from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DemoUser(Base):
    __tablename__ = "demo_users"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class DemoSession(Base):
    __tablename__ = "demo_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40))
    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(500))
    status_code: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class LLMRun(Base):
    __tablename__ = "llm_runs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40))
    candidate_id: Mapped[str] = mapped_column(String(40))
    operation: Mapped[str] = mapped_column(String(40))
    provider: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(160))
    used_fallback: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Relationship(Base):
    __tablename__ = "relationships"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[str] = mapped_column(String(40), index=True)
    source_candidate_id: Mapped[str] = mapped_column(String(40))
    target_candidate_id: Mapped[str] = mapped_column(String(40))
    relation: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[float] = mapped_column(Float)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="suspected")
    explanation: Mapped[str] = mapped_column(Text)


class SourceState(Base):
    __tablename__ = "source_states"
    provider: Mapped[str] = mapped_column(String(40), primary_key=True)
    status: Mapped[str] = mapped_column(String(40))


class UsageEvent(Base):
    __tablename__ = "usage_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40))
    candidate_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
