from contextvars import ContextVar
from datetime import datetime, timezone
from hashlib import sha256

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.workspace import DemoSession, DemoUser

current_user_id = ContextVar("current_user_id", default="demo_manager")


def seed_users(db: Session) -> None:
    for user_id, name, role in (
        ("demo_manager", "演示管理员", "admin"),
        ("demo_recruiter", "招聘顾问", "member"),
        ("demo_observer", "观察成员", "member"),
    ):
        if db.get(DemoUser, user_id) is None:
            db.add(DemoUser(id=user_id, name=name, role=role, active=True))
    db.commit()


def resolve_user(db: Session, token: str | None) -> DemoUser:
    if not token:
        # A local-only workspace opens as the demo administrator by default.
        user = db.get(DemoUser, "demo_manager")
    else:
        session = db.get(DemoSession, sha256(token.encode()).hexdigest())
        if session is None or session.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
            raise AppError("SESSION_INVALID", "演示会话已过期，请切换演示用户。", 401)
        user = db.get(DemoUser, session.user_id)
    if user is None or not user.active:
        raise AppError("USER_INACTIVE", "演示用户不可用。", 403)
    return user


def require_admin(request: Request) -> None:
    if request.state.user_role != "admin":
        raise AppError("FORBIDDEN", "此页面仅管理员可访问。", 403)
