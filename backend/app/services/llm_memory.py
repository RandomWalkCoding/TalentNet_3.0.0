from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Candidate, Evidence, Feedback, LLMMemory
from app.schemas.llm_memory import LLMMemoryCreate, LLMMemoryRead, MemoryBuildResponse


class LLMMemoryService:
    def create_memory(self, db: Session, payload: LLMMemoryCreate) -> LLMMemoryRead:
        if payload.candidate_id and db.get(Candidate, payload.candidate_id) is None:
            raise AppError(
                code="CANDIDATE_NOT_FOUND",
                message="Candidate does not exist.",
                status_code=404,
            )
        memory = LLMMemory(
            id=f"mem_{uuid4().hex}",
            candidate_id=payload.candidate_id,
            scope=payload.scope,
            kind=payload.kind,
            content=payload.content,
            evidence_ids=payload.evidence_ids,
            weight=payload.weight,
            source=payload.source,
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return LLMMemoryRead.model_validate(memory)

    def list_memories(
        self, db: Session, candidate_id: str | None = None
    ) -> list[LLMMemoryRead]:
        statement = select(LLMMemory).order_by(LLMMemory.updated_at.desc())
        if candidate_id:
            statement = statement.where(LLMMemory.candidate_id == candidate_id)
        return [LLMMemoryRead.model_validate(item) for item in db.scalars(statement)]

    def build_candidate_memory(self, db: Session, candidate_id: str) -> MemoryBuildResponse:
        candidate = db.get(Candidate, candidate_id)
        if candidate is None:
            raise AppError(
                code="CANDIDATE_NOT_FOUND",
                message="Candidate does not exist.",
                status_code=404,
            )
        existing = {
            item.content
            for item in db.scalars(
                select(LLMMemory).where(LLMMemory.candidate_id == candidate_id)
            )
        }
        created: list[LLMMemory] = []
        evidence_items = list(
            db.scalars(
                select(Evidence)
                .where(Evidence.candidate_id == candidate_id)
                .order_by(Evidence.observed_at.desc())
                .limit(3)
            )
        )
        if evidence_items:
            content = (
                f"{candidate.name} memory: prioritize evidence-backed reasoning; "
                f"latest signals include "
                + " | ".join(item.summary[:140] for item in evidence_items)
            )
            if content not in existing:
                created.append(
                    LLMMemory(
                        id=f"mem_{uuid4().hex}",
                        candidate_id=candidate_id,
                        scope="candidate",
                        kind="evidence_summary",
                        content=content,
                        evidence_ids=[item.id for item in evidence_items],
                        weight=1.4,
                        source="auto_dataset",
                    )
                )
        feedback_items = list(
            db.scalars(
                select(Feedback)
                .where(Feedback.candidate_id == candidate_id)
                .order_by(Feedback.created_at.desc())
                .limit(3)
            )
        )
        if feedback_items:
            content = (
                f"{candidate.name} memory: outreach tone should account for recent "
                f"feedback outcomes: "
                + ", ".join(item.outcome for item in feedback_items)
            )
            if content not in existing:
                created.append(
                    LLMMemory(
                        id=f"mem_{uuid4().hex}",
                        candidate_id=candidate_id,
                        scope="candidate",
                        kind="feedback_pattern",
                        content=content,
                        evidence_ids=[],
                        weight=1.1,
                        source="auto_feedback",
                    )
                )
        if created:
            db.add_all(created)
            db.commit()
        memories = self.list_memories(db, candidate_id)
        return MemoryBuildResponse(created=len(created), memories=memories)
