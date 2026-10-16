from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Candidate, CandidateScore, Company
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate


def list_companies(db: Session) -> list[CompanyRead]:
    companies = db.scalars(select(Company).order_by(Company.name)).all()
    candidates = db.scalars(select(Candidate)).all()
    scores = db.scalars(select(CandidateScore)).all()
    latest_score_by_candidate = {score.candidate_id: score for score in scores}

    result: list[CompanyRead] = []
    for company in companies:
        company_candidates = [
            candidate for candidate in candidates if candidate.current_company_id == company.id
        ]
        high_risk_count = sum(
            1
            for candidate in company_candidates
            if latest_score_by_candidate.get(candidate.id)
            and latest_score_by_candidate[candidate.id].risk_level in {"very_high", "high"}
        )
        result.append(
            CompanyRead(
                id=company.id,
                name=company.name,
                industry=company.industry,
                website=company.website,
                monitor_status=company.monitor_status,
                last_scanned_at=company.last_scanned_at,
                candidate_count=len(company_candidates),
                high_risk_count=high_risk_count,
            )
        )
    return result


def create_company(db: Session, payload: CompanyCreate) -> CompanyRead:
    existing = _find_company_by_name(db, payload.name)
    if existing is not None:
        raise AppError(
            code="COMPANY_DUPLICATED",
            message="Company with the same name already exists.",
            status_code=409,
            details={"company_id": existing.id},
        )
    company = Company(
        id=f"company_{uuid4().hex}",
        name=payload.name,
        industry=payload.industry,
        website=payload.website,
        monitor_status=payload.monitor_status,
        last_scanned_at=None,
    )
    db.add(company)
    db.commit()
    return _company_read(db, company)


def update_company(db: Session, company_id: str, payload: CompanyUpdate) -> CompanyRead:
    company = db.get(Company, company_id)
    if company is None:
        raise AppError(
            code="COMPANY_NOT_FOUND",
            message="Company does not exist.",
            status_code=404,
        )
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        existing = _find_company_by_name(db, changes["name"])
        if existing is not None and existing.id != company.id:
            raise AppError(
                code="COMPANY_DUPLICATED",
                message="Company with the same name already exists.",
                status_code=409,
                details={"company_id": existing.id},
            )
    for field, value in changes.items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return _company_read(db, company)


def _find_company_by_name(db: Session, name: str) -> Company | None:
    normalized = name.strip().lower()
    companies = db.scalars(select(Company)).all()
    for company in companies:
        if company.name.strip().lower() == normalized:
            return company
    return None


def _company_read(db: Session, company: Company) -> CompanyRead:
    candidates = db.scalars(select(Candidate).where(Candidate.current_company_id == company.id)).all()
    scores = db.scalars(select(CandidateScore)).all()
    latest_score_by_candidate = {score.candidate_id: score for score in scores}
    high_risk_count = sum(
        1
        for candidate in candidates
        if latest_score_by_candidate.get(candidate.id)
        and latest_score_by_candidate[candidate.id].risk_level in {"very_high", "high"}
    )
    return CompanyRead(
        id=company.id,
        name=company.name,
        industry=company.industry,
        website=company.website,
        monitor_status=company.monitor_status,
        last_scanned_at=company.last_scanned_at,
        candidate_count=len(candidates),
        high_risk_count=high_risk_count,
    )
