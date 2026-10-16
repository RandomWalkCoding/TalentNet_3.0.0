import json
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.models import Candidate, CandidateScore, Evidence
from app.schemas.llm import AISummaryResponse, OutreachResponse, OutreachVariant


class GatewaySummaryPayload(BaseModel):
    summary: str = Field(min_length=1)
    risk_explanation: str = Field(min_length=1)
    conflict_notes: list[str] = Field(default_factory=list)
    cited_evidence_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class GatewayOutreachVariant(BaseModel):
    tone: str = Field(min_length=1)
    message: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)


class GatewayOutreachPayload(BaseModel):
    variants: list[GatewayOutreachVariant] = Field(min_length=1, max_length=3)
    compliance_note: str = Field(min_length=1)


class GatewaySourcingPlanItem(BaseModel):
    target_site: str = Field(min_length=1)
    query: str = Field(min_length=1)
    mode: str = Field(min_length=1)
    reason: str = Field(default="")


class GatewaySourcingPlanPayload(BaseModel):
    query_plan: list[GatewaySourcingPlanItem] = Field(min_length=1, max_length=12)


class GatewayCandidateProfilePayload(BaseModel):
    is_person_profile: bool = False
    name: str | None = None
    company: str | None = None
    title: str | None = None
    department: str | None = None
    location: str | None = None
    domain: str | None = None
    profile_summary: str | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    rejection_reason: str | None = None


class GatewayCandidateLead(BaseModel):
    full_name: str | None = None
    current_company: str | None = None
    title: str | None = None
    education: str | None = None
    profile_links: list[str] = Field(default_factory=list)
    source_snippet: str | None = None
    evidence: str | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)


class GatewayCandidateLeadPayload(BaseModel):
    candidates: list[GatewayCandidateLead] = Field(default_factory=list)


@dataclass(frozen=True)
class LLMRuntime:
    provider: str
    model: str
    used_fallback: bool


class LLMGateway:
    fallback_provider = "local"
    fallback_model = "local-structured-v1"
    last_error: str | None = None

    def configured(self) -> bool:
        return bool(settings.llm_api_key) and settings.llm_provider != "local"

    def status(self) -> dict[str, Any]:
        return {
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "configured": self.configured(),
            "base_url": self._redact_base_url(settings.llm_base_url),
            "fallback_model": self.fallback_model,
            "last_error": self.last_error,
        }

    def generate_summary(
        self,
        candidate: Candidate,
        evidence_items: list[Evidence],
        latest_score: CandidateScore | None,
    ) -> AISummaryResponse:
        allowed_ids = {item.id for item in evidence_items}
        if self.configured():
            try:
                payload = self._chat_json(
                    [
                        self._system_prompt(),
                        {
                            "role": "user",
                            "content": self._summary_prompt(candidate, evidence_items, latest_score),
                        },
                    ]
                )
                parsed = GatewaySummaryPayload.model_validate(payload)
                cited = self._valid_ids(parsed.cited_evidence_ids, allowed_ids)
                if not cited:
                    raise ValueError("LLM summary did not cite current evidence.")
                return AISummaryResponse(
                    candidate_id=candidate.id,
                    summary=parsed.summary,
                    risk_explanation=parsed.risk_explanation,
                    conflict_notes=parsed.conflict_notes,
                    cited_evidence_ids=cited,
                    limitations=parsed.limitations,
                    model_provider=settings.llm_provider,
                    model_name=settings.llm_model,
                    used_fallback=False,
                )
            except (httpx.HTTPError, ValueError, ValidationError, KeyError, json.JSONDecodeError) as exc:
                self._record_error(exc)
        return self._local_summary(candidate, evidence_items, latest_score)

    def generate_outreach(
        self,
        candidate: Candidate,
        evidence_items: list[Evidence],
        latest_score: CandidateScore | None,
    ) -> OutreachResponse:
        allowed_ids = {item.id for item in evidence_items}
        if self.configured():
            try:
                payload = self._chat_json(
                    [
                        self._system_prompt(),
                        {
                            "role": "user",
                            "content": self._outreach_prompt(candidate, evidence_items, latest_score),
                        },
                    ]
                )
                parsed = GatewayOutreachPayload.model_validate(payload)
                variants = [
                    OutreachVariant(
                        tone=item.tone,
                        message=item.message,
                        evidence_ids=self._valid_ids(item.evidence_ids, allowed_ids),
                    )
                    for item in parsed.variants
                ]
                if not variants or any(not item.evidence_ids for item in variants):
                    raise ValueError("LLM outreach did not cite current evidence.")
                return OutreachResponse(
                    candidate_id=candidate.id,
                    variants=variants,
                    compliance_note=parsed.compliance_note,
                    model_provider=settings.llm_provider,
                    model_name=settings.llm_model,
                    used_fallback=False,
                )
            except (httpx.HTTPError, ValueError, ValidationError, KeyError, json.JSONDecodeError) as exc:
                self._record_error(exc)
        return self._local_outreach(candidate, evidence_items, latest_score)

    def generate_sourcing_plan(
        self,
        *,
        talent_profile: str,
        target_count: int,
        public_site_scope: str | None,
        connected_sources: list[str],
        company_name: str | None = None,
        max_tasks: int = 6,
    ) -> tuple[list[dict[str, str]], LLMRuntime]:
        if self.configured():
            try:
                payload = self._chat_json(
                    [
                        self._system_prompt(),
                        {
                            "role": "user",
                            "content": self._sourcing_plan_prompt(
                                talent_profile=talent_profile,
                                target_count=target_count,
                                public_site_scope=public_site_scope,
                                connected_sources=connected_sources,
                                company_name=company_name,
                                max_tasks=max_tasks,
                            ),
                        },
                    ]
                )
                parsed = GatewaySourcingPlanPayload.model_validate(payload)
                allowed_targets = {"search_engine", "company_site", "arxiv", "job_site", *connected_sources}
                plan = [
                    {
                        "target_site": item.target_site,
                        "query": item.query,
                        "mode": item.mode,
                        "reason": item.reason,
                    }
                    for item in parsed.query_plan[:max_tasks]
                    if item.target_site in allowed_targets
                ]
                if not plan:
                    raise ValueError("LLM sourcing plan was empty or used unsupported targets.")
                return plan, LLMRuntime(settings.llm_provider, settings.llm_model, False)
            except (httpx.HTTPError, ValueError, ValidationError, KeyError, json.JSONDecodeError) as exc:
                self._record_error(exc)
        return [], LLMRuntime(self.fallback_provider, self.fallback_model, True)

    def extract_candidate_profile(
        self,
        *,
        page_url: str,
        page_title: str,
        page_text: str,
        search_query: str,
    ) -> tuple[dict[str, Any], LLMRuntime]:
        if self.configured():
            try:
                payload = self._chat_json(
                    [
                        self._system_prompt(),
                        {
                            "role": "user",
                            "content": self._candidate_profile_prompt(
                                page_url=page_url,
                                page_title=page_title,
                                page_text=page_text,
                                search_query=search_query,
                            ),
                        },
                    ]
                )
                parsed = GatewayCandidateProfilePayload.model_validate(payload)
                return parsed.model_dump(), LLMRuntime(settings.llm_provider, settings.llm_model, False)
            except (httpx.HTTPError, ValueError, ValidationError, KeyError, json.JSONDecodeError) as exc:
                self._record_error(exc)
        return {
            "is_person_profile": False,
            "name": None,
            "company": None,
            "title": None,
            "department": None,
            "location": None,
            "domain": None,
            "profile_summary": None,
            "confidence": 0.0,
            "rejection_reason": self.last_error or "LLM not configured.",
        }, LLMRuntime(self.fallback_provider, self.fallback_model, True)

    def extract_candidate_leads_from_search_results(
        self,
        *,
        user_intent: str,
        search_results: list[dict[str, str | None]],
        max_candidates: int = 20,
    ) -> tuple[list[dict[str, Any]], LLMRuntime]:
        local_candidates = self._local_candidate_leads(search_results, max_candidates)
        if self._local_leads_are_useful(local_candidates, max_candidates):
            return local_candidates, LLMRuntime(self.fallback_provider, self.fallback_model, True)
        if self.configured() and search_results:
            try:
                payload = self._chat_json(
                    [
                        self._candidate_extraction_system_prompt(),
                        {
                            "role": "user",
                            "content": self._candidate_leads_prompt(
                                user_intent=user_intent,
                                search_results=search_results,
                                max_candidates=max_candidates,
                            ),
                        },
                    ],
                    temperature=0.1,
                    max_tokens=max(settings.llm_max_tokens, 4096),
                )
                parsed = GatewayCandidateLeadPayload.model_validate(payload)
                candidates = [
                    self._clean_candidate_lead(item.model_dump(), search_results)
                    for item in parsed.candidates[:max_candidates]
                ]
                candidates = [item for item in candidates if item["full_name"] or item["profile_links"]]
                candidates = self._merge_local_candidate_leads(
                    candidates,
                    local_candidates,
                    max_candidates,
                )
                return candidates, LLMRuntime(settings.llm_provider, settings.llm_model, False)
            except (httpx.HTTPError, ValueError, ValidationError, KeyError, json.JSONDecodeError) as exc:
                self._record_error(exc)
        return local_candidates, LLMRuntime(
            self.fallback_provider,
            self.fallback_model,
            True,
        )

    def _local_leads_are_useful(self, leads: list[dict[str, Any]], max_candidates: int) -> bool:
        if not leads:
            return False
        required = min(max_candidates, 3)
        if len(leads) < required:
            return False
        complete = 0
        for lead in leads[:required]:
            if lead.get("full_name") and lead.get("profile_links") and (lead.get("current_company") or lead.get("title")):
                complete += 1
        return complete >= required

    def _chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
        body = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or settings.llm_max_tokens,
            "response_format": {"type": "json_object"},
        }
        response: httpx.Response | None = None
        last_error: Exception | None = None
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            for attempt in range(max(settings.llm_retry_count, 0) + 1):
                try:
                    response = client.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {settings.llm_api_key}",
                            "Content-Type": "application/json",
                        },
                        json=body,
                    )
                    response.raise_for_status()
                    break
                except httpx.HTTPError as exc:
                    last_error = exc
                    if attempt >= max(settings.llm_retry_count, 0):
                        raise
                    time.sleep(0.3 * (attempt + 1))
        if response is None:
            raise ValueError(f"LLM request did not return a response: {last_error}")
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type or response.text.lstrip().startswith("data:"):
            content = self._content_from_sse(response.text)
        else:
            payload = response.json()
            content = payload["choices"][0].get("message", {}).get("content")
            if content is None:
                content = payload["choices"][0].get("text", "")
        return self._parse_json_content(content)

    def _chat_json_array(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> list[dict[str, Any]]:
        payload = self._chat_json(
            [
                *messages[:-1],
                {
                    **messages[-1],
                    "content": (
                        messages[-1]["content"]
                        + "\n\nReturn a raw JSON array. Do not wrap it in an object."
                    ),
                },
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if isinstance(payload, list):
            return payload
        if "candidates" in payload and isinstance(payload["candidates"], list):
            return payload["candidates"]
        raise ValueError("LLM response did not contain a JSON array.")

    def _content_from_sse(self, body: str) -> str:
        chunks: list[str] = []
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped.startswith("data:"):
                continue
            data = stripped.removeprefix("data:").strip()
            if not data or data == "[DONE]":
                continue
            payload = json.loads(data)
            choices = payload.get("choices") or []
            if not choices:
                continue
            choice = choices[0]
            delta = choice.get("delta") or {}
            message = choice.get("message") or {}
            content = delta.get("content") or message.get("content")
            if content:
                chunks.append(content)
        content = "".join(chunks).strip()
        if not content:
            raise ValueError("LLM stream did not include content.")
        return content

    def _extract_json_text(self, content: str) -> str:
        stripped = content.strip()
        if (stripped.startswith("{") and stripped.endswith("}")) or (
            stripped.startswith("[") and stripped.endswith("]")
        ):
            return stripped
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
        if fenced:
            return fenced.group(1).strip()
        fenced_array = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", stripped, flags=re.DOTALL)
        if fenced_array:
            return fenced_array.group(1).strip()
        first = stripped.find("{")
        last = stripped.rfind("}")
        if first != -1 and last != -1 and last > first:
            return stripped[first : last + 1]
        first_array = stripped.find("[")
        last_array = stripped.rfind("]")
        if first_array != -1 and last_array != -1 and last_array > first_array:
            return stripped[first_array : last_array + 1]
        raise ValueError("LLM response did not contain a JSON object.")

    def _parse_json_content(self, content: str) -> dict[str, Any] | list[Any]:
        parsed = json.loads(self._extract_json_text(content))
        if isinstance(parsed, (dict, list)):
            return parsed
        raise ValueError("LLM JSON response must be an object or array.")

    def _record_error(self, exc: Exception) -> None:
        message = str(exc)
        self.last_error = f"{exc.__class__.__name__}: {message[:240]}"
        print(f"[TalentNet LLM] {self.last_error}")

    def _system_prompt(self) -> dict[str, str]:
        return {
            "role": "system",
            "content": (
                "You are TalentNet's backend-only recruiting intelligence assistant. "
                "Return strict JSON only. For candidate summaries and outreach, cite evidence IDs from the provided list. "
                "For sourcing plans, transform the user's natural language intent into targeted web-search actions. "
                "For profile extraction, only return a person profile when the page clearly represents one individual. "
                "Do not infer private attributes, do not claim resignation certainty, and do not bypass access controls."
            ),
        }

    def _candidate_extraction_system_prompt(self) -> dict[str, str]:
        return {
            "role": "system",
            "content": (
                "You are an aggressive recruiting intelligence extractor for noisy Google snippets. "
                "Infer company and title from abbreviations, truncated text, Chinese/English mixed descriptions, and role/company order. "
                "For AI sourcing search-result extraction, keep education null unless the source gives a clearly labeled education field. "
                "Use common normalization such as CMU=Carnegie Mellon University, Stanford=Stanford University, 涓婃捣浜ゅぇ=涓婃捣浜ら€氬ぇ瀛? 璋锋瓕=Google, 瀛楄妭=瀛楄妭璺冲姩. "
                "Never copy the person's full_name into current_company, title, or education. "
                "Return strict JSON only with this object shape: "
                "{\"candidates\":[{\"full_name\":string|null,\"current_company\":string|null,"
                "\"title\":string|null,\"education\":string|null,\"profile_links\":[string],\"source_snippet\":string|null,\"evidence\":string|null,"
                "\"confidence\":number}]}. "
                "If a field cannot be inferred even from clues, use null or an empty array. "
                "Prefer concrete person profile URLs such as LinkedIn /in pages, GitHub user pages, "
                "author pages, team/person pages, or personal websites."
            ),
        }

    def _summary_prompt(
        self,
        candidate: Candidate,
        evidence_items: list[Evidence],
        latest_score: CandidateScore | None,
    ) -> str:
        return json.dumps(
            {
                "task": "generate_candidate_summary",
                "schema": {
                    "summary": "string",
                    "risk_explanation": "string",
                    "conflict_notes": ["string"],
                    "cited_evidence_ids": ["evidence_id"],
                    "limitations": ["string"],
                },
                "candidate": self._candidate_payload(candidate),
                "latest_score": self._score_payload(latest_score),
                "evidence": self._evidence_payload(evidence_items),
            },
            ensure_ascii=False,
        )

    def _outreach_prompt(
        self,
        candidate: Candidate,
        evidence_items: list[Evidence],
        latest_score: CandidateScore | None,
    ) -> str:
        return json.dumps(
            {
                "task": "generate_outreach_variants",
                "schema": {
                    "variants": [
                        {"tone": "string", "message": "string", "evidence_ids": ["evidence_id"]}
                    ],
                    "compliance_note": "string",
                },
                "rules": [
                    "Return exactly three editable first-message drafts.",
                    "Messages must be respectful, low-pressure, and not overstate risk.",
                    "Each variant must cite at least one evidence ID.",
                ],
                "candidate": self._candidate_payload(candidate),
                "latest_score": self._score_payload(latest_score),
                "evidence": self._evidence_payload(evidence_items),
            },
            ensure_ascii=False,
        )

    def _sourcing_plan_prompt(
        self,
        *,
        talent_profile: str,
        target_count: int,
        public_site_scope: str | None,
        connected_sources: list[str],
        company_name: str | None,
        max_tasks: int,
    ) -> str:
        allowed_targets = [
            "search_engine",
            "company_site",
            "arxiv",
            "job_site",
            *connected_sources,
        ]
        return json.dumps(
            {
                "task": "generate_talent_sourcing_search_plan",
                "user_intent": talent_profile,
                "schema": {
                    "query_plan": [
                        {
                            "target_site": "one of allowed_targets",
                            "query": "precise web search query, not a copy of user_intent",
                            "mode": "public_web or connected_account",
                            "reason": "why this query helps the recruiting search",
                        }
                    ]
                },
                "rules": [
                    f"Return between 1 and {max_tasks} search items.",
                    "You are an AI web search agent. Understand the user_intent, then create targeted search queries.",
                    "Never copy the whole user prompt as a query.",
                    "Break broad asks into specific searches for people pages, LinkedIn profile pages, team pages, papers, GitHub, patents, talks, and company pages.",
                    "If user asks for Google search, use target_site search_engine and produce Google-style boolean/site queries.",
                    "If user asks for LinkedIn pages and no connected LinkedIn account exists, use search_engine with site:linkedin.com/in queries.",
                    "For candidate LinkedIn queries, include the target company plus at least one role, team, or technical-domain keyword from the user_intent. Never return a query that is only site:linkedin.com/in plus a company name.",
                    "Prefer queries like site:linkedin.com/in Anthropic \"Research Scientist\" \"AI safety\" or site:linkedin.com/in OpenAI \"post-training\" engineer.",
                    "Avoid over-constraining queries with too many quoted phrases. Prefer 2-4 keyword queries that can return many people.",
                    "Each query should be short, precise, and likely to return concrete people/profile pages.",
                    "Use only allowed target_site values.",
                    "For public targets, mode must be public_web.",
                    "For connected private sources, mode must be connected_account.",
                    "Do not invent private credentials or bypass login.",
                    "Queries should find real public profile pages, team pages, papers, jobs, or company people signals.",
                ],
                "allowed_targets": allowed_targets,
                "company_name": company_name,
                "talent_profile": talent_profile,
                "target_count": target_count,
                "public_site_scope": public_site_scope,
                "connected_sources": connected_sources,
            },
            ensure_ascii=False,
        )

    def _candidate_profile_prompt(
        self,
        *,
        page_url: str,
        page_title: str,
        page_text: str,
        search_query: str,
    ) -> str:
        return json.dumps(
            {
                "task": "extract_candidate_profile_from_visible_page",
                "schema": {
                    "is_person_profile": "boolean",
                    "name": "string or null",
                    "company": "string or null",
                    "title": "string or null",
                    "department": "string or null",
                    "location": "string or null",
                    "domain": "string or null",
                    "profile_summary": "string or null",
                    "confidence": "number 0..1",
                    "rejection_reason": "string or null",
                },
                "rules": [
                    "Only use text visible on the page. Do not invent missing fields.",
                    "If the page is a search result, login wall, company page, job page, or generic list page, set is_person_profile=false.",
                    "For LinkedIn, extract the person's display name, current headline/title, current company if visible, location if visible, and concise professional summary.",
                    "If a field is not visible, return null for that field.",
                    "Confidence should be >=0.75 only when name plus at least one of title/company/location is visible.",
                    "Return strict JSON only.",
                ],
                "page": {
                    "url": page_url,
                    "title": page_title,
                    "visible_text": page_text[:6000],
                },
                "search_query": search_query,
            },
            ensure_ascii=False,
        )

    def _candidate_leads_prompt(
        self,
        *,
        user_intent: str,
        search_results: list[dict[str, str | None]],
        max_candidates: int,
    ) -> str:
        return json.dumps(
            {
                "task": "extract_candidate_leads_from_search_results",
                "user_intent": user_intent,
                "schema": {
                    "candidates": [
                        {
                            "full_name": "string or null",
                            "current_company": "string or null",
                            "title": "string or null",
                            "education": "string or null",
                            "profile_links": ["url"],
                            "source_snippet": "string or null",
                            "evidence": "short Chinese explanation of which keywords support the inference",
                            "confidence": "number 0..1",
                        }
                    ]
                },
                "rules": [
                "Use only the provided search_results.",
                "Each candidate must correspond to a real individual, not a company, login page, search page, job page, or generic article.",
                "Extract or reasonably infer full_name, current_company, title, and profile_links from title/snippet/url.",
                    "Set education to null unless the search result has an explicit labeled education field. Do not infer schools from query keywords.",
                "Never put the candidate name into current_company, title, or education.",
                    "Return candidates when at least a real full_name and a direct profile_links URL are supported. Fill missing fields with null.",
                    "profile_links must be direct candidate/person profile URLs from search_results.",
                    "source_snippet should be the shortest snippet that supports the extraction.",
                    "evidence must briefly explain the keyword evidence in Chinese.",
                    f"Return at most {max_candidates} candidates.",
                    "Return strict JSON only.",
                ],
                "search_results": search_results[:80],
            },
            ensure_ascii=False,
        )

    def _clean_candidate_lead(
        self,
        item: dict[str, Any],
        search_results: list[dict[str, str | None]] | None = None,
    ) -> dict[str, Any]:
        links = item.get("profile_links") or []
        if not isinstance(links, list):
            links = [str(links)]
        cleaned_links = [
            link.strip()
            for link in links
            if isinstance(link, str) and link.strip().startswith(("http://", "https://"))
        ][:5]
        full_name = self._clean_person_name(item.get("full_name"), cleaned_links[0] if cleaned_links else "")
        company = self._clean_optional_text(item.get("current_company"), 120)
        title = self._clean_optional_text(item.get("title"), 160)
        education = None
        evidence_text = self._clean_optional_text(item.get("evidence"), 300)
        source_snippet = self._clean_optional_text(item.get("source_snippet"), 500)
        confidence = max(0.0, min(float(item.get("confidence") or 0.0), 1.0))
        query_text = None

        matched_result = self._search_result_for_lead(full_name, cleaned_links, search_results or [])
        if matched_result:
            result_title = matched_result.get("title") or ""
            result_url = matched_result.get("url") or ""
            query_text = self._clean_optional_text(matched_result.get("query"), 240)
            result_snippet = (
                matched_result.get("profile_page_text")
                or matched_result.get("snippet")
                or matched_result.get("text")
                or ""
            )
            context_text = " ".join(
                str(item or "")
                for item in [
                    matched_result.get("user_intent"),
                    matched_result.get("query"),
                    result_title,
                    result_snippet,
                ]
            )
            profile = self._profile_fields_from_result_text(
                matched_result.get("profile_page_title") or result_title,
                result_url,
                result_snippet,
            )
            full_name = profile.get("full_name") or full_name or self._name_from_result_title(result_title, result_url)
            company = (
                company
                or profile.get("current_company")
                or self._company_from_result_text(result_title, result_snippet)
                or self._infer_known_company(context_text)
            )
            title = (
                title
                or profile.get("title")
                or self._title_from_result_text(result_title, result_snippet)
                or self._infer_title_from_text(context_text)
            )
            education = None
            source_snippet = source_snippet or evidence_text or self._clean_optional_text(result_snippet or result_title, 500)
            if not cleaned_links and result_url and self._looks_like_candidate_url(result_url):
                cleaned_links = [result_url]
            if company or title:
                confidence = max(confidence, 0.72)
        company, title, education = self._sanitize_candidate_facts(full_name, company, title, education)
        evidence = evidence_text or self._lead_evidence_text(
            company=company,
            title=title,
            education=education,
            source_snippet=source_snippet,
            query=query_text,
        )
        return {
            "full_name": full_name,
            "current_company": company,
            "title": title,
            "education": education,
            "profile_links": cleaned_links,
            "source_snippet": source_snippet,
            "evidence": evidence,
            "query": query_text,
            "confidence": confidence,
        }

    def _clean_optional_text(self, value: object, max_length: int) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = re.sub(r"\s+", " ", value).strip()
        return cleaned[:max_length] or None

    def _lead_evidence_text(
        self,
        *,
        company: str | None,
        title: str | None,
        education: str | None,
        source_snippet: str | None,
        query: str | None,
    ) -> str | None:
        parts: list[str] = []
        if source_snippet:
            parts.append(f"搜索结果摘要：{source_snippet[:180]}")
        inferred = []
        if company:
            inferred.append(f"公司={company}")
        if title:
            inferred.append(f"职位={title}")
        if education:
            inferred.append(f"院校={education}")
        if inferred:
            parts.append("结构化字段：" + "，".join(inferred))
        if query:
            parts.append(f"检索式：{query[:160]}")
        return "；".join(parts)[:500] or None

    def _sanitize_candidate_facts(
        self,
        full_name: str | None,
        company: str | None,
        title: str | None,
        education: str | None,
    ) -> tuple[str | None, str | None, str | None]:
        return (
            self._clean_company_fact(company, full_name),
            self._clean_title_fact(title, full_name),
            self._clean_education_fact(education, full_name),
        )

    def _clean_company_fact(self, value: str | None, full_name: str | None) -> str | None:
        cleaned = self._clean_optional_text(value, 120)
        if not cleaned or self._same_text(cleaned, full_name) or self._looks_like_person_name(cleaned):
            return None
        if self._looks_like_title_chunk(cleaned) or self._looks_like_school_text(cleaned):
            return None
        return cleaned

    def _clean_title_fact(self, value: str | None, full_name: str | None) -> str | None:
        cleaned = self._clean_optional_text(value, 160)
        if not cleaned or self._same_text(cleaned, full_name) or self._looks_like_school_text(cleaned):
            return None
        return cleaned if self._looks_like_title_chunk(cleaned) else None

    def _clean_education_fact(self, value: str | None, full_name: str | None) -> str | None:
        cleaned = self._clean_optional_text(value, 240)
        if not cleaned or self._same_text(cleaned, full_name):
            return None
        return cleaned if self._looks_like_school_text(cleaned) else None

    def _same_text(self, left: str | None, right: str | None) -> bool:
        if not left or not right:
            return False
        normalize = lambda value: re.sub(r"[^a-z0-9]+", "", value.lower())
        return normalize(left) == normalize(right)

    def _looks_like_person_name(self, value: str) -> bool:
        cleaned = re.sub(r"\s+", " ", value).strip()
        known_companies = {
            "openai",
            "anthropic",
            "google deepmind",
            "deepmind",
            "google",
            "meta",
            "microsoft",
            "apple",
            "nvidia",
            "tesla",
            "xai",
            "mistral ai",
            "cohere",
            "perplexity ai",
            "perplexity",
            "databricks",
            "mosaicml",
            "bytedance",
            "tencent",
            "baidu",
            "meituan",
        }
        if cleaned.lower() in known_companies:
            return False
        words = cleaned.split()
        if not (2 <= len(words) <= 4):
            return False
        if any(self._looks_like_title_chunk(word) or self._looks_like_school_text(word) for word in words):
            return False
        company_terms = {
            "ai",
            "labs",
            "lab",
            "inc",
            "corp",
            "corporation",
            "technologies",
            "technology",
            "systems",
            "research",
            "group",
        }
        if any(word.lower().strip(".,") in company_terms for word in words):
            return False
        return all(re.fullmatch(r"[A-Z][A-Za-z.'-]{1,30}", word) for word in words)

    def _profile_fields_from_result_text(self, title: str, url: str, text: str) -> dict[str, str | None]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        compact = " ".join(lines)
        name = self._name_from_profile_lines(lines) or self._name_from_result_title(title, url)
        headline = ""
        if name:
            for index, line in enumerate(lines[:20]):
                if line.lower() == name.lower() and index + 1 < len(lines):
                    headline = lines[index + 1]
                    break
        if not headline:
            headline = next((line for line in lines[:20] if self._looks_like_title_chunk(line)), "")
        role = self._title_from_result_text(title, headline or compact[:1000])
        company = self._company_from_result_text(title, headline or compact[:1000])
        return {
            "full_name": name,
            "current_company": company,
            "title": role,
            "education": None,
        }

    def _education_from_linkedin_lines(self, lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            if line.strip().lower() == "education":
                window = lines[index + 1 : index + 8]
                for item in window:
                    if self._looks_like_school_text(item):
                        return item[:240]
        for item in lines:
            if self._looks_like_school_text(item):
                return item[:240]
        return None

    def _name_from_profile_lines(self, lines: list[str]) -> str | None:
        blocked = {"experience", "education", "about", "activity", "contact info"}
        for line in lines[:8]:
            cleaned = self._clean_person_name(line)
            if cleaned and cleaned.lower() not in blocked and not self._looks_like_title_chunk(cleaned):
                return cleaned
        return None

    def _looks_like_school_text(self, value: str) -> bool:
        lowered = value.lower()
        school_terms = [
            "university",
            "college",
            "institute",
            "school",
            "phd",
            "ph.d",
            "master",
            "bachelor",
            "mba",
            "大学",
            "学院",
            "交大",
        ]
        blocked_terms = ["company", "followers", "connections", "engineer", "scientist", "manager"]
        return any(term in lowered for term in school_terms) and not any(term in lowered for term in blocked_terms)

    def _clean_person_name(self, value: object, url: str = "") -> str | None:
        cleaned = self._clean_optional_text(value, 120)
        if not cleaned:
            return self._name_from_profile_url(url) if url else None
        cleaned = self._strip_profile_id_suffix_from_name(cleaned, url)
        lowered = cleaned.lower().strip()
        blocked = {"linkedin", "profile", "sign in", "login", "register", "search", "jobs"}
        if lowered in blocked:
            return self._name_from_profile_url(url) if url else None
        if " " not in cleaned and re.fullmatch(r"[A-Za-z]{6,40}", cleaned):
            split_name = self._split_compact_latin_name(cleaned)
            if split_name:
                return split_name
        return self._title_case_name(cleaned)

    def _local_candidate_leads(
        self, search_results: list[dict[str, str | None]], max_candidates: int
    ) -> list[dict[str, Any]]:
        leads: list[dict[str, Any]] = []
        seen: set[tuple[str | None, str | None]] = set()
        for result in search_results:
            title = result.get("title") or ""
            url = result.get("url") or ""
            snippet = result.get("snippet") or result.get("text") or ""
            if not self._looks_like_candidate_url(url):
                continue
            name = self._name_from_result_title(title, url)
            if not name:
                continue
            context_text = " ".join(
                str(item or "")
                for item in [
                    result.get("user_intent"),
                    result.get("query"),
                    title,
                    snippet,
                ]
            )
            company = self._company_from_result_text(title, snippet) or self._infer_known_company(context_text)
            role = self._title_from_result_text(title, snippet) or self._infer_title_from_text(context_text)
            education = None
            company, role, education = self._sanitize_candidate_facts(name, company, role, education)
            source_snippet = snippet[:500] or title[:500]
            evidence = self._lead_evidence_text(
                company=company,
                title=role,
                education=education,
                source_snippet=source_snippet,
                query=self._clean_optional_text(result.get("query"), 240),
            )
            key = (name.lower(), url.lower())
            if key in seen:
                continue
            seen.add(key)
            leads.append(
                {
                    "full_name": name,
                    "current_company": company,
                    "title": role,
                    "education": education,
                    "profile_links": [url],
                    "source_snippet": source_snippet,
                    "evidence": evidence,
                    "query": self._clean_optional_text(result.get("query"), 240),
                    "confidence": 0.62 if role or company or education else 0.48,
                }
            )
            if len(leads) >= max_candidates:
                break
        return leads

    def _merge_local_candidate_leads(
        self,
        model_leads: list[dict[str, Any]],
        local_leads: list[dict[str, Any]],
        max_candidates: int,
    ) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        by_key: dict[tuple[str, str], dict[str, Any]] = {}
        for lead in [*model_leads, *local_leads]:
            name = (lead.get("full_name") or "").strip().lower()
            link = ((lead.get("profile_links") or [""])[0] or "").strip().lower()
            if not name and not link:
                continue
            key = (name, self._normalize_url_for_match(link))
            existing = by_key.get(key)
            if existing:
                if not existing.get("current_company") and lead.get("current_company"):
                    existing["current_company"] = lead["current_company"]
                if not existing.get("title") and lead.get("title"):
                    existing["title"] = lead["title"]
                if not existing.get("education") and lead.get("education"):
                    existing["education"] = lead["education"]
                if not existing.get("source_snippet") and lead.get("source_snippet"):
                    existing["source_snippet"] = lead["source_snippet"]
                if not existing.get("evidence") and lead.get("evidence"):
                    existing["evidence"] = lead["evidence"]
                if not existing.get("query") and lead.get("query"):
                    existing["query"] = lead["query"]
                existing["confidence"] = max(existing.get("confidence") or 0, lead.get("confidence") or 0)
                continue
            by_key[key] = lead
            merged.append(lead)
            if len(merged) >= max_candidates:
                break
        return merged

    def _search_result_for_lead(
        self,
        full_name: str | None,
        links: list[str],
        search_results: list[dict[str, str | None]],
    ) -> dict[str, str | None] | None:
        normalized_links = {self._normalize_url_for_match(link) for link in links if link}
        normalized_name = re.sub(r"\s+", " ", full_name or "").strip().lower()
        for result in search_results:
            url = result.get("url") or ""
            if url and self._normalize_url_for_match(url) in normalized_links:
                return result
        if normalized_name:
            for result in search_results:
                haystack = re.sub(
                    r"\s+",
                    " ",
                    f"{result.get('title') or ''} {result.get('snippet') or ''}".lower(),
                )
                if normalized_name in haystack:
                    return result
        return None

    def _normalize_url_for_match(self, url: str) -> str:
        if not url:
            return ""
        try:
            parsed = httpx.URL(url)
        except httpx.InvalidURL:
            return url.strip().rstrip("/").lower()
        host = (parsed.host or "").lower().removeprefix("www.")
        path = parsed.path.rstrip("/").lower()
        return f"{host}{path}"

    def _looks_like_candidate_url(self, url: str) -> bool:
        parsed = httpx.URL(url) if url else None
        if parsed is None:
            return False
        host = parsed.host or ""
        path = parsed.path.lower().strip("/")
        if "linkedin.com" in host:
            return path.startswith("in/")
        if "github.com" in host:
            return bool(path) and "/" not in path and path not in {"orgs", "topics"}
        return any(part in path for part in ["people/", "team/", "profile/", "author/"])

    def _name_from_result_title(self, title: str, url: str) -> str | None:
        cleaned = re.sub(r"\s+", " ", title.replace("| LinkedIn", "").replace(" - LinkedIn", "")).strip()
        head = re.split(r"\s[-|鈥撯€擼\s", cleaned, maxsplit=1)[0].strip()
        blocked = {"linkedin", "sign in", "login", "register", "search", "jobs"}
        if 2 <= len(head) <= 100 and head.lower() not in blocked:
            return head
        path = httpx.URL(url).path.strip("/")
        slug = path.split("/")[-1] if path else ""
        slug = re.sub(r"[-_]+", " ", re.sub(r"\d+", "", slug)).strip()
        return " ".join(word.capitalize() for word in slug.split())[:100] or None

    def _company_from_result_text(self, title: str, snippet: str) -> str | None:
        inferred_company = self._infer_known_company(f"{title} {snippet}")
        if inferred_company:
            return inferred_company
        linkedin_parts = self._linkedin_google_snippet_parts(snippet)
        if linkedin_parts.get("company"):
            return linkedin_parts["company"]
        combined = self._normalize_result_text(f"{title} {snippet}")
        patterns = [
            r"\bat\s+([A-Z][A-Za-z0-9&.,' +\-]{1,60})(?=\s*(?:\||-|,|$))",
            r"\b@\s*([A-Z][A-Za-z0-9&.,' +\-]{1,60})(?=\s*(?:\||-|,|$))",
            r"\bCompany[:：]\s*([A-Z][A-Za-z0-9&.,' +\-]{1,60})(?=\s*(?:\||-|,|$))",
            r"\bCurrent(?:ly)?[:：]\s*([A-Z][A-Za-z0-9&.,' +\-]{1,60})(?=\s*(?:\||-|,|$))",
        ]
        for pattern in patterns:
            match = re.search(pattern, combined, flags=re.I)
            if match:
                company = self._clean_extracted_company(match.group(1))
                if company and self._looks_like_company_name(company):
                    return company
        return None

    def _title_from_result_text(self, title: str, snippet: str) -> str | None:
        inferred_title = self._infer_title_from_text(f"{title} {snippet}")
        if inferred_title:
            return inferred_title
        linkedin_parts = self._linkedin_google_snippet_parts(snippet)
        if linkedin_parts.get("title"):
            return linkedin_parts["title"]
        combined = self._normalize_result_text(f"{title} {snippet}")
        title_without_brand = re.sub(r"\s*\|\s*LinkedIn.*$", "", self._normalize_result_text(title), flags=re.I)
        patterns = [
            (r"^[^-|]+\s+(?:-|\|)\s+(.{2,120}?)\s+at\s+[A-Z][A-Za-z0-9&.,' +\-]{1,60}(?=\s*(?:\||-|,|$))", title_without_brand),
            (r"\bTitle[:：]\s*(.{2,120}?)(?=\s*(?:\||-|,|$))", combined),
            (r"\b(?:is|as)\s+(?:a|an)\s+(.{2,100}?)\s+at\s+[A-Z][A-Za-z0-9&.,' +\-]{1,60}", combined),
        ]
        for pattern, target in patterns:
            match = re.search(pattern, target, flags=re.I)
            if match:
                role = self._clean_extracted_title(match.group(1))
                if role:
                    return role
        roles = [
            "Principal Research Scientist",
            "Senior Research Scientist",
            "Research Scientist",
            "Senior Research Engineer",
            "Research Engineer",
            "Machine Learning Engineer",
            "Software Engineer",
            "AI Engineer",
            "Infrastructure Engineer",
            "Product Manager",
            "Data Scientist",
            "Engineering Manager",
            "Member of Technical Staff",
            "Staff Engineer",
        ]
        combined_lower = combined.lower()
        for role in roles:
            if role.lower() in combined_lower:
                return role
        return None

    def _normalize_result_text(self, value: str) -> str:
        normalized = value
        for separator in ["·", "•", "路", "锝?", "鈥?", "璺?", "閿?", "閳?", "бд"]:
            normalized = normalized.replace(separator, " | ")
        return re.sub(r"\s+", " ", normalized).strip()

    def _linkedin_google_snippet_parts(self, snippet: str) -> dict[str, str | None]:
        text = snippet
        separators = ["·", "•", "路", "鈥?", "璺?", "閿?", "閳?", "бд"]
        for separator in separators:
            text = text.replace(separator, " | ")
        text = re.sub(r"\s+", " ", text).strip()
        if "|" not in text:
            return {"title": None, "company": None}
        first_line = re.split(
            r"\b(?:AI executive|Executive|Engineer|Researcher|Scientist|Experienced|Building|Works on)\b",
            text,
            maxsplit=1,
            flags=re.I,
        )[0]
        chunks = [
            (self._clean_optional_text(chunk, 160) or "").strip(" .,-|")
            for chunk in re.split(r"\s*\|\s*", first_line)
        ]
        chunks = [chunk for chunk in chunks if chunk]
        if len(chunks) < 2:
            return {"title": None, "company": None}
        company = None
        role = None
        for chunk in reversed(chunks):
            cleaned = self._clean_extracted_company(chunk)
            if cleaned and self._looks_like_company_name(cleaned):
                company = cleaned
                break
        for chunk in chunks:
            cleaned = self._clean_extracted_title(chunk)
            if cleaned and self._looks_like_title_chunk(cleaned):
                role = cleaned
                break
        return {"title": role, "company": company}

    def _education_from_result_text(self, title: str, snippet: str) -> str | None:
        inferred_school = self._infer_school_from_text(f"{title} {snippet}")
        if inferred_school:
            return inferred_school
        combined = self._normalize_result_text(f"{title} {snippet}")
        patterns = [
            r"\b(?:Education|Alumni|Alumna|Alumnus)[:：]\s*([^|,。;；]{2,120})",
            r"\b(?:University|College|Institute|School) of [A-Z][A-Za-z&.'\- ]{2,80}",
            r"\b[A-Z][A-Za-z&.'\- ]{2,80} (?:University|College|Institute|School)\b",
            r"\b(?:PhD|Ph\.D\.|MS|M\.S\.|MSc|BSc|BS|BA|MBA)\s+(?:at|from|in)?\s*([A-Z][A-Za-z&.'\- ]{2,80})",
            r"(?:就读于|毕业于|读博|毕业)\s*([^|,。;；]{2,80})",
        ]
        for pattern in patterns:
            match = re.search(pattern, combined)
            if match:
                value = match.group(1) if match.lastindex else match.group(0)
                value = re.split(r"[.;。；|]", value, maxsplit=1)[0]
                education = self._clean_optional_text(value, 240)
                if education and not self._looks_like_title_chunk(education):
                    return education.strip(" .,-|")
        return None

    def _result_chunks(self, title: str, snippet: str) -> list[str]:
        text = self._normalize_result_text(f"{title} 路 {snippet}")
        text = re.sub(r"\s*\|\s*LinkedIn.*$", "", text, flags=re.I)
        chunks = [
            self._clean_optional_text(chunk, 120) or ""
            for chunk in re.split(r"\s*(?:\||-|鈥搢鈥攟路|,)\s*", text)
        ]
        return [chunk for chunk in chunks if chunk]

    def _looks_like_company_chunk(self, chunk: str) -> bool:
        lowered = chunk.lower()
        blocked = {
            "linkedin",
            "profile",
            "people",
            "jobs",
            "followers",
            "connections",
            "san francisco",
            "london",
            "new york",
            "seattle",
            "beijing",
            "shanghai",
        }
        if lowered in blocked or self._looks_like_title_chunk(chunk):
            return False
        known = {
            "openai",
            "anthropic",
            "google deepmind",
            "deepmind",
            "google",
            "meta",
            "microsoft",
            "apple",
            "nvidia",
            "tesla",
            "xai",
            "mistral ai",
            "cohere",
            "perplexity",
            "databricks",
        }
        return lowered in known or bool(re.fullmatch(r"[A-Z][A-Za-z0-9&.,' +\-]{2,60}", chunk))

    def _looks_like_company_name(self, value: str) -> bool:
        cleaned = value.strip(" .,-|")
        if not cleaned or self._looks_like_person_name(cleaned) or self._looks_like_title_chunk(cleaned):
            return False
        known = {
            "openai",
            "anthropic",
            "google deepmind",
            "deepmind",
            "google",
            "meta",
            "microsoft",
            "apple",
            "nvidia",
            "tesla",
            "xai",
            "mistral ai",
            "cohere",
            "perplexity",
            "databricks",
        }
        lowered = cleaned.lower()
        descriptive_terms = ["safety", "inference", "infrastructure", "platform", "systems", "distributed", "machine learning"]
        if any(term in lowered for term in descriptive_terms):
            return False
        company_terms = ["labs", "lab", "inc", "corp", "corporation", "technologies"]
        return lowered in known or any(term in lowered.split() for term in company_terms)

    def _infer_known_company(self, text: str) -> str | None:
        lowered = text.lower()
        aliases = [
            ("微软亚洲研究院", "微软亚洲研究院"),
            ("msra", "微软亚洲研究院"),
            ("字节跳动", "字节跳动"),
            ("bytedance", "ByteDance"),
            ("腾讯", "Tencent"),
            ("tencent", "Tencent"),
            ("google deepmind", "Google DeepMind"),
            ("deepmind", "Google DeepMind"),
            ("谷歌", "Google"),
            ("google", "Google"),
            ("百度", "百度"),
            ("baidu", "Baidu"),
            ("美团", "美团"),
            ("meituan", "Meituan"),
            ("openai", "OpenAI"),
            ("anthropic", "Anthropic"),
            ("perplexity ai", "Perplexity AI"),
            ("perplexity", "Perplexity AI"),
            ("mistral ai", "Mistral AI"),
            ("mistral", "Mistral AI"),
            ("cohere", "Cohere"),
            ("mosaicml", "Databricks MosaicML"),
            ("databricks", "Databricks"),
            ("xai", "xAI"),
            ("meta", "Meta"),
            ("nvidia", "NVIDIA"),
            ("apple", "Apple"),
            ("microsoft", "Microsoft"),
        ]
        for alias, company in aliases:
            if alias.lower() in lowered:
                return company
        return None

    def _infer_school_from_text(self, text: str) -> str | None:
        lowered = text.lower()
        aliases = [
            ("清华", "Tsinghua University"),
            ("tsinghua", "Tsinghua University"),
            ("上海交大", "上海交通大学"),
            ("sjtu", "上海交通大学"),
            ("stanford", "Stanford University"),
            ("cmu", "卡耐基梅隆大学 (CMU)"),
            ("carnegie mellon", "卡耐基梅隆大学 (CMU)"),
            ("mit", "MIT"),
            ("berkeley", "UC Berkeley"),
            ("北大", "北京大学"),
            ("北京大学", "北京大学"),
            ("pku", "北京大学"),
        ]
        education_markers = [
            "graduated",
            "alumni",
            "studied",
            "education",
            "就读",
            "毕业",
            "读博",
            "phd",
            "master",
        ]
        for alias, school in aliases:
            if alias.lower() in lowered and (
                any(marker in lowered for marker in education_markers) or alias.lower() in {"cmu", "stanford", "mit", "tsinghua", "sjtu", "pku"}
            ):
                return school
        return None

    def _infer_title_from_text(self, text: str) -> str | None:
        lowered = text.lower()
        chinese_patterns = [
            (r"(前沿技术负责人)", "前沿技术负责人"),
            (r"(资深架构师)", "资深架构师"),
            (r"(高级算法专家)", "高级算法专家"),
            (r"(软件工程师|软工)", "软件工程师"),
            (r"(研究员)", "研究员"),
        ]
        for pattern, title in chinese_patterns:
            if re.search(pattern, text):
                return title
        english_titles = [
            "Vice President, AI Infrastructure",
            "Senior Software Engineer",
            "Staff Software Engineer",
            "Senior Research Engineer",
            "Research Scientist",
            "Research Engineer",
            "Machine Learning Engineer",
            "ML Engineer",
            "LLM Engineer",
            "Inference Engineer",
            "Software Engineer",
            "AI Researcher",
            "AI Engineer",
            "Infrastructure Engineer",
            "Member of Technical Staff",
        ]
        for title in english_titles:
            if title.lower() in lowered:
                if title == "ML Engineer":
                    return "Machine Learning Engineer"
                return title
        if re.search(r"\bllm\s+engineer\b", lowered):
            return "LLM Engineer"
        if re.search(r"\bml\s+engineer\b", lowered):
            return "Machine Learning Engineer"
        if re.search(r"\binference\s+engineer\b", lowered):
            return "Inference Engineer"
        return None

    def _looks_like_title_chunk(self, chunk: str) -> bool:
        lowered = chunk.lower()
        return any(
            word in lowered
            for word in [
                "engineer",
                "scientist",
                "researcher",
                "manager",
                "director",
                "president",
                "executive",
                "head",
                "vp",
                "vice president",
                "lead",
                "staff",
                "principal",
                "founder",
                "architect",
                "developer",
                "product",
                "recruiter",
                "负责人",
                "架构师",
                "工程师",
                "研究员",
                "专家",
            ]
        )

    def _clean_extracted_company(self, value: str) -> str | None:
        cleaned = self._clean_optional_text(value, 120)
        if not cleaned:
            return None
        cleaned = re.sub(r"\b(?:working|focused|specializing|based)\b.*$", "", cleaned, flags=re.I)
        cleaned = cleaned.strip(" .,-|路")
        return cleaned or None

    def _clean_extracted_title(self, value: str) -> str | None:
        cleaned = self._clean_optional_text(value, 160)
        if not cleaned:
            return None
        cleaned = re.sub(r"\s+at\s+[A-Z][A-Za-z0-9&.,' +\-]{1,60}.*$", "", cleaned, flags=re.I)
        cleaned = cleaned.strip(" .,-|路")
        blocked = {"linkedin", "profile", "people", "jobs"}
        return None if cleaned.lower() in blocked else cleaned

    def _name_from_result_title(self, title: str, url: str) -> str | None:
        cleaned = re.sub(r"\s+", " ", title.replace("| LinkedIn", "").replace(" - LinkedIn", "")).strip()
        head = re.split(r"\s+(?:-|鈥搢鈥攟\||路)\s+", cleaned, maxsplit=1)[0].strip()
        blocked = {"linkedin", "sign in", "login", "register", "search", "jobs", "profile"}
        if 2 <= len(head) <= 100 and head.lower() not in blocked and not head.lower().startswith("https://"):
            return self._title_case_name(self._strip_profile_id_suffix_from_name(head, url))
        return self._name_from_profile_url(url)

    def _name_from_profile_url(self, url: str) -> str | None:
        if not url:
            return None
        try:
            path = httpx.URL(url).path.strip("/")
        except httpx.InvalidURL:
            return None
        parts = [part for part in path.split("/") if part]
        slug = ""
        if len(parts) >= 2 and parts[0].lower() == "in":
            slug = parts[1]
        elif parts:
            slug = parts[-1]
        slug = re.sub(r"\?.*$", "", slug)
        slug = self._strip_profile_slug_id(slug)
        slug = slug.strip("-_ .")
        if not slug:
            return None
        if re.search(r"[-_ .]", slug):
            cleaned = re.sub(r"[-_ .]+", " ", slug).strip()
            return self._title_case_name(cleaned) or None
        return self._split_compact_latin_name(slug) or self._title_case_name(slug)

    def _strip_profile_slug_id(self, slug: str) -> str:
        pieces = [piece for piece in re.split(r"[-_ .]+", slug) if piece]
        while pieces:
            tail = pieces[-1]
            if re.search(r"\d", tail) or re.fullmatch(r"[a-fA-F]{2,12}", tail):
                pieces.pop()
                continue
            break
        return " ".join(pieces) if pieces else re.sub(r"\d+$", "", slug)

    def _strip_profile_id_suffix_from_name(self, name: str, url: str) -> str:
        cleaned = re.sub(r"\s+", " ", name).strip()
        if not url or "linkedin.com" not in url.lower():
            return cleaned
        try:
            path = httpx.URL(url).path.strip("/")
            slug = path.split("/")[-1] if path else ""
        except httpx.InvalidURL:
            slug = ""
        words = cleaned.split()
        while len(words) > 1:
            tail = words[-1].strip(".,")
            slug_tail_matches = bool(slug and re.search(rf"(?:-|_){re.escape(tail)}[a-z0-9]*$", slug, flags=re.I))
            linkedin_id_fragment = bool(slug and re.search(r"\d", slug) and re.fullmatch(r"[A-Fa-f]{1,4}", tail))
            if re.search(r"\d", tail) or linkedin_id_fragment or (slug_tail_matches and re.fullmatch(r"[A-Fa-f]{1,8}", tail)):
                words.pop()
                continue
            break
        return " ".join(words)

    def _split_compact_latin_name(self, value: str) -> str | None:
        cleaned = re.sub(r"[^A-Za-z]", "", value).strip()
        if not cleaned or len(cleaned) < 6:
            return None
        camel = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", cleaned)
        if " " in camel:
            return self._title_case_name(camel)
        lower = cleaned.lower()
        known_surnames = [
            "lacroix",
            "goodfriend",
            "citro",
            "lofgren",
            "shama",
            "zhang",
            "chen",
            "singh",
            "patel",
            "kim",
            "wang",
            "liu",
            "li",
            "lee",
            "lin",
            "xu",
            "zhou",
            "yang",
            "huang",
            "zhao",
            "kumar",
            "nguyen",
            "garcia",
            "smith",
            "johnson",
            "brown",
            "miller",
            "wilson",
            "anderson",
            "thomas",
            "moore",
            "martin",
            "white",
            "clark",
            "lewis",
            "walker",
            "hall",
            "allen",
            "young",
        ]
        for surname in sorted(known_surnames, key=len, reverse=True):
            if lower.endswith(surname) and len(lower) > len(surname) + 1:
                given = lower[: -len(surname)]
                if 2 <= len(given) <= 20:
                    return self._title_case_name(f"{given} {surname}")
        return None

    def _title_case_name(self, value: str) -> str | None:
        cleaned = re.sub(r"\s+", " ", value).strip(" .,-_|/")
        if not cleaned:
            return None
        particles = {"de", "del", "da", "di", "du", "van", "von", "la", "le", "al"}
        words = []
        for word in cleaned.split():
            if not word:
                continue
            lower = word.lower()
            if lower in particles:
                words.append(lower)
            elif re.fullmatch(r"[A-Z]{2,}", word):
                words.append(word)
            else:
                words.append("-".join(part[:1].upper() + part[1:].lower() for part in word.split("-") if part))
        return " ".join(words)[:120] or None

    def _local_summary(
        self,
        candidate: Candidate,
        evidence_items: list[Evidence],
        latest_score: CandidateScore | None,
    ) -> AISummaryResponse:
        selected = evidence_items[:3]
        evidence_ids = [item.id for item in selected]
        evidence_text = "；".join(item.summary for item in selected)
        conflict_notes: list[str] = []
        if latest_score and latest_score.risk_level == "needs_review":
            conflict_notes.append("当前评分置信度不足，需要人工核实后再作为触达依据。")
        if any(item.source == "company_site" for item in evidence_items) and latest_score and latest_score.risk_score >= 70:
            conflict_notes.append("存在公司官网或公开项目页证据，需要确认候选人是否仍在核心项目中。")

        return AISummaryResponse(
            candidate_id=candidate.id,
            summary=(
                f"{candidate.name} 当前任职于 {candidate.current_company.name}，"
                f"方向为 {candidate.domain or candidate.title}。近期信号包括：{evidence_text}"
            ),
            risk_explanation=(
                latest_score.explanation
                if latest_score and latest_score.explanation
                else "当前尚未生成风险评分，建议先刷新评分后再判断触达优先级。"
            ),
            conflict_notes=conflict_notes,
            cited_evidence_ids=evidence_ids,
            limitations=[
                "本输出由后端 LLM Gateway 生成，仅引用系统已保存证据。",
                "不得将该判断作为确定离职结论或自动外发内容。",
            ],
            model_provider=self.fallback_provider,
            model_name=self.fallback_model,
            used_fallback=True,
        )

    def _local_outreach(
        self,
        candidate: Candidate,
        evidence_items: list[Evidence],
        latest_score: CandidateScore | None,
    ) -> OutreachResponse:
        cited = [item.id for item in evidence_items[:2]]
        topic = candidate.domain or candidate.title
        company = candidate.current_company.name
        variants = [
            OutreachVariant(
                tone="专业直接",
                message=(
                    f"你好 {candidate.name}，最近关注到你在 {topic} 方向的公开经历。"
                    "我们正在看一个和大规模 AI 系统落地相关的机会，想请教你是否愿意做一次低压力交流。"
                ),
                evidence_ids=cited,
            ),
            OutreachVariant(
                tone="研究交流",
                message=(
                    f"你好 {candidate.name}，看到你在 {company} 的公开经历和近期相关信号，"
                    f"我对你在 {topic} 方向的判断很感兴趣。如果方便，想约 20 分钟交流行业和技术趋势。"
                ),
                evidence_ids=cited,
            ),
            OutreachVariant(
                tone="机会探索",
                message=(
                    f"你好 {candidate.name}，我们在搭建一个需要 {topic} 经验的核心团队。"
                    "不确定你近期是否开放了解外部机会，如果时机合适，我可以先发一份简短背景给你。"
                ),
                evidence_ids=cited,
            ),
        ]
        return OutreachResponse(
            candidate_id=candidate.id,
            variants=variants,
            compliance_note="开场白仅供用户编辑参考，系统不会自动发送给候选人。",
            model_provider=self.fallback_provider,
            model_name=self.fallback_model,
            used_fallback=True,
        )

    def _candidate_payload(self, candidate: Candidate) -> dict[str, Any]:
        return {
            "id": candidate.id,
            "name": candidate.name,
            "company": candidate.current_company.name,
            "title": candidate.title,
            "department": candidate.department,
            "domain": candidate.domain,
            "location": candidate.location,
        }

    def _score_payload(self, score: CandidateScore | None) -> dict[str, Any] | None:
        if score is None:
            return None
        return {
            "risk_score": score.risk_score,
            "confidence_score": score.confidence_score,
            "risk_level": score.risk_level,
            "reason_codes": score.reason_codes,
            "explanation": score.explanation,
            "limitations": score.limitations,
        }

    def _evidence_payload(self, evidence_items: list[Evidence]) -> list[dict[str, Any]]:
        return [
            {
                "id": item.id,
                "source": item.source,
                "title": item.title,
                "url": item.url,
                "summary": item.summary,
                "confidence": item.confidence,
                "confirmed_by_user": item.confirmed_by_user,
                "observed_at": item.observed_at.isoformat(),
            }
            for item in evidence_items[:8]
        ]

    def _valid_ids(self, ids: list[str], allowed_ids: set[str]) -> list[str]:
        result: list[str] = []
        for item in ids:
            if item in allowed_ids and item not in result:
                result.append(item)
        return result

    def _redact_base_url(self, value: str) -> str | None:
        if not value:
            return None
        return value.rstrip("/")






