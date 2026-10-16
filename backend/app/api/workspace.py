from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.identity import current_user_id, require_admin
from app.models.workspace import AuditLog, DemoSession, DemoUser, UsageEvent
from app.models import Candidate
from typing import Literal
from uuid import uuid4
from app.services.llm_gateway import LLMGateway

router = APIRouter(tags=["workspace"])


class SessionSelection(BaseModel):
    user_id: str


class UsageEventCreate(BaseModel):
    candidate_id: str
    kind: Literal["candidate_view", "outreach_copy"]


@router.post("/usage-events", status_code=201)
def create_usage_event(payload: UsageEventCreate, db: Session = Depends(get_db)) -> dict:
    if db.get(Candidate, payload.candidate_id) is None:
        raise AppError("CANDIDATE_NOT_FOUND", "候选人不存在。", 404)
    db.add(UsageEvent(id=f"event_{uuid4().hex}", user_id=current_user_id.get(),
                      candidate_id=payload.candidate_id, kind=payload.kind))
    db.commit()
    return {"recorded": True}


@router.get("/session")
def session_context(request: Request, db: Session = Depends(get_db)) -> dict:
    users = db.scalars(select(DemoUser).where(DemoUser.active.is_(True))).all()
    return {
        "user_id": request.state.user_id,
        "role": request.state.user_role,
        "mode": "local_demo",
        "users": [{"id": u.id, "name": u.name, "role": u.role} for u in users],
    }


@router.post("/session")
def select_session(payload: SessionSelection, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.get(DemoUser, payload.user_id)
    if user is None or not user.active:
        raise AppError("USER_NOT_FOUND", "演示用户不存在。", 404)
    token = secrets.token_urlsafe(32)
    db.add(DemoSession(token_hash=sha256(token.encode()).hexdigest(), user_id=user.id,
                       expires_at=datetime.now(timezone.utc) + timedelta(days=7)))
    db.commit()
    response.set_cookie("talentnet_session", token, httponly=True, samesite="lax", max_age=604800)
    return {"user_id": user.id, "role": user.role}


@router.delete("/session")
def clear_session(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    token = request.cookies.get("talentnet_session")
    if token:
        session = db.get(DemoSession, sha256(token.encode()).hexdigest())
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie("talentnet_session")
    return {"mode": "local_demo"}


@router.get("/workspace/settings")
def workspace_settings() -> dict:
    return {"mode": "local_demo", "llm": LLMGateway().status(), "database": "SQLite",
            "notice": "本地演示用户切换用于验证权限；部署到网络前需接入真实身份认证。"}


@router.get("/audit-logs", dependencies=[Depends(require_admin)])
def audit_logs(db: Session = Depends(get_db)) -> list[dict]:
    logs = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)).all()
    return [{"id": row.id, "user_id": row.user_id, "method": row.method, "path": row.path,
             "status_code": row.status_code, "created_at": row.created_at} for row in logs]
