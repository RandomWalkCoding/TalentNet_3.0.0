import csv
from io import StringIO
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models import Candidate, CandidateScore, Company
from app.schemas.candidate import (
    CandidateCreate,
    CandidateDetail,
    CandidateImportResult,
    CandidateListItem,
    CandidateScoreRead,
    CandidateUpdate,
)
from app.schemas.evidence import EvidenceRead
from app.services.risk_scoring import RiskScoringService

CLUE_DOMAINS = {"AI 搜索线索"}


def _latest_score(candidate: Candidate) -> CandidateScore | None:
    if not candidate.scores:
        return None
    return sorted(candidate.scores, key=lambda score: (score.created_at, score.id), reverse=True)[0]


def list_candidates(db: Session, company_id: str | None = None) -> list[CandidateListItem]:
    statement = (
        select(Candidate)
        .options(selectinload(Candidate.current_company), selectinload(Candidate.scores))
        .order_by(Candidate.name)
    )
    if company_id:
        statement = statement.where(Candidate.current_company_id == company_id)
    candidates = db.scalars(statement).all()

    items: list[CandidateListItem] = []
    for candidate in candidates:
        if _is_clue_candidate(candidate):
            continue
        score = _latest_score(candidate)
        items.append(
            CandidateListItem(
                id=candidate.id,
                name=candidate.name,
                current_company_id=candidate.current_company_id,
                company_name=candidate.current_company.name,
                title=candidate.title,
                department=candidate.department,
                location=candidate.location,
                domain=candidate.domain,
                follow_status=candidate.follow_status,
                risk_level=score.risk_level if score else None,
                risk_score=score.risk_score if score else None,
                confidence_score=score.confidence_score if score else None,
            )
        )
    return items


def _is_clue_candidate(candidate: Candidate) -> bool:
    return candidate.domain in CLUE_DOMAINS or candidate.name.startswith("AI 搜索线索")


def create_candidate(db: Session, payload: CandidateCreate) -> CandidateDetail:
    _ensure_company(db, payload.current_company_id)
    duplicate = _find_duplicate_candidate(db, payload.name, payload.current_company_id)
    if duplicate is not None:
        raise AppError(
            code="CANDIDATE_DUPLICATED",
            message="Candidate with the same name already exists in this company.",
            status_code=409,
            details={"candidate_id": duplicate.id},
        )
    candidate = Candidate(
        id=f"cand_{uuid4().hex}",
        name=payload.name,
        current_company_id=payload.current_company_id,
        title=payload.title,
        department=payload.department,
        location=payload.location,
        domain=payload.domain,
        profile_summary=payload.profile_summary,
        source_type=payload.source_type,
        follow_status=payload.follow_status,
    )
    db.add(candidate)
    db.commit()
    RiskScoringService().refresh_candidate_score(db, candidate.id)
    return get_candidate_detail(db, candidate.id)


def update_candidate(db: Session, candidate_id: str, payload: CandidateUpdate) -> CandidateDetail:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise AppError(
            code="CANDIDATE_NOT_FOUND",
            message="Candidate does not exist.",
            status_code=404,
        )
    changes = payload.model_dump(exclude_unset=True)
    target_company_id = changes.get("current_company_id", candidate.current_company_id)
    _ensure_company(db, target_company_id)
    target_name = changes.get("name", candidate.name)
    duplicate = _find_duplicate_candidate(db, target_name, target_company_id)
    if duplicate is not None and duplicate.id != candidate.id:
        raise AppError(
            code="CANDIDATE_DUPLICATED",
            message="Candidate with the same name already exists in this company.",
            status_code=409,
            details={"candidate_id": duplicate.id},
        )
    for field, value in changes.items():
        setattr(candidate, field, value)
    db.commit()
    db.refresh(candidate)
    RiskScoringService().refresh_candidate_score(db, candidate.id)
    return get_candidate_detail(db, candidate.id)


def import_candidates_csv(db: Session, content: str) -> CandidateImportResult:
    reader = csv.DictReader(StringIO(content))
    required = {"name", "company_name", "title"}
    if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
        raise AppError(
            code="CSV_SCHEMA_INVALID",
            message="CSV must include name, company_name and title columns.",
            status_code=422,
            details={"required_columns": sorted(required)},
        )

    created_ids: list[str] = []
    duplicate_count = 0
    errors: list[str] = []
    for line_number, row in enumerate(reader, start=2):
        try:
            name = (row.get("name") or "").strip()
            company_name = (row.get("company_name") or "").strip()
            title = (row.get("title") or "").strip()
            if not name or not company_name or not title:
                raise ValueError("name, company_name and title are required.")
            company = _find_or_create_company(
                db,
                name=company_name,
                industry=(row.get("industry") or "Unknown").strip() or "Unknown",
                website=(row.get("website") or "").strip() or None,
            )
            duplicate = _find_duplicate_candidate(db, name, company.id)
            if duplicate is not None:
                duplicate_count += 1
                continue
            candidate = Candidate(
                id=f"cand_{uuid4().hex}",
                name=name,
                current_company_id=company.id,
                title=title,
                department=(row.get("department") or "").strip() or None,
                location=(row.get("location") or "").strip() or None,
                domain=(row.get("domain") or "").strip() or None,
                profile_summary=(row.get("profile_summary") or "").strip() or None,
                source_type="csv_import",
                follow_status="new",
            )
            db.add(candidate)
            db.commit()
            RiskScoringService().refresh_candidate_score(db, candidate.id)
            created_ids.append(candidate.id)
        except Exception as exc:
            db.rollback()
            errors.append(f"line {line_number}: {exc}")
    return CandidateImportResult(
        created_count=len(created_ids),
        duplicate_count=duplicate_count,
        failed_count=len(errors),
        created_candidate_ids=created_ids,
        errors=errors,
    )


def get_candidate_detail(db: Session, candidate_id: str) -> CandidateDetail:
    candidate = db.scalar(
        select(Candidate)
        .where(Candidate.id == candidate_id)
        .options(
            selectinload(Candidate.current_company),
            selectinload(Candidate.evidence_items),
            selectinload(Candidate.scores),
        )
    )
    if candidate is None:
        raise AppError(
            code="CANDIDATE_NOT_FOUND",
            message="Candidate does not exist.",
            status_code=404,
        )

    score = _latest_score(candidate)
    return CandidateDetail(
        id=candidate.id,
        name=candidate.name,
        current_company_id=candidate.current_company_id,
        company_name=candidate.current_company.name,
        title=candidate.title,
        department=candidate.department,
        location=candidate.location,
        domain=candidate.domain,
        profile_summary=candidate.profile_summary,
        source_type=candidate.source_type,
        follow_status=candidate.follow_status,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
        latest_score=CandidateScoreRead.model_validate(score) if score else None,
        evidence=[
            EvidenceRead.model_validate(item)
            for item in sorted(
                candidate.evidence_items, key=lambda evidence: evidence.observed_at, reverse=True
            )
        ],
    )


def _ensure_company(db: Session, company_id: str) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise AppError(
            code="COMPANY_NOT_FOUND",
            message="Company does not exist.",
            status_code=404,
        )
    return company


def _find_duplicate_candidate(db: Session, name: str, company_id: str) -> Candidate | None:
    normalized = name.strip().lower()
    candidates = db.scalars(
        select(Candidate).where(Candidate.current_company_id == company_id)
    ).all()
    for candidate in candidates:
        if candidate.name.strip().lower() == normalized:
            return candidate
    return None


def _find_or_create_company(
    db: Session, name: str, industry: str, website: str | None
) -> Company:
    normalized = name.strip().lower()
    companies = db.scalars(select(Company)).all()
    for company in companies:
        if company.name.strip().lower() == normalized:
            return company
    company = Company(
        id=f"company_{uuid4().hex}",
        name=name,
        industry=industry,
        website=website,
        monitor_status="active",
        last_scanned_at=None,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company
