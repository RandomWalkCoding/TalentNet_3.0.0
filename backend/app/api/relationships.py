from hashlib import sha256
from itertools import combinations
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.errors import AppError
from app.models import Candidate, Company, Evidence
from app.models.workspace import Relationship

router = APIRouter(tags=["relationships"])


class RelationshipDecision(BaseModel):
    status: Literal["confirmed", "rejected", "suspected"]


def read_relationship(row: Relationship, db: Session) -> dict:
    source = db.get(Candidate, row.source_candidate_id)
    target = db.get(Candidate, row.target_candidate_id)
    evidence = db.scalars(select(Evidence).where(Evidence.id.in_(row.evidence_ids))).all() if row.evidence_ids else []
    return {"id": row.id, "company_id": row.company_id,
            "source_candidate_id": row.source_candidate_id, "target_candidate_id": row.target_candidate_id,
            "source_name": source.name if source else row.source_candidate_id,
            "target_name": target.name if target else row.target_candidate_id,
            "relation": row.relation, "confidence": row.confidence, "evidence_ids": row.evidence_ids,
            "status": row.status, "explanation": row.explanation,
            "evidence": [{"id": e.id, "title": e.title, "candidate_id": e.candidate_id} for e in evidence]}


@router.get("/relationships")
def list_relationships(company_id: str | None = Query(None), db: Session = Depends(get_db)) -> list[dict]:
    query = select(Relationship).order_by(Relationship.id)
    if company_id:
        query = query.where(Relationship.company_id == company_id)
    return [read_relationship(row, db) for row in db.scalars(query).all()]


@router.post("/relationship-graph/rebuild")
def rebuild(company_id: str | None = Query(None), db: Session = Depends(get_db)) -> list[dict]:
    if company_id and not db.get(Company, company_id):
        raise AppError("COMPANY_NOT_FOUND", "公司不存在。", 404)
    query = select(Candidate).options(selectinload(Candidate.evidence_items)).order_by(Candidate.id)
    if company_id:
        query = query.where(Candidate.current_company_id == company_id)
    groups: dict[tuple[str, str], list[Candidate]] = {}
    generated_ids: set[str] = set()
    for candidate in db.scalars(query).all():
        # Candidate-provided metadata suggests a relationship, never establishes it.
        if candidate.department:
            groups.setdefault((candidate.current_company_id, candidate.department), []).append(candidate)
    for (company, department), candidates in groups.items():
        # Bound pair generation for a usable local demo on imported datasets.
        for source, target in combinations(candidates[:30], 2):
            key = sha256(f"{source.id}|{target.id}|same_department".encode()).hexdigest()[:40]
            generated_ids.add(key)
            evidence_ids = [e.id for c in (source, target) for e in c.evidence_items if e.confirmed_by_user]
            row = db.get(Relationship, key)
            if row is None:
                row = Relationship(id=key, company_id=company, source_candidate_id=source.id,
                                   target_candidate_id=target.id, relation="same_department", status="suspected")
                db.add(row)
            row.evidence_ids = evidence_ids
            row.company_id = company
            row.confidence = 0.35
            row.explanation = f"两人的录入资料均标注部门“{department}”；仅作为待人工审核的关系线索。关联的个人证据不自动证明两人存在直接关系。"
    stale_query = select(Relationship).where(Relationship.relation == "same_department")
    if company_id:
        stale_query = stale_query.where(Relationship.company_id == company_id)
    for row in db.scalars(stale_query).all():
        if row.id not in generated_ids and row.status == "suspected":
            db.delete(row)
    db.commit()
    return list_relationships(company_id, db)


@router.patch("/relationships/{relationship_id}")
def decide(relationship_id: str, payload: RelationshipDecision, db: Session = Depends(get_db)) -> dict:
    row = db.get(Relationship, relationship_id)
    if row is None:
        raise AppError("RELATIONSHIP_NOT_FOUND", "关系线索不存在。", 404)
    row.status = payload.status
    db.commit()
    return read_relationship(row, db)
