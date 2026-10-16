from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.identity import current_user_id
from app.models import Candidate, CandidateScore, TalentPoolItem
from app.schemas.talent_pool import TalentPoolItemRead, TalentPoolUpdate

RISK_SORT = {
    "very_high": 5,
    "high": 4,
    "medium": 3,
    "needs_review": 2,
    "low": 1,
    None: 0,
}

WINDOW_SORT = {
    "未来 1 周内优先触达": 5,
    "未来 2 周内": 4,
    "未来 1 个月观察": 3,
    "证据不足，需人工核实": 2,
    "暂不建议主动触达": 1,
    None: 0,
}


def add_candidate_to_pool(db: Session, candidate_id: str) -> TalentPoolItemRead:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise AppError(
            code="CANDIDATE_NOT_FOUND",
            message="Candidate does not exist.",
            status_code=404,
        )

    existing = db.scalar(
        select(TalentPoolItem).where(TalentPoolItem.candidate_id == candidate_id)
    )
    if existing is None:
        existing = TalentPoolItem(
            id=f"pool_{uuid4().hex}",
            candidate_id=candidate_id,
            owner_user_id=current_user_id.get(),
            priority="high",
            status="watching",
            note="",
        )
        db.add(existing)
        candidate.follow_status = "in_pool"
        db.commit()
        db.refresh(existing)

    return _read_item(db, existing.id)


def list_talent_pool(
    db: Session,
    company_id: str | None = None,
    risk_level: str | None = None,
    status: str | None = None,
    pending_feedback: bool = False,
) -> list[TalentPoolItemRead]:
    items = db.scalars(
        select(TalentPoolItem)
        .options(
            selectinload(TalentPoolItem.candidate).selectinload(Candidate.current_company),
            selectinload(TalentPoolItem.candidate).selectinload(Candidate.scores),
        )
        .order_by(TalentPoolItem.added_at.desc())
    ).all()

    result = [_to_read(item) for item in items]
    if company_id:
        result = [item for item in result if item.company_id == company_id]
    if risk_level:
        result = [item for item in result if item.risk_level == risk_level]
    if status:
        result = [item for item in result if item.status == status]
    if pending_feedback:
        result = [item for item in result if item.status in {"watching", "contacted"}]

    return sorted(
        result,
        key=lambda item: (
            RISK_SORT.get(item.risk_level, 0),
            item.risk_score or 0,
            WINDOW_SORT.get(item.recommended_window, 0),
            item.added_at,
        ),
        reverse=True,
    )


def update_talent_pool_item(
    db: Session, item_id: str, payload: TalentPoolUpdate
) -> TalentPoolItemRead:
    item = db.get(TalentPoolItem, item_id)
    if item is None:
        raise AppError(
            code="TALENT_POOL_ITEM_NOT_FOUND",
            message="Talent pool item does not exist.",
            status_code=404,
        )

    if payload.priority is not None:
        item.priority = payload.priority
    if payload.status is not None:
        item.status = payload.status
        item.candidate.follow_status = payload.status
    if payload.note is not None:
        item.note = payload.note

    db.commit()
    return _read_item(db, item_id)


def delete_talent_pool_item(db: Session, item_id: str) -> None:
    item = db.get(TalentPoolItem, item_id)
    if item is None:
        raise AppError(
            code="TALENT_POOL_ITEM_NOT_FOUND",
            message="Talent pool item does not exist.",
            status_code=404,
        )
    item.candidate.follow_status = "new"
    db.delete(item)
    db.commit()


def _read_item(db: Session, item_id: str) -> TalentPoolItemRead:
    item = db.scalar(
        select(TalentPoolItem)
        .where(TalentPoolItem.id == item_id)
        .options(
            selectinload(TalentPoolItem.candidate).selectinload(Candidate.current_company),
            selectinload(TalentPoolItem.candidate).selectinload(Candidate.scores),
        )
    )
    if item is None:
        raise AppError(
            code="TALENT_POOL_ITEM_NOT_FOUND",
            message="Talent pool item does not exist.",
            status_code=404,
        )
    return _to_read(item)


def _latest_score(candidate: Candidate) -> CandidateScore | None:
    if not candidate.scores:
        return None
    return sorted(candidate.scores, key=lambda score: (score.created_at, score.id), reverse=True)[0]


def _to_read(item: TalentPoolItem) -> TalentPoolItemRead:
    candidate = item.candidate
    score = _latest_score(candidate)
    return TalentPoolItemRead(
        id=item.id,
        candidate_id=candidate.id,
        owner_user_id=item.owner_user_id,
        candidate_name=candidate.name,
        company_id=candidate.current_company_id,
        company_name=candidate.current_company.name,
        title=candidate.title,
        department=candidate.department,
        domain=candidate.domain,
        location=candidate.location,
        priority=item.priority,
        status=item.status,
        note=item.note,
        risk_level=score.risk_level if score else None,
        risk_score=score.risk_score if score else None,
        confidence_score=score.confidence_score if score else None,
        recommended_window=score.recommended_window if score else None,
        added_at=item.added_at,
    )
