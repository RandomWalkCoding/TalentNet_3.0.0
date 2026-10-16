from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Candidate, Company, Evidence
from app.schemas.evidence import EvidenceCreate, EvidenceRead, EvidenceUpdate
from app.services.risk_scoring import RiskScoringService


class EvidenceRepository:
    def __init__(self) -> None:
        self.scoring = RiskScoringService()

    def list(self, db: Session, candidate_id: str | None = None) -> list[EvidenceRead]:
        statement = select(Evidence).order_by(Evidence.observed_at.desc())
        if candidate_id:
            statement = statement.where(Evidence.candidate_id == candidate_id)
        evidence_items = db.scalars(statement).all()
        return [EvidenceRead.model_validate(item) for item in evidence_items]

    def create(self, db: Session, payload: EvidenceCreate) -> Evidence:
        self._validate_candidate_and_company(db, payload.candidate_id, payload.company_id)
        duplicate = self._find_duplicate(
            db,
            candidate_id=payload.candidate_id,
            source=payload.source,
            title=payload.title,
            url=payload.url,
            summary=payload.summary,
            exclude_id=None,
        )
        if duplicate is not None:
            raise AppError(
                code="EVIDENCE_DUPLICATED",
                message="Evidence already exists for this candidate and source.",
                status_code=409,
                details={"evidence_id": duplicate.id},
            )

        evidence = Evidence(
            id=f"ev_{uuid4().hex}",
            candidate_id=payload.candidate_id,
            company_id=payload.company_id,
            source=payload.source,
            title=payload.title,
            url=payload.url,
            screenshot_path=payload.screenshot_path,
            observed_at=payload.observed_at or datetime.now(timezone.utc),
            event_time=payload.event_time,
            summary=payload.summary,
            raw_text=payload.raw_text,
            confidence=payload.confidence,
            confirmed_by_user=payload.confirmed_by_user,
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)
        if evidence.confirmed_by_user:
            self.scoring.refresh_candidate_score(db, evidence.candidate_id)
        return evidence

    def update(self, db: Session, evidence_id: str, payload: EvidenceUpdate) -> Evidence:
        evidence = self._get_evidence(db, evidence_id)
        changes = payload.model_dump(exclude_unset=True)
        company_id = changes.get("company_id", evidence.company_id)
        self._validate_candidate_and_company(db, evidence.candidate_id, company_id)

        source = changes.get("source", evidence.source)
        title = changes.get("title", evidence.title)
        url = changes.get("url", evidence.url)
        summary = changes.get("summary", evidence.summary)
        duplicate = self._find_duplicate(
            db,
            candidate_id=evidence.candidate_id,
            source=source,
            title=title,
            url=url,
            summary=summary,
            exclude_id=evidence.id,
        )
        if duplicate is not None:
            raise AppError(
                code="EVIDENCE_DUPLICATED",
                message="Evidence already exists for this candidate and source.",
                status_code=409,
                details={"evidence_id": duplicate.id},
            )

        for field, value in changes.items():
            setattr(evidence, field, value)
        db.commit()
        db.refresh(evidence)
        if evidence.confirmed_by_user:
            self.scoring.refresh_candidate_score(db, evidence.candidate_id)
        return evidence

    def confirm(self, db: Session, evidence_id: str) -> Evidence:
        evidence = self._get_evidence(db, evidence_id)
        evidence.confirmed_by_user = True
        db.commit()
        db.refresh(evidence)
        self.scoring.refresh_candidate_score(db, evidence.candidate_id)
        return evidence

    def _get_evidence(self, db: Session, evidence_id: str) -> Evidence:
        evidence = db.get(Evidence, evidence_id)
        if evidence is None:
            raise AppError(
                code="EVIDENCE_NOT_FOUND",
                message="Evidence does not exist.",
                status_code=404,
            )
        return evidence

    def _validate_candidate_and_company(
        self, db: Session, candidate_id: str, company_id: str | None
    ) -> None:
        if db.get(Candidate, candidate_id) is None:
            raise AppError(
                code="CANDIDATE_NOT_FOUND",
                message="Candidate does not exist.",
                status_code=404,
            )
        if company_id is not None and db.get(Company, company_id) is None:
            raise AppError(
                code="COMPANY_NOT_FOUND",
                message="Company does not exist.",
                status_code=404,
            )

    def _find_duplicate(
        self,
        db: Session,
        candidate_id: str,
        source: str,
        title: str,
        url: str | None,
        summary: str,
        exclude_id: str | None,
    ) -> Evidence | None:
        statement = select(Evidence).where(
            Evidence.candidate_id == candidate_id,
            Evidence.source == source,
        )
        if exclude_id is not None:
            statement = statement.where(Evidence.id != exclude_id)
        candidates = db.scalars(statement).all()
        normalized_url = self._normalize(url)
        normalized_title = self._normalize(title)
        normalized_summary = self._normalize(summary)
        for item in candidates:
            if normalized_url and self._normalize(item.url) == normalized_url:
                return item
            if (
                self._normalize(item.title) == normalized_title
                and self._normalize(item.summary) == normalized_summary
            ):
                return item
        return None

    def _normalize(self, value: str | None) -> str:
        return " ".join((value or "").strip().lower().split())
