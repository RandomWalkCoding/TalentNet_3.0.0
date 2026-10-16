from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Candidate, Company
from app.core.errors import AppError
from app.repositories.evidence import EvidenceRepository
from app.repositories.talent_pool import add_candidate_to_pool
from app.schemas.browser_task import BrowserTaskCreate, BrowserTaskRead
from app.schemas.evidence import EvidenceCreate
from app.schemas.sourcing import (
    CandidateLead,
    CandidateLeadSaveRequest,
    CandidateLeadSaveResponse,
    TalentSourcingRequest,
    TalentSourcingResponse,
)
from app.services.browser_task import BrowserTaskService
from app.services.llm_gateway import LLMGateway, LLMRuntime
from app.services.risk_scoring import RiskScoringService
from app.services.source_connections import SourceConnectionService


class TalentSourcingService:
    def __init__(self) -> None:
        self.browser_tasks = BrowserTaskService()
        self.connections = SourceConnectionService()
        self.llm = LLMGateway()
        self.evidence_repository = EvidenceRepository()

    def run_sourcing(self, db: Session, payload: TalentSourcingRequest) -> TalentSourcingResponse:
        connected_sources = self.connections.connected_private_sources()
        plan, plan_runtime = self.llm.generate_sourcing_plan(
            talent_profile=payload.talent_profile,
            target_count=payload.target_count,
            public_site_scope=payload.public_site_scope,
            connected_sources=connected_sources,
            company_name=self._company_name(db, payload.company_id),
            max_tasks=payload.max_tasks,
        )
        if not plan:
            plan = self._build_fallback_plan(payload, connected_sources)
            plan_runtime = LLMRuntime("local", "local-structured-v1", True)

        tasks: list[BrowserTaskRead] = []
        search_results: list[dict[str, str | None]] = []
        per_query_limit = max(1, min(3, payload.target_count))
        for item in plan[: payload.max_tasks]:
            result_cards = self.browser_tasks.collect_search_results(
                item["query"],
                item["target_site"],
                limit=per_query_limit,
            )
            if result_cards:
                for card in result_cards:
                    card["query"] = item["query"]
                    card["target_site"] = item["target_site"]
                    card["user_intent"] = payload.talent_profile
                search_results.extend(result_cards)
                continue
            candidate_urls = self.browser_tasks.discover_candidate_pages(
                item["query"],
                item["target_site"],
                limit=per_query_limit,
            )
            for quick_query in candidate_urls[:per_query_limit]:
                tasks.append(
                    self.browser_tasks.create_pending_search_task(
                        db,
                        BrowserTaskCreate(
                            task_type="search_candidate",
                            query=quick_query,
                            target_site=item["target_site"],
                            candidate_id=payload.candidate_id,
                            company_id=payload.company_id,
                        ),
                    )
                )

        if not search_results:
            search_results = self._search_results_from_tasks(tasks)
        extracted, extraction_runtime = self.llm.extract_candidate_leads_from_search_results(
            user_intent=payload.talent_profile,
            search_results=search_results,
            max_candidates=min(payload.target_count, 50),
        )
        candidate_leads = [
            CandidateLead(
                **item,
                task_id=self._task_id_for_link(tasks, item.get("profile_links") or []),
                candidate_id=self._candidate_id_for_link(tasks, item.get("profile_links") or []),
            )
            for item in extracted
        ]
        final_runtime = extraction_runtime if not extraction_runtime.used_fallback else plan_runtime
        return TalentSourcingResponse(
            query_plan=plan[: payload.max_tasks],
            tasks=tasks,
            extracted_candidates=candidate_leads,
            compliance_note=(
                "The system only reads public or user-authorized pages. It does not store "
                "platform passwords or bypass login, CAPTCHA, anti-scraping, or platform permissions. "
                "Search results are structured into candidate cards before users decide whether to save them."
            ),
            model_provider=final_runtime.provider,
            model_name=final_runtime.model,
            llm_used=not final_runtime.used_fallback,
            used_fallback_plan=plan_runtime.used_fallback,
        )

    def save_candidate_lead(self, db: Session, payload: CandidateLeadSaveRequest) -> CandidateLeadSaveResponse:
        company = self._find_or_create_company(db, payload.current_company or "AI 搜索待归类")
        candidate = self._find_or_create_candidate_from_lead(db, payload, company)
        link = payload.profile_links[0] if payload.profile_links else None
        summary = self._lead_summary(payload)
        if link:
            try:
                self.evidence_repository.create(
                    db,
                    EvidenceCreate(
                        candidate_id=candidate.id,
                        company_id=company.id,
                        source="manual",
                        title=f"{candidate.name} - AI 搜索结果",
                        url=link,
                        observed_at=datetime.now(timezone.utc),
                        event_time=datetime.now(timezone.utc),
                        summary=summary,
                        raw_text=summary,
                        confidence=payload.confidence,
                        confirmed_by_user=True,
                    ),
                )
            except AppError as exc:
                if exc.code != "EVIDENCE_DUPLICATED":
                    raise
        RiskScoringService().refresh_candidate_score(db, candidate.id)
        add_candidate_to_pool(db, candidate.id)
        return CandidateLeadSaveResponse(candidate_id=candidate.id, company_id=company.id)

    def _search_results_from_tasks(self, tasks: list[BrowserTaskRead]) -> list[dict[str, str | None]]:
        results: list[dict[str, str | None]] = []
        for task in tasks:
            draft = task.evidence_draft
            results.append(
                {
                    "task_id": task.id,
                    "query": task.query,
                    "target_site": task.target_site,
                    "title": (draft.title if draft else None) or task.page_title or task.result_summary,
                    "url": (draft.url if draft else None) or task.page_url,
                    "snippet": (draft.summary if draft else None)
                    or (draft.raw_text if draft else None)
                    or task.result_summary
                    or task.error_message,
                    "candidate_id": draft.candidate_id if draft else None,
                    "source": "search_result",
                    "user_intent": task.query,
                }
            )
        return results

    def _task_id_for_link(self, tasks: list[BrowserTaskRead], links: list[str]) -> str | None:
        normalized = {link.rstrip("/") for link in links if isinstance(link, str)}
        for task in tasks:
            draft = task.evidence_draft
            urls = {
                (task.page_url or "").rstrip("/"),
                ((draft.url if draft else None) or "").rstrip("/"),
            }
            if normalized & urls:
                return task.id
        return None

    def _candidate_id_for_link(self, tasks: list[BrowserTaskRead], links: list[str]) -> str | None:
        task_id = self._task_id_for_link(tasks, links)
        if not task_id:
            return None
        for task in tasks:
            if task.id == task_id and task.evidence_draft:
                return task.evidence_draft.candidate_id
        return None

    def _build_fallback_plan(
        self, payload: TalentSourcingRequest, connected_sources: list[str] | None = None
    ) -> list[dict[str, str]]:
        intent = " ".join(payload.talent_profile.split())
        scoped_profile = self._query_from_prompt(intent, payload.public_site_scope)
        plan: list[dict[str, str]] = [
            {
                "target_site": "search_engine",
                "query": scoped_profile,
                "mode": "public_web",
                "reason": "Generate a public web search focused on concrete person/profile pages.",
            }
        ]
        connected = set(connected_sources or [])
        if "linkedin" in connected:
            plan.append(
                {
                    "target_site": "linkedin",
                    "query": self._keywords(intent),
                    "mode": "connected_account",
                    "reason": "Use the connected LinkedIn account to search visible profile pages.",
                }
            )
        plan.extend(
            [
                {
                    "target_site": "company_site",
                    "query": f"{scoped_profile} team staff people profile",
                    "mode": "public_web",
                    "reason": "Find team, people, or project pages that identify candidates.",
                },
                {
                    "target_site": "arxiv",
                    "query": self._keywords(intent),
                    "mode": "public_web",
                    "reason": "Find paper authors and technical domains.",
                },
                {
                    "target_site": "job_site",
                    "query": f"{scoped_profile} hiring team job posting signal",
                    "mode": "public_web",
                    "reason": "Find hiring and team-expansion signals.",
                },
            ]
        )
        if "maimai" in connected:
            plan.append(
                {
                    "target_site": "maimai",
                    "query": self._keywords(intent),
                    "mode": "connected_account",
                    "reason": "Use the connected Maimai account for visible professional profiles.",
                }
            )
        return plan

    def _query_from_prompt(self, prompt: str, public_site_scope: str | None) -> str:
        keywords = self._keywords(prompt)
        lower = prompt.lower()
        if public_site_scope and public_site_scope.strip():
            return f"site:{public_site_scope.strip()} {keywords}"
        if "linkedin" in lower or "领英" in prompt:
            return f"site:linkedin.com/in {keywords}"
        if "github" in lower:
            return f"site:github.com {keywords}"
        return f"{keywords} profile OR LinkedIn OR team"

    def _keywords(self, prompt: str) -> str:
        stopwords = {
            "帮我",
            "请",
            "去",
            "检索",
            "搜索",
            "找到",
            "全部",
            "所有",
            "页面",
            "的人",
            "people",
            "find",
            "search",
            "google",
            "linkedin",
            "profile",
            "all",
            "the",
            "of",
            "for",
        }
        cleaned = prompt
        for token in stopwords:
            cleaned = cleaned.replace(token, " ")
        words = [word.strip(" ，。；;:：()[]{}\"'") for word in cleaned.split()]
        compact = [word for word in words if len(word) >= 2]
        return " ".join(compact[:18]) or prompt[:160]

    def _company_name(self, db: Session, company_id: str | None) -> str | None:
        if not company_id:
            return None
        company = db.get(Company, company_id)
        return company.name if company else None

    def _find_or_create_company(self, db: Session, name: str) -> Company:
        normalized = name.strip().lower()
        for company in db.query(Company).all():
            if company.name.strip().lower() == normalized:
                return company
        company = Company(
            id=f"company_{uuid4().hex}",
            name=name.strip()[:120] or "AI 搜索待归类",
            industry="AI / Technology",
            website=None,
            monitor_status="active",
        )
        db.add(company)
        db.commit()
        db.refresh(company)
        return company

    def _find_or_create_candidate_from_lead(
        self, db: Session, payload: CandidateLeadSaveRequest, company: Company
    ) -> Candidate:
        normalized = payload.full_name.strip().lower()
        for candidate in db.query(Candidate).filter(Candidate.current_company_id == company.id).all():
            if candidate.name.strip().lower() == normalized:
                return candidate
        candidate = Candidate(
            id=f"cand_{uuid4().hex}",
            name=payload.full_name.strip()[:120],
            current_company_id=company.id,
            title=(payload.title or "Technical Talent")[:160],
            department=None,
            location=None,
            domain=None,
            profile_summary=self._lead_summary(payload),
            source_type="ai_search",
            follow_status="new",
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        return candidate

    def _lead_summary(self, payload: CandidateLeadSaveRequest) -> str:
        parts: list[str] = []
        if payload.education:
            parts.append(f"毕业院校/教育背景：{payload.education}")
        if payload.source_snippet:
            parts.append(payload.source_snippet)
        return "\n".join(parts) or "Candidate lead extracted from search result."
