from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.feedback import create_feedback, list_feedback
from app.schemas.feedback import FeedbackCreate, FeedbackRead

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackRead)
def post_feedback(payload: FeedbackCreate, db: Session = Depends(get_db)) -> FeedbackRead:
    return create_feedback(db, payload)


@router.get("", response_model=list[FeedbackRead])
def get_feedback(
    candidate_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[FeedbackRead]:
    return list_feedback(db, candidate_id=candidate_id)
