from sqlalchemy import select
from uuid import uuid4
from app.core.identity import current_user_id
from app.models.workspace import LLMRun
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models import Candidate, Evidence
from app.schemas.llm import AISummaryResponse, LLMStatusResponse, OutreachResponse
from app.services.llm_gateway import LLMGateway


class LLMService:
    def __init__(self) -> None:
        self.gateway = LLMGateway()

    def get_status(self) -> LLMStatusResponse:
        return LLMStatusResponse.model_validate(self.gateway.status())

    def generate_summary(self, db: Session, candidate_id: str) -> AISummaryResponse:
        candidate = self._get_candidate(db, candidate_id)
        evidence_items = self._get_evidence(db, candidate_id)
        if not evidence_items:
            raise AppError(
                code="EVIDENCE_REQUIRED",
                message="Cannot generate AI summary without evidence.",
                status_code=400,
            )
        latest_score = (
            sorted(candidate.scores, key=lambda score: (score.created_at, score.id), reverse=True)[0]
            if candidate.scores
            else None
        )
        result = self.gateway.generate_summary(candidate, evidence_items, latest_score)
        self._record_run(db, candidate_id, "summary", result)
        return result

    def generate_outreach(self, db: Session, candidate_id: str) -> OutreachResponse:
        candidate = self._get_candidate(db, candidate_id)
        evidence_items = self._get_evidence(db, candidate_id)
        if not evidence_items:
            raise AppError(
                code="EVIDENCE_REQUIRED",
                message="Cannot generate outreach variants without evidence.",
                status_code=400,
            )
        latest_score = (
            sorted(candidate.scores, key=lambda score: (score.created_at, score.id), reverse=True)[0]
            if candidate.scores
            else None
        )
        result = self.gateway.generate_outreach(candidate, evidence_items, latest_score)
        self._record_run(db, candidate_id, "outreach", result)
        return result

    def _record_run(self, db: Session, candidate_id: str, operation: str, result) -> None:
        db.add(LLMRun(id=f"llm_{uuid4().hex}", user_id=current_user_id.get(), candidate_id=candidate_id,
                      operation=operation, provider=result.model_provider, model=result.model_name,
                      used_fallback=result.used_fallback))
        db.commit()

    def _get_candidate(self, db: Session, candidate_id: str) -> Candidate:
        candidate = db.scalar(
            select(Candidate)
            .where(Candidate.id == candidate_id)
            .options(selectinload(Candidate.current_company), selectinload(Candidate.scores))
        )
        if candidate is None:
            raise AppError(
                code="CANDIDATE_NOT_FOUND",
                message="Candidate does not exist.",
                status_code=404,
            )
        return candidate

    def _get_evidence(self, db: Session, candidate_id: str) -> list[Evidence]:
        return list(
            db.scalars(
                select(Evidence)
                .where(Evidence.candidate_id == candidate_id)
                .order_by(Evidence.observed_at.desc())
            ).all()
        )
