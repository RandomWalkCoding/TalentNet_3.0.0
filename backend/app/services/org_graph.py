from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Candidate, CandidateScore, Company
from app.schemas.org_graph import OrgGraphEdge, OrgGraphNode, OrgGraphResponse


class OrgGraphService:
    def get_graph(self, db: Session, company_id: str | None = None) -> OrgGraphResponse:
        statement = (
            select(Candidate)
            .options(
                selectinload(Candidate.current_company),
                selectinload(Candidate.evidence_items),
                selectinload(Candidate.scores),
            )
            .order_by(Candidate.current_company_id, Candidate.department, Candidate.name)
        )
        if company_id:
            statement = statement.where(Candidate.current_company_id == company_id)
        candidates = list(db.scalars(statement).all())
        company_ids = {candidate.current_company_id for candidate in candidates}
        companies = {
            company.id: company
            for company in db.scalars(select(Company).where(Company.id.in_(company_ids))).all()
        } if company_ids else {}

        nodes: dict[str, OrgGraphNode] = {}
        edges: list[OrgGraphEdge] = []
        for company in companies.values():
            nodes[f"company:{company.id}"] = OrgGraphNode(
                id=f"company:{company.id}",
                label=company.name,
                type="company",
                status=company.monitor_status,
                meta={"industry": company.industry, "company_id": company.id, "company_name": company.name},
            )
        for candidate in candidates:
            department = candidate.department or "Unknown Department"
            dept_id = f"department:{candidate.current_company_id}:{department}"
            nodes.setdefault(
                dept_id,
                OrgGraphNode(
                    id=dept_id,
                    label=department,
                    type="department",
                    status="confirmed",
                    meta={"company_id": candidate.current_company_id},
                ),
            )
            candidate_id = f"candidate:{candidate.id}"
            latest_score = self._latest_score(candidate.scores)
            status = self._node_status(latest_score)
            nodes[candidate_id] = OrgGraphNode(
                id=candidate_id,
                label=candidate.name,
                type="candidate",
                status=status,
                meta={
                    "title": candidate.title,
                    "domain": candidate.domain,
                    "company_id": candidate.current_company_id,
                    "company_name": candidate.current_company.name if candidate.current_company else None,
                    "department": candidate.department,
                    "location": candidate.location,
                    "risk_score": latest_score.risk_score if latest_score else None,
                    "risk_level": latest_score.risk_level if latest_score else None,
                },
            )
            edges.append(
                OrgGraphEdge(
                    source=f"company:{candidate.current_company_id}",
                    target=dept_id,
                    relation="has_department",
                    confidence=1,
                )
            )
            edges.append(
                OrgGraphEdge(
                    source=dept_id,
                    target=candidate_id,
                    relation="current_member",
                    confidence=0.9 if candidate.evidence_items else 0.65,
                )
            )
            for evidence in candidate.evidence_items[:2]:
                evidence_id = f"evidence:{evidence.id}"
                nodes[evidence_id] = OrgGraphNode(
                    id=evidence_id,
                    label=evidence.title[:80],
                    type="evidence",
                    status="confirmed" if evidence.confirmed_by_user else "suspected",
                    meta={"source": evidence.source, "confidence": evidence.confidence},
                )
                edges.append(
                    OrgGraphEdge(
                        source=candidate_id,
                        target=evidence_id,
                        relation="supported_by",
                        confidence=evidence.confidence,
                    )
                )
        return OrgGraphResponse(company_id=company_id, nodes=list(nodes.values()), edges=edges)

    def _latest_score(self, scores: list[CandidateScore]) -> CandidateScore | None:
        return sorted(scores, key=lambda item: (item.created_at, item.id), reverse=True)[0] if scores else None

    def _node_status(self, score: CandidateScore | None) -> str:
        if score is None or score.risk_level == "needs_review":
            return "suspected"
        if score.risk_level in {"very_high", "high"}:
            return "confirmed"
        return "watching"
