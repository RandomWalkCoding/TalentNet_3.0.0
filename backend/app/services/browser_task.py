from datetime import datetime, timezone
from pathlib import Path
import os
import re
from urllib.parse import parse_qs, unquote, urlparse
from urllib.parse import urlencode
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.models import BrowserTask, Candidate, Company, Evidence
from app.repositories.evidence import EvidenceRepository
from app.repositories.talent_pool import add_candidate_to_pool
from app.schemas.browser_task import BrowserTaskCreate, BrowserTaskRead, EvidenceDraftUpdate
from app.schemas.evidence import EvidenceCreate
from app.services.llm_gateway import LLMGateway
from app.services.risk_scoring import RiskScoringService

TARGET_SITE_TO_SOURCE = {
    "linkedin": "linkedin_visible",
    "maimai": "maimai_visible",
    "search_engine": "manual",
    "arxiv": "arxiv",
    "company_site": "company_site",
    "job_site": "job_site",
    "patent": "patent",
}


class NoConcreteResultError(Exception):
    pass


class BrowserTaskService:
    def __init__(self) -> None:
        self.evidence_repository = EvidenceRepository()
        self.llm = LLMGateway()

    def create_task(self, db: Session, payload: BrowserTaskCreate) -> BrowserTaskRead:
        task = BrowserTask(
            id=f"task_{uuid4().hex}",
            task_type=payload.task_type,
            query=payload.query,
            target_site=payload.target_site,
            status="pending",
            execution_log=[],
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        self.run_task(db, task.id, payload)
        return self.get_task(db, task.id)

    def create_pending_search_task(self, db: Session, payload: BrowserTaskCreate) -> BrowserTaskRead:
        page_url = payload.query if payload.query.startswith(("http://", "https://")) else None
        task = BrowserTask(
            id=f"task_{uuid4().hex}",
            task_type=payload.task_type,
            query=payload.query,
            target_site=payload.target_site,
            status="waiting_user",
            result_summary="已生成待判断线索。浏览器读取可稍后重试，当前搜索不会因网页自动化失败而中断。",
            execution_log=[
                {
                    "message": "Created from AI sourcing quick path without blocking on browser automation.",
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            ],
            page_title=f"候选线索：{payload.query}",
            page_url=page_url,
            evidence_draft={
                "candidate_id": payload.candidate_id,
                "company_id": payload.company_id,
                "source": TARGET_SITE_TO_SOURCE.get(payload.target_site, "manual"),
                "title": f"候选线索：{payload.query}",
                "url": page_url,
                "screenshot_path": None,
                "summary": f"AI 搜索任务已创建：{payload.query}",
                "raw_text": payload.query,
                "confidence": 0.55,
            },
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return BrowserTaskRead.model_validate(task)

    def discover_candidate_pages(self, query: str, target_site: str = "search_engine", limit: int = 8) -> list[str]:
        target_url = self._target_url(target_site, query)
        return self._discover_candidate_urls(target_url, limit=limit)

    def collect_search_results(
        self, query: str, target_site: str = "search_engine", limit: int = 10
    ) -> list[dict[str, str | None]]:
        target_url = self._target_url(target_site, query)
        return self._collect_search_results(target_url, limit=limit)

    def retry_task(self, db: Session, task_id: str) -> BrowserTaskRead:
        task = self._get_task_model(db, task_id)
        payload = BrowserTaskCreate(
            task_type=task.task_type,
            query=task.query,
            target_site=task.target_site,
            candidate_id=(task.evidence_draft or {}).get("candidate_id"),
            company_id=(task.evidence_draft or {}).get("company_id"),
        )
        task.status = "pending"
        task.error_message = None
        task.execution_log = []
        task.evidence_draft = None
        task.result_summary = None
        db.commit()
        self.run_task(db, task.id, payload)
        return self.get_task(db, task.id)

    def get_task(self, db: Session, task_id: str) -> BrowserTaskRead:
        return BrowserTaskRead.model_validate(self._get_task_model(db, task_id))

    def list_tasks(self, db: Session) -> list[BrowserTaskRead]:
        tasks = db.scalars(select(BrowserTask).order_by(BrowserTask.created_at.desc())).all()
        return [BrowserTaskRead.model_validate(task) for task in tasks]

    def list_pending_tasks(self, db: Session) -> list[BrowserTaskRead]:
        tasks = db.scalars(
            select(BrowserTask)
            .where(BrowserTask.status.in_(["pending", "running", "waiting_user"]))
            .order_by(BrowserTask.created_at.desc())
        ).all()
        return [BrowserTaskRead.model_validate(task) for task in tasks]

    def cancel_task(self, db: Session, task_id: str) -> BrowserTaskRead:
        task = self._get_task_model(db, task_id)
        if task.status in {"completed", "failed", "cancelled"}:
            return BrowserTaskRead.model_validate(task)
        task.status = "cancelled"
        self._log(task, "cancelled", "用户取消任务")
        db.commit()
        db.refresh(task)
        return BrowserTaskRead.model_validate(task)

    def update_evidence_draft(
        self, db: Session, task_id: str, payload: EvidenceDraftUpdate
    ) -> BrowserTaskRead:
        task = self._get_task_model(db, task_id)
        if task.status != "waiting_user" or not task.evidence_draft:
            raise AppError(
                code="EVIDENCE_DRAFT_NOT_EDITABLE",
                message="Evidence draft can only be edited before confirmation.",
                status_code=400,
            )
        task.evidence_draft = {
            **task.evidence_draft,
            **payload.model_dump(exclude_unset=True),
        }
        self._log(task, "draft_updated", "用户编辑了证据草稿")
        db.commit()
        db.refresh(task)
        return BrowserTaskRead.model_validate(task)

    def confirm_evidence(self, db: Session, task_id: str) -> Evidence:
        task = self._get_task_model(db, task_id)
        if task.status != "waiting_user":
            raise AppError("BROWSER_TASK_NOT_CONFIRMABLE", "Only a pending review can be confirmed.", 409)
        if not task.evidence_draft:
            raise AppError(
                code="EVIDENCE_DRAFT_NOT_READY",
                message="Browser task has no evidence draft to confirm.",
                status_code=400,
            )
        draft = task.evidence_draft
        candidate_id = draft.get("candidate_id")
        if not candidate_id:
            raise AppError(
                code="CANDIDATE_REQUIRED",
                message="Evidence draft requires a candidate before confirmation.",
                status_code=400,
            )

        evidence = self.evidence_repository.create(
            db,
            EvidenceCreate(
                candidate_id=candidate_id,
                company_id=draft.get("company_id"),
                source=draft["source"],
                title=draft["title"],
                url=draft.get("url"),
                screenshot_path=draft.get("screenshot_path"),
                observed_at=datetime.now(timezone.utc),
                event_time=datetime.now(timezone.utc),
                summary=draft["summary"],
                raw_text=draft.get("raw_text"),
                confidence=float(draft.get("confidence", 0.65)),
                confirmed_by_user=True,
            ),
        )
        task.status = "completed"
        task.result_summary = f"已确认并保存证据：{evidence.title}"
        self._log(task, "confirmed", f"证据入库：{evidence.id}")
        db.commit()
        db.refresh(evidence)
        return evidence

    def add_result_to_pool(self, db: Session, task_id: str) -> dict:
        task = self._get_task_model(db, task_id)
        if not task.evidence_draft:
            raise AppError(
                code="EVIDENCE_DRAFT_NOT_READY",
                message="Search result has no draft to add.",
                status_code=400,
        )
        draft = task.evidence_draft
        candidate_id = draft.get("candidate_id")
        if not candidate_id:
            raise AppError(
                code="CANDIDATE_REQUIRED_FOR_POOL",
                message=(
                    "Search clues must be assigned to a real candidate before they can be "
                    "saved or added to the talent pool."
                ),
                status_code=400,
            )
        evidence = self.confirm_evidence(db, task_id)
        pool_item = add_candidate_to_pool(db, candidate_id)
        return {
            "candidate_id": candidate_id,
            "evidence_id": evidence.id,
            "pool_item_id": pool_item.id,
        }

    def run_task(self, db: Session, task_id: str, payload: BrowserTaskCreate) -> None:
        task = self._get_task_model(db, task_id)
        task.status = "running"
        self._log(task, "started", "开始执行网页任务")
        db.commit()

        target_url = self._target_url(payload.target_site, payload.query)
        try:
            page_data = self._run_playwright(task.id, target_url)
            task.page_title = page_data["title"]
            task.page_url = page_data["url"]
            task.screenshot_path = page_data["screenshot_path"]
            self._log(task, "page_loaded", f"读取页面：{task.page_title or task.page_url}")
            draft = self._draft_from_page(payload, task, page_data["text"])
            if not draft.get("candidate_id"):
                draft = self._attach_candidate_from_profile(db, task, draft, page_data["text"], payload.query)
            task.evidence_draft = draft
            task.result_summary = "已读取公开网页并生成待确认的证据草稿。"
            task.status = "waiting_user"
            self._log(task, "draft_ready", "证据草稿已生成，等待人工确认")
        except NoConcreteResultError as exc:
            task.error_message = str(exc)
            self._log(task, "failed", str(exc))
            task.page_url = target_url
            task.result_summary = "未找到可读取的具体候选人相关页面。"
            task.status = "failed"
        except Exception as exc:
            task.error_message = str(exc)
            self._log(task, "fallback", f"真实浏览器执行失败，使用可运行降级草稿：{exc}")
            task.page_url = target_url
            task.screenshot_path = None
            task.evidence_draft = self._fallback_draft(payload, task, target_url, str(exc))
            task.result_summary = "真实浏览器执行失败，已生成降级草稿供人工编辑确认。"
            task.status = "waiting_user"
        db.commit()

    def _run_playwright(self, task_id: str, target_url: str) -> dict[str, str]:
        from playwright.sync_api import sync_playwright

        screenshot_path = Path("artifacts") / "browser-tasks" / f"{task_id}.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        user_data_dir = Path(settings.browser_user_data_dir)
        user_data_dir.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            launch_options = {
                "headless": settings.browser_headless,
                "args": ["--disable-blink-features=AutomationControlled"],
            }
            executable_path = self._local_browser_executable()
            if executable_path:
                launch_options["executable_path"] = executable_path
            browser, should_close, is_connected_browser = self._open_browser(playwright, launch_options, user_data_dir)
            try:
                page = browser.pages[0] if browser.pages else browser.new_page()
                page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(1000)
                if self._is_search_result_page(page.url):
                    result_url = self._first_concrete_result_url(page)
                    if not result_url:
                        raise NoConcreteResultError("AI 检索没有找到可读取的具体候选人相关页面，请换一个更明确的检索指令。")
                    self._log_search_handoff(task_id, target_url, result_url)
                    page.goto(result_url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(1000)
                title = page.title()
                text = self._page_visible_text(page)[:6000]
                if not text.strip():
                    raise NoConcreteResultError("已打开具体页面，但页面可见文本为空，无法形成可靠候选线索。")
                if self._is_blocked_or_auth_page(page.url, title, text):
                    raise NoConcreteResultError("页面是登录、注册或访问拦截页，没有可入库的候选人资料。")
                page.screenshot(path=str(screenshot_path), full_page=True)
                final_url = page.url
            finally:
                if should_close:
                    browser.close()
        return {
            "title": title,
            "url": final_url,
            "text": text,
            "screenshot_path": str(screenshot_path).replace("\\", "/"),
        }

    def _discover_candidate_urls(self, target_url: str, limit: int = 8) -> list[str]:
        from playwright.sync_api import sync_playwright

        user_data_dir = Path(settings.browser_user_data_dir)
        user_data_dir.mkdir(parents=True, exist_ok=True)
        try:
            with sync_playwright() as playwright:
                launch_options = {
                    "headless": settings.browser_headless,
                    "args": ["--disable-blink-features=AutomationControlled"],
                }
                executable_path = self._local_browser_executable()
                if executable_path:
                    launch_options["executable_path"] = executable_path
                browser, should_close, _is_connected_browser = self._open_browser(playwright, launch_options, user_data_dir)
                try:
                    page = browser.pages[0] if browser.pages else browser.new_page()
                    page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(1200)
                    if not self._is_search_result_page(page.url):
                        return [page.url] if self._is_concrete_result_url(page.url) else []
                    urls = self._concrete_result_urls(page, limit=limit)
                    if not urls and "google.com" in urlparse(target_url).netloc.lower():
                        bing_url = self._bing_url_from_google_url(target_url)
                        if bing_url:
                            page.goto(bing_url, wait_until="domcontentloaded", timeout=15000)
                            page.wait_for_timeout(1200)
                            urls = self._concrete_result_urls(page, limit=limit)
                    return urls
                finally:
                    if should_close:
                        browser.close()
        except Exception as exc:
            print(f"[TalentNet Browser] URL discovery failed: {exc.__class__.__name__}: {str(exc)[:240]}")
            return []

    def _collect_search_results(self, target_url: str, limit: int = 10) -> list[dict[str, str | None]]:
        from playwright.sync_api import sync_playwright

        user_data_dir = Path(settings.browser_user_data_dir)
        user_data_dir.mkdir(parents=True, exist_ok=True)
        try:
            with sync_playwright() as playwright:
                launch_options = {
                    "headless": settings.browser_headless,
                    "args": ["--disable-blink-features=AutomationControlled"],
                }
                executable_path = self._local_browser_executable()
                if executable_path:
                    launch_options["executable_path"] = executable_path
                browser, should_close, is_connected_browser = self._open_browser(playwright, launch_options, user_data_dir)
                try:
                    page = browser.pages[0] if browser.pages else browser.new_page()
                    page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(1200)
                    results = self._search_result_cards(page, limit=limit)
                    if not results and "google.com" in urlparse(target_url).netloc.lower():
                        bing_url = self._bing_url_from_google_url(target_url)
                        if bing_url:
                            page.goto(bing_url, wait_until="domcontentloaded", timeout=15000)
                            page.wait_for_timeout(1200)
                            results = self._search_result_cards(page, limit=limit)
                    return self._enrich_result_cards_from_profiles(
                        browser,
                        results,
                        limit=limit,
                        allow_private_profile_open=is_connected_browser,
                    )
                finally:
                    if should_close:
                        browser.close()
        except Exception as exc:
            print(f"[TalentNet Browser] search result collection failed: {exc.__class__.__name__}: {str(exc)[:240]}")
            return []

    def _search_result_cards(self, page, limit: int = 10) -> list[dict[str, str | None]]:
        cards: list[dict[str, str | None]] = []
        seen: set[str] = set()
        selectors = [
            "div.g",
            "li.b_algo",
            "article",
            "[data-testid='result']",
        ]
        for selector in selectors:
            nodes = page.locator(selector)
            count = min(nodes.count(), 40)
            for index in range(count):
                node = nodes.nth(index)
                try:
                    link = node.locator("a[href]").first
                    href = self._normalize_result_url(link.get_attribute("href"))
                    if not href or not self._is_concrete_result_url(href):
                        continue
                    normalized = href.rstrip("/")
                    if normalized in seen:
                        continue
                    seen.add(normalized)
                    title = ""
                    for title_selector in ["h3", "h2", "a"]:
                        try:
                            title = node.locator(title_selector).first.inner_text(timeout=600).strip()
                            if title:
                                break
                        except Exception:
                            continue
                    text = node.inner_text(timeout=1000).strip()
                    snippet = self._snippet_from_result_text(text, title)
                    if not title:
                        title = self._title_from_url(href) or href
                    cards.append(
                        {
                            "title": title or href,
                            "url": href,
                            "snippet": snippet,
                            "source": "search_result",
                        }
                    )
                    if len(cards) >= limit:
                        return cards
                except Exception:
                    continue
        if not cards:
            cards = self._search_result_cards_from_links(page, limit=limit)
        return cards

    def _search_result_cards_from_links(self, page, limit: int = 10) -> list[dict[str, str | None]]:
        cards: list[dict[str, str | None]] = []
        seen: set[str] = set()
        links = page.locator("a[href]")
        count = min(links.count(), 120)
        for index in range(count):
            try:
                link = links.nth(index)
                href = self._normalize_result_url(link.get_attribute("href"))
                if not href or not self._is_concrete_result_url(href):
                    continue
                normalized = href.rstrip("/")
                if normalized in seen:
                    continue
                seen.add(normalized)
                title = ""
                try:
                    title = link.inner_text(timeout=500).strip()
                except Exception:
                    title = ""
                context = self._nearby_text(link, title)
                cards.append(
                    {
                        "title": title or self._title_from_url(href) or href,
                        "url": href,
                        "snippet": self._snippet_from_result_text(context, title) or context or self._title_from_url(href),
                        "source": "search_result",
                    }
                )
                if len(cards) >= limit:
                    return cards
            except Exception:
                continue
        return cards

    def _nearby_text(self, link, title: str) -> str:
        handles = [
            "xpath=ancestor::div[1]",
            "xpath=ancestor::div[2]",
            "xpath=ancestor::li[1]",
            "xpath=ancestor::article[1]",
        ]
        for selector in handles:
            try:
                text = link.locator(selector).first.inner_text(timeout=700).strip()
                if text and len(text) > len(title or ""):
                    return text[:1200]
            except Exception:
                continue
        return title

    def _enrich_result_cards_from_profiles(
        self,
        browser,
        results: list[dict[str, str | None]],
        limit: int = 10,
        allow_private_profile_open: bool = False,
    ) -> list[dict[str, str | None]]:
        enriched: list[dict[str, str | None]] = []
        for result in results[:limit]:
            url = result.get("url") or ""
            if self._should_open_profile_for_enrichment(url):
                if not allow_private_profile_open:
                    result = {
                        **result,
                        "profile_enrichment_status": "needs_connected_chrome",
                    }
                    enriched.append(result)
                    continue
                detail = self._read_profile_result(browser, url)
                if detail:
                    result = {
                        **result,
                        "title": detail.get("title") or result.get("title"),
                        "snippet": self._merge_snippets(result.get("snippet"), detail.get("text")),
                        "profile_page_title": detail.get("title"),
                        "profile_page_text": detail.get("text"),
                    }
            enriched.append(result)
        return enriched

    def _should_open_profile_for_enrichment(self, url: str) -> bool:
        if not url:
            return False
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path.strip("/").lower()
        return "linkedin.com" in host and path.startswith("in/")

    def _read_profile_result(self, browser, url: str) -> dict[str, str] | None:
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=18000)
            page.wait_for_timeout(1800)
            title = page.title()
            text = self._page_visible_text(page)[:8000]
            if not text.strip() or self._is_blocked_or_auth_page(page.url, title, text):
                return None
            return {"title": title, "text": text}
        except Exception:
            return None
        finally:
            try:
                page.close()
            except Exception:
                pass

    def _merge_snippets(self, search_snippet: str | None, profile_text: str | None) -> str | None:
        pieces = [item.strip() for item in [search_snippet, profile_text] if item and item.strip()]
        if not pieces:
            return None
        return "\n\n".join(pieces)[:5000]

    def _snippet_from_result_text(self, text: str, title: str) -> str | None:
        cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        if title:
            cleaned = cleaned.replace(title, "", 1).strip()
        return cleaned[:700] or None

    def _title_from_url(self, url: str) -> str | None:
        parsed = urlparse(url)
        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if "linkedin.com" in parsed.netloc.lower() and len(parts) >= 2 and parts[0].lower() == "in":
            slug = parts[1]
        elif parts:
            slug = parts[-1]
        else:
            return None
        slug = re.sub(r"[-_]+", " ", slug)
        slug = re.sub(r"\d+", "", slug).strip()
        title = " ".join(word.capitalize() for word in slug.split())
        return title[:120] or None

    def _open_browser(self, playwright, launch_options: dict, user_data_dir: Path):
        if settings.browser_cdp_url:
            try:
                browser = playwright.chromium.connect_over_cdp(settings.browser_cdp_url, timeout=2500)
                if browser.contexts:
                    return browser.contexts[0], False, True
                return browser.new_context(viewport={"width": 1365, "height": 900}), True, True
            except Exception:
                pass
        return playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            viewport={"width": 1365, "height": 900},
            **launch_options,
        ), True, False

    def _page_visible_text(self, page) -> str:
        if "linkedin.com" in urlparse(page.url).netloc.lower():
            linkedin_text = self._linkedin_profile_text(page)
            if linkedin_text.strip():
                return linkedin_text
        return page.locator("body").inner_text(timeout=5000)

    def _linkedin_profile_text(self, page) -> str:
        parts: list[str] = []
        selectors = [
            "main h1",
            "main .text-body-medium",
            "main .pv-text-details__left-panel",
            "main .pv-top-card--list-bullet",
            "section:has(#about)",
            "section:has(#experience)",
            "section:has(#education)",
            "section:has(#skills)",
            "main",
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count():
                    value = locator.inner_text(timeout=1500).strip()
                    if value and value not in parts:
                        parts.append(value)
            except Exception:
                continue
        return "\n\n".join(parts)

    def _local_browser_executable(self) -> str | None:
        configured = settings.browser_executable or os.getenv("TALENTNET_BROWSER_EXECUTABLE")
        candidates = [
            configured,
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate
        return None

    def _is_search_result_page(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return any(item in host for item in ["bing.com", "google.com", "duckduckgo.com"])

    def _first_concrete_result_url(self, page) -> str | None:
        urls = self._concrete_result_urls(page, limit=1)
        return urls[0] if urls else None

    def _concrete_result_urls(self, page, limit: int = 8) -> list[str]:
        selectors = [
            "a:has(h3)",
            "li.b_algo h2 a",
            "article h2 a",
            "a[data-testid='result-title-a']",
            "a[href]",
        ]
        result: list[str] = []
        seen: set[str] = set()
        for selector in selectors:
            links = page.locator(selector)
            count = min(links.count(), 80)
            for index in range(count):
                href = links.nth(index).get_attribute("href")
                candidate = self._normalize_result_url(href)
                if candidate and self._is_concrete_result_url(candidate):
                    normalized = candidate.rstrip("/")
                    if normalized not in seen:
                        seen.add(normalized)
                        result.append(candidate)
                    if len(result) >= limit:
                        return result
        return result

    def _normalize_result_url(self, href: str | None) -> str | None:
        if not href:
            return None
        if href.startswith("/"):
            return None
        parsed = urlparse(href)
        if parsed.netloc.endswith("bing.com") and parsed.path.startswith("/ck/a"):
            query = parse_qs(parsed.query)
            encoded = (query.get("u") or [""])[0]
            if encoded.startswith("a1"):
                encoded = encoded[2:]
            if encoded:
                try:
                    import base64

                    padding = "=" * (-len(encoded) % 4)
                    return base64.urlsafe_b64decode(encoded + padding).decode("utf-8", errors="ignore")
                except Exception:
                    return unquote(encoded)
        return href

    def _bing_url_from_google_url(self, url: str) -> str | None:
        parsed = urlparse(url)
        query = parse_qs(parsed.query).get("q", [""])[0]
        if not query:
            return None
        return "https://www.bing.com/search?" + urlencode({"q": query})

    def _is_concrete_result_url(self, url: str) -> bool:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if parsed.scheme not in {"http", "https"}:
            return False
        blocked_hosts = ["bing.com", "google.com", "microsoft.com", "msn.com", "duckduckgo.com"]
        if any(host == item or host.endswith(f".{item}") for item in blocked_hosts):
            return False
        blocked_path_bits = [
            "login",
            "signin",
            "signup",
            "authwall",
            "checkpoint",
            "uas/login",
            "sorry",
            "captcha",
            "policies",
            "preferences",
        ]
        if any(bit in parsed.path.lower() for bit in blocked_path_bits):
            return False
        return self._looks_like_person_homepage(url)

    def _is_blocked_or_auth_page(self, url: str, title: str, text: str) -> bool:
        parsed = urlparse(url)
        lowered_url = url.lower()
        lowered_title = title.lower()
        compact_text = " ".join(text.split())
        lowered_text = compact_text.lower()
        auth_markers = [
            "sign in",
            "sign up",
            "join linkedin",
            "login",
            "log in",
            "authwall",
            "checkpoint",
            "captcha",
            "注册",
            "登录",
            "加入 linkedin",
            "加入领英",
        ]
        if any(marker in lowered_url for marker in ["login", "signin", "signup", "authwall", "checkpoint"]):
            return True
        if any(marker in lowered_title for marker in auth_markers):
            return True
        if any(marker in lowered_text[:1200] for marker in auth_markers):
            person_markers = [
                "experience",
                "education",
                "about",
                "activity",
                "followers",
                "connections",
                "工作经历",
                "教育经历",
                "动态",
                "简介",
            ]
            if not any(marker in lowered_text for marker in person_markers):
                return True
        if (
            "linkedin.com" in parsed.netloc.lower()
            and any(marker in lowered_text[:1200] for marker in auth_markers)
            and not self._linkedin_text_looks_like_profile(compact_text)
        ):
            return True
        return False

    def _linkedin_text_looks_like_profile(self, text: str) -> bool:
        lowered = text.lower()
        if len(text.strip()) < 80:
            return False
        blocked_names = {"注册", "登录", "sign in", "join linkedin", "linkedin"}
        first_line = next((line.strip().lower() for line in text.splitlines() if line.strip()), "")
        if first_line in blocked_names:
            return False
        profile_markers = [
            "experience",
            "education",
            "about",
            "activity",
            "followers",
            "connections",
            "工作经历",
            "教育经历",
            "动态",
            "简介",
        ]
        role_markers = [
            "engineer",
            "scientist",
            "research",
            "manager",
            "founder",
            "director",
            "product",
            "工程师",
            "研究",
            "经理",
            "负责人",
        ]
        return any(marker in lowered for marker in profile_markers) and any(
            marker in lowered for marker in role_markers
        )

    def _looks_like_person_homepage(self, url: str) -> bool:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path.strip("/").lower()
        if "linkedin.com" in host:
            return path.startswith("in/")
        if "github.com" in host:
            return bool(path) and "/" not in path and path not in {"orgs", "topics", "features", "marketplace"}
        if "scholar.google" in host:
            return "user=" in parsed.query
        if "semanticsscholar.org" in host:
            return path.startswith("author/")
        if "twitter.com" in host or "x.com" in host:
            return bool(path) and "/" not in path
        return any(bit in path for bit in ["/people/", "/team/", "/profile/", "/author/"])

    def _log_search_handoff(self, task_id: str, search_url: str, result_url: str) -> None:
        # Hook for tests/debugging without persisting another task log entry from inside Playwright.
        _ = (task_id, search_url, result_url)

    def _draft_from_page(
        self, payload: BrowserTaskCreate, task: BrowserTask, raw_text: str
    ) -> dict:
        source = TARGET_SITE_TO_SOURCE.get(payload.target_site, "manual")
        summary = self._summarize_text(raw_text, payload)
        return {
            "candidate_id": payload.candidate_id,
            "company_id": payload.company_id,
            "source": source,
            "title": task.page_title or f"网页任务：{payload.query}",
            "url": task.page_url,
            "screenshot_path": task.screenshot_path,
            "summary": summary,
            "raw_text": raw_text[:3000],
            "confidence": 0.72 if raw_text else 0.55,
        }

    def _attach_candidate_from_profile(
        self, db: Session, task: BrowserTask, draft: dict, raw_text: str, search_query: str = ""
    ) -> dict:
        profile = self._extract_profile(task.page_url or "", task.page_title or "", raw_text, search_query)
        if not profile["name"] or not self._is_valid_candidate_profile(profile, task.page_url or "", task.page_title or "", raw_text):
            raise NoConcreteResultError("已找到具体页面，但无法自动识别候选人姓名，因此不会生成条目。")
        company = self._find_or_create_company(db, profile["company"] or draft.get("company_id") or "AI 检索待归类")
        candidate = self._find_or_create_candidate(db, profile, company, draft)
        return {
            **draft,
            "candidate_id": candidate.id,
            "company_id": company.id,
            "title": f"{profile['name']} - {profile['title'] or candidate.title}",
            "summary": (
                f"已自动识别候选人：{profile['name']}；"
                f"当前/相关公司：{company.name}；"
                f"岗位/方向：{candidate.title}。来源页面：{task.page_url}。"
            ),
            "confidence": max(float(draft.get("confidence", 0.7)), 0.78),
        }

    def _extract_profile(self, url: str, title: str, raw_text: str, search_query: str = "") -> dict[str, str | None]:
        llm_profile, runtime = self.llm.extract_candidate_profile(
            page_url=url,
            page_title=title,
            page_text=raw_text,
            search_query=search_query,
        )
        if (
            not runtime.used_fallback
            and llm_profile.get("is_person_profile")
            and llm_profile.get("name")
            and float(llm_profile.get("confidence") or 0) >= 0.68
        ):
            return {
                "name": self._clean_profile_field(llm_profile.get("name"), 120),
                "company": self._clean_profile_field(llm_profile.get("company"), 120),
                "title": self._clean_profile_field(llm_profile.get("title"), 160),
                "department": self._clean_profile_field(llm_profile.get("department"), 160),
                "location": self._clean_profile_field(llm_profile.get("location"), 120),
                "domain": self._clean_profile_field(llm_profile.get("domain"), 120),
                "profile_summary": self._clean_profile_field(llm_profile.get("profile_summary"), 1200),
            }

        text = " ".join(raw_text.split())
        title_clean = self._clean_title(title)
        name = self._name_from_title(title_clean) or self._name_from_url(url)
        company = self._company_from_text(title_clean, text)
        role = self._role_from_text(title_clean, text)
        domain = self._domain_from_text(f"{title_clean} {text}")
        return {
            "name": name,
            "company": company,
            "title": role,
            "department": self._department_from_text(text),
            "location": self._location_from_text(text),
            "domain": domain,
            "profile_summary": text[:1000] if text else title_clean,
        }

    def _clean_profile_field(self, value: object, max_length: int) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = re.sub(r"\s+", " ", value).strip(" \t\r\n-|")
        return cleaned[:max_length] or None

    def _is_valid_candidate_profile(
        self, profile: dict[str, str | None], url: str, title: str, raw_text: str
    ) -> bool:
        name = (profile.get("name") or "").strip().lower()
        invalid_names = {
            "注册",
            "登录",
            "登入",
            "sign in",
            "sign up",
            "join linkedin",
            "linkedin",
            "authwall",
        }
        if not name or name in invalid_names:
            return False
        if any(token in name for token in ["注册", "登录", "sign in", "join linkedin"]):
            return False
        if not (profile.get("title") or profile.get("company") or profile.get("location")):
            return False
        return not self._is_blocked_or_auth_page(url, title, raw_text)

    def _clean_title(self, title: str) -> str:
        return re.sub(r"\s+", " ", title.replace("| LinkedIn", "").replace(" - LinkedIn", "")).strip()

    def _name_from_title(self, title: str) -> str | None:
        head = re.split(r"\s[-|–]\s", title, maxsplit=1)[0].strip()
        head = re.sub(r"\s+\|\s+.*$", "", head).strip()
        blocked = ["search", "google", "bing", "注册", "登录", "sign in", "sign up", "join linkedin"]
        if 2 <= len(head) <= 80 and not any(word.lower() in head.lower() for word in blocked):
            return head
        return None

    def _name_from_url(self, url: str) -> str | None:
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if "linkedin.com" in parsed.netloc.lower() and len(parts) >= 2 and parts[0].lower() == "in":
            slug = parts[1]
        elif parts:
            slug = parts[-1]
        else:
            return None
        slug = re.sub(r"[-_]+", " ", slug)
        slug = re.sub(r"\d+", "", slug).strip()
        return " ".join(word.capitalize() for word in slug.split())[:80] or None

    def _company_from_text(self, title: str, text: str) -> str | None:
        patterns = [
            r" at ([A-Z][A-Za-z0-9&.\- ]{2,60})",
            r"@([A-Z][A-Za-z0-9&.\- ]{2,60})",
            r"Current:?\s*([A-Z][A-Za-z0-9&.\- ]{2,60})",
            r"Company:?\s*([A-Z][A-Za-z0-9&.\- ]{2,60})",
        ]
        combined = f"{title} {text[:1200]}"
        for pattern in patterns:
            match = re.search(pattern, combined)
            if match:
                return match.group(1).strip(" .,-|")[:120]
        for known in ["Anthropic", "OpenAI", "Google DeepMind", "DeepMind", "Meta", "Microsoft", "NVIDIA", "Apple"]:
            if known.lower() in combined.lower():
                return known
        return None

    def _role_from_text(self, title: str, text: str) -> str | None:
        combined = f"{title} {text[:1200]}"
        roles = [
            "Research Scientist",
            "Research Engineer",
            "Machine Learning Engineer",
            "Software Engineer",
            "AI Engineer",
            "Infrastructure Engineer",
            "Engineer",
            "Scientist",
        ]
        for role in roles:
            if role.lower() in combined.lower():
                return role
        title_parts = re.split(r"\s[-|–]\s", title)
        if len(title_parts) > 1:
            return title_parts[1].strip()[:160]
        return "Technical Talent"

    def _department_from_text(self, text: str) -> str | None:
        lowered = text.lower()
        departments = [
            ("Research", ["research", "scientist", "paper"]),
            ("Engineering", ["engineer", "software", "infrastructure"]),
            ("Product", ["product manager", "product"]),
            ("Data", ["data scientist", "analytics", "data"]),
        ]
        for label, keywords in departments:
            if any(keyword in lowered for keyword in keywords):
                return label
        return None

    def _location_from_text(self, text: str) -> str | None:
        patterns = [
            r"\b(San Francisco Bay Area|San Francisco|New York|Seattle|London|Beijing|Shanghai|Shenzhen|Singapore)\b",
            r"\b([A-Z][A-Za-z .-]+,\s*(?:California|CA|New York|NY|Washington|WA|United Kingdom|China))\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)[:120]
        return None

    def _domain_from_text(self, text: str) -> str | None:
        lowered = text.lower()
        domains = [
            ("LLM / AI Infrastructure", ["llm", "inference", "ai infra", "infrastructure"]),
            ("Research", ["research", "scientist", "paper"]),
            ("Machine Learning", ["machine learning", "ml engineer"]),
            ("GPU / Systems", ["gpu", "cuda", "kernel", "systems"]),
        ]
        for label, keywords in domains:
            if any(keyword in lowered for keyword in keywords):
                return label
        return None

    def _find_or_create_company(self, db: Session, name_or_id: str) -> Company:
        existing = db.get(Company, name_or_id)
        if existing:
            return existing
        normalized = name_or_id.strip().lower()
        for company in db.scalars(select(Company)).all():
            if company.name.strip().lower() == normalized:
                return company
        company = Company(
            id=f"company_{uuid4().hex}",
            name=name_or_id.strip()[:120] or "AI 检索待归类",
            industry="AI / Technology",
            website=None,
            monitor_status="active",
        )
        db.add(company)
        db.commit()
        db.refresh(company)
        return company

    def _find_or_create_candidate(self, db: Session, profile: dict[str, str | None], company: Company, draft: dict) -> Candidate:
        name = profile["name"] or "Unknown Candidate"
        normalized = name.strip().lower()
        for candidate in db.scalars(select(Candidate).where(Candidate.current_company_id == company.id)).all():
            if candidate.name.strip().lower() == normalized:
                return candidate
        candidate = Candidate(
            id=f"cand_{uuid4().hex}",
            name=name[:120],
            current_company_id=company.id,
            title=(profile["title"] or "Technical Talent")[:160],
            department=profile.get("department"),
            location=profile.get("location"),
            domain=profile["domain"],
            profile_summary=profile["profile_summary"],
            source_type="ai_search",
            follow_status="new",
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        RiskScoringService().refresh_candidate_score(db, candidate.id)
        return candidate

    def _fallback_draft(
        self, payload: BrowserTaskCreate, task: BrowserTask, target_url: str, error: str
    ) -> dict:
        source = TARGET_SITE_TO_SOURCE.get(payload.target_site, "manual")
        return {
            "candidate_id": payload.candidate_id,
            "company_id": payload.company_id,
            "source": source,
            "title": f"候选线索：{payload.query[:96]}",
            "url": target_url,
            "screenshot_path": task.screenshot_path,
            "summary": (
                f"未能完整读取页面。搜索意图：{payload.query[:180]}。"
                "请打开来源确认姓名、公司、岗位和匹配信号后，再归属到具体候选人。"
            ),
            "raw_text": f"browser_error={error}; target_url={target_url}",
            "confidence": 0.45,
        }

    def _summarize_text(self, raw_text: str, payload: BrowserTaskCreate) -> str:
        cleaned = " ".join(raw_text.split())
        if not cleaned:
            return f"页面可见文本为空。搜索意图：{payload.query[:180]}。需要人工补充候选人、公司和岗位信息。"
        snippets = self._best_snippets(cleaned, payload.query)
        source_hint = {
            "linkedin": "公开履历页可能包含岗位、公司、经历或活跃信号",
            "maimai": "职场社区页可能包含职业状态、公司和岗位信号",
            "company_site": "公司页面可能确认组织、团队或项目背景",
            "job_site": "招聘页面可能反映团队扩张或岗位需求",
            "arxiv": "论文页面可能确认研究方向和技术影响力",
            "patent": "专利页面可能确认技术领域和发明人信息",
        }.get(payload.target_site, "公开网页可能包含候选人匹配信号")
        return (
            f"{source_hint}。核心线索：{' / '.join(snippets)}。"
            "请核实是否对应真实候选人，再决定是否归属到人才库中的人。"
        )

    def _best_snippets(self, cleaned: str, query: str) -> list[str]:
        words = [word.lower() for word in query.replace('"', " ").split() if len(word) >= 3]
        sentences = [
            item.strip(" -|")
            for item in cleaned.replace("。", ".").replace("；", ".").split(".")
            if len(item.strip()) >= 18
        ]
        scored: list[tuple[int, str]] = []
        for sentence in sentences[:80]:
            lowered = sentence.lower()
            score = sum(1 for word in words if word in lowered)
            score += sum(1 for word in ["engineer", "research", "ai", "llm", "team", "profile", "linkedin"] if word in lowered)
            if score:
                scored.append((score, sentence[:140]))
        selected = [item for _, item in sorted(scored, key=lambda pair: pair[0], reverse=True)[:2]]
        if selected:
            return selected
        return [cleaned[:160]]

    def _target_url(self, target_site: str, query: str) -> str:
        stripped = query.strip()
        if stripped.startswith("http://") or stripped.startswith("https://"):
            return stripped
        if target_site == "linkedin":
            return "https://www.linkedin.com/search/results/all/?" + urlencode(
                {"keywords": stripped}
            )
        if target_site == "maimai":
            return "https://maimai.cn/search?" + urlencode({"query": stripped})
        if target_site == "arxiv":
            return "https://arxiv.org/search/?" + urlencode(
                {"query": stripped, "searchtype": "all"}
            )
        if target_site == "company_site":
            return "https://www.google.com/search?" + urlencode(
                {"q": f"site:company {stripped}"}
            )
        if target_site == "job_site":
            return "https://www.google.com/search?" + urlencode(
                {"q": f"job posting hiring team {stripped}"}
            )
        if target_site == "patent":
            return "https://patents.google.com/?" + urlencode({"q": stripped})
        return "https://www.google.com/search?" + urlencode({"q": stripped})

    def _get_task_model(self, db: Session, task_id: str) -> BrowserTask:
        task = db.get(BrowserTask, task_id)
        if task is None:
            raise AppError(
                code="BROWSER_TASK_NOT_FOUND",
                message="Browser task does not exist.",
                status_code=404,
            )
        return task

    def _log(self, task: BrowserTask, event: str, message: str) -> None:
        current = list(task.execution_log or [])
        current.append(
            {
                "event": event,
                "message": message,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
        task.execution_log = current
