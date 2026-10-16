from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.sourcing import (
    CandidateLeadSaveRequest,
    CandidateLeadSaveResponse,
    TalentSourcingRequest,
    TalentSourcingResponse,
)
from app.services.sourcing import TalentSourcingService

router = APIRouter(prefix="/sourcing", tags=["sourcing"])
service = TalentSourcingService()


@router.post("/run", response_model=TalentSourcingResponse)
def run_talent_sourcing(
    payload: TalentSourcingRequest, db: Session = Depends(get_db)
) -> TalentSourcingResponse:
    return service.run_sourcing(db, payload)


@router.post("/leads/save", response_model=CandidateLeadSaveResponse)
def save_candidate_lead(
    payload: CandidateLeadSaveRequest, db: Session = Depends(get_db)
) -> CandidateLeadSaveResponse:
    return service.save_candidate_lead(db, payload)
