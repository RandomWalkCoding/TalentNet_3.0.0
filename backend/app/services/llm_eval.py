from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candidate, Evidence, LLMEvalCase, LLMEvalRun
from app.schemas.llm_eval import (
    DatasetSeedResponse,
    LLMEvalCaseRead,
    LLMEvalResult,
    LLMEvalRunRead,
)
from app.services.llm import LLMService
from app.services.llm_memory import LLMMemoryService


class LLMEvalService:
    def __init__(self) -> None:
        self.llm_service = LLMService()
        self.memory_service = LLMMemoryService()

    def seed_dataset(self, db: Session) -> DatasetSeedResponse:
        existing_ids = set(db.scalars(select(LLMEvalCase.id)).all())
        candidates = list(db.scalars(select(Candidate).order_by(Candidate.id)).all())
        created: list[LLMEvalCase] = []
        for candidate in candidates:
            evidence_ids = list(
                db.scalars(
                    select(Evidence.id)
                    .where(Evidence.candidate_id == candidate.id)
                    .order_by(Evidence.observed_at.desc())
                    .limit(3)
                )
            )
            if not evidence_ids:
                continue
            for task_type in ("summary", "outreach"):
                case_id = f"eval_{candidate.id}_{task_type}"
                if case_id in existing_ids:
                    continue
                created.append(
                    LLMEvalCase(
                        id=case_id,
                        candidate_id=candidate.id,
                        task_type=task_type,
                        expected_evidence_ids=evidence_ids,
                        required_terms=[candidate.name],
                        forbidden_terms=["已经离职", "guaranteed resignation"],
                        min_citations=1,
                        notes="Auto-generated seed evaluation case.",
                    )
                )
        if created:
            db.add_all(created)
            db.commit()
        cases = self.list_cases(db)
        return DatasetSeedResponse(created_cases=len(created), cases=cases)

    def list_cases(self, db: Session) -> list[LLMEvalCaseRead]:
        return [
            LLMEvalCaseRead.model_validate(item)
            for item in db.scalars(select(LLMEvalCase).order_by(LLMEvalCase.id))
        ]

    def run_eval(self, db: Session) -> LLMEvalRunRead:
        if not db.scalar(select(LLMEvalCase.id).limit(1)):
            self.seed_dataset(db)
        cases = list(db.scalars(select(LLMEvalCase).order_by(LLMEvalCase.id)))
        results = [self._run_case(db, case) for case in cases]
        passed = sum(1 for item in results if item.passed)
        average = round(
            sum(item.score for item in results) / len(results), 3
        ) if results else 0
        provider = results[0].model_provider if results else "local"
        model = results[0].model_name if results else "local-structured-v1"
        used_fallback = any(item.used_fallback for item in results)
        run = LLMEvalRun(
            id=f"evalrun_{uuid4().hex}",
            status="completed",
            total_cases=len(results),
            passed_cases=passed,
            failed_cases=len(results) - passed,
            average_score=average,
            model_provider=provider,
            model_name=model,
            used_fallback=used_fallback,
            results=[item.model_dump() for item in results],
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return LLMEvalRunRead.model_validate(run)

    def latest_run(self, db: Session) -> LLMEvalRunRead | None:
        run = db.scalar(select(LLMEvalRun).order_by(LLMEvalRun.created_at.desc()).limit(1))
        return LLMEvalRunRead.model_validate(run) if run else None

    def _run_case(self, db: Session, case: LLMEvalCase) -> LLMEvalResult:
        self.memory_service.build_candidate_memory(db, case.candidate_id)
        if case.task_type == "outreach":
            response = self.llm_service.generate_outreach(db, case.candidate_id)
            output = " ".join(item.message for item in response.variants)
            citations = []
            for item in response.variants:
                citations.extend(item.evidence_ids)
        else:
            response = self.llm_service.generate_summary(db, case.candidate_id)
            output = " ".join(
                [
                    response.summary,
                    response.risk_explanation,
                    " ".join(response.conflict_notes),
                    " ".join(response.limitations),
                ]
            )
            citations = response.cited_evidence_ids
        unique_citations = list(dict.fromkeys(citations))
        expected = set(case.expected_evidence_ids)
        checks = {
            "min_citations": len(unique_citations) >= case.min_citations,
            "expected_citation": bool(expected.intersection(unique_citations)),
            "required_terms": all(term in output for term in case.required_terms),
            "forbidden_terms": not any(term in output for term in case.forbidden_terms),
        }
        score = round(sum(1 for value in checks.values() if value) / len(checks), 3)
        return LLMEvalResult(
            case_id=case.id,
            candidate_id=case.candidate_id,
            task_type=case.task_type,
            passed=all(checks.values()),
            score=score,
            checks=checks,
            citations=unique_citations,
            model_provider=response.model_provider,
            model_name=response.model_name,
            used_fallback=response.used_fallback,
            output_preview=output[:360],
        )
