from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.candidate import CandidateScoreRead
from app.services.risk_scoring import RiskScoringService

router = APIRouter(prefix="/candidates", tags=["scoring"])
service = RiskScoringService()


@router.get("/{candidate_id}/score", response_model=CandidateScoreRead)
def get_candidate_score(
    candidate_id: str, db: Session = Depends(get_db)
) -> CandidateScoreRead:
    return CandidateScoreRead.model_validate(service.get_latest_score(db, candidate_id))


@router.post("/{candidate_id}/refresh-score", response_model=CandidateScoreRead)
def refresh_candidate_score(
    candidate_id: str, db: Session = Depends(get_db)
) -> CandidateScoreRead:
    return CandidateScoreRead.model_validate(service.refresh_candidate_score(db, candidate_id))
