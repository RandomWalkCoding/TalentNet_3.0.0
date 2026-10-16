from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.identity import current_user_id
from app.models import Badcase, Candidate, CandidateScore, Feedback, TalentPoolItem
from app.schemas.feedback import FeedbackCreate, FeedbackRead

VALID_OUTCOMES = {
    "contacted",
    "no_response",
    "rejected",
    "not_interested",
    "interested",
    "in_process",
    "offer_sent",
    "hired",
    "bad_prediction",
}

OUTCOME_TO_STATUS = {
    "contacted": "contacted",
    "no_response": "contacted",
    "rejected": "closed",
    "not_interested": "closed",
    "interested": "contacted",
    "in_process": "in_process",
    "offer_sent": "in_process",
    "hired": "closed",
    "bad_prediction": "watching",
}


def create_feedback(db: Session, payload: FeedbackCreate) -> FeedbackRead:
    if payload.outcome not in VALID_OUTCOMES:
        raise AppError(
            code="INVALID_OUTCOME",
            message="Feedback outcome is not supported.",
            status_code=422,
            details={"outcome": payload.outcome},
        )

    candidate = db.get(Candidate, payload.candidate_id)
    if candidate is None:
        raise AppError(
            code="CANDIDATE_NOT_FOUND",
            message="Candidate does not exist.",
            status_code=404,
        )

    feedback = Feedback(
        id=f"feedback_{uuid4().hex}",
        candidate_id=payload.candidate_id,
        user_id=current_user_id.get(),
        outcome=payload.outcome,
        contact_channel=payload.contact_channel,
        note=payload.note,
        contacted_at=payload.contacted_at or datetime.now(timezone.utc),
    )
    db.add(feedback)

    next_status = OUTCOME_TO_STATUS[payload.outcome]
    candidate.follow_status = next_status
    pool_item = db.scalar(
        select(TalentPoolItem).where(TalentPoolItem.candidate_id == payload.candidate_id)
    )
    if pool_item is not None:
        pool_item.status = next_status

    if payload.outcome == "bad_prediction":
        score = db.scalar(
            select(CandidateScore)
            .where(CandidateScore.candidate_id == payload.candidate_id)
            .order_by(CandidateScore.created_at.desc(), CandidateScore.id.desc())
        )
        db.add(
            Badcase(
                id=f"badcase_{uuid4().hex}",
                candidate_id=payload.candidate_id,
                score_id=score.id if score else None,
                feedback_id=feedback.id,
                error_type="wrong_reason",
                user_reason=payload.note,
            )
        )

    db.commit()
    db.refresh(feedback)
    return FeedbackRead.model_validate(feedback)


def list_feedback(db: Session, candidate_id: str | None = None) -> list[FeedbackRead]:
    statement = select(Feedback).order_by(Feedback.created_at.desc())
    if candidate_id:
        statement = statement.where(Feedback.candidate_id == candidate_id)
    return [FeedbackRead.model_validate(item) for item in db.scalars(statement).all()]
