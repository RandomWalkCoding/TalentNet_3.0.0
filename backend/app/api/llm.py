from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.llm import AISummaryResponse, LLMStatusResponse, OutreachResponse
from app.services.llm import LLMService

router = APIRouter(tags=["llm"])
service = LLMService()


@router.get("/llm/status", response_model=LLMStatusResponse)
def get_llm_status() -> LLMStatusResponse:
    return service.get_status()


@router.post("/candidates/{candidate_id}/generate-summary", response_model=AISummaryResponse)
def generate_summary(
    candidate_id: str, db: Session = Depends(get_db)
) -> AISummaryResponse:
    return service.generate_summary(db, candidate_id)


@router.post("/candidates/{candidate_id}/generate-outreach", response_model=OutreachResponse)
def generate_outreach(
    candidate_id: str, db: Session = Depends(get_db)
) -> OutreachResponse:
    return service.generate_outreach(db, candidate_id)
