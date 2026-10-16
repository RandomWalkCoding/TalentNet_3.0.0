from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_stage5_create_and_list_browser_task() -> None:
    reset_db()
    with TestClient(app) as client:
        created = client.post(
            "/api/browser-tasks",
            json={
                "task_type": "verify_profile",
                "query": "林晨 OpenAI post-training",
                "target_site": "linkedin",
                "candidate_id": "cand_lin_chen",
                "company_id": "company_openai",
            },
        )
        listed = client.get("/api/browser-tasks?show_history=true")
        default_listed = client.get("/api/browser-tasks")

    assert created.status_code == 200
    payload = created.json()
    assert payload["status"] == "waiting_user"
    assert payload["evidence_draft"]["source"] == "linkedin_visible"
    assert payload["execution_log"]
    assert default_listed.status_code == 200
    assert default_listed.json() == []
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == payload["id"]


def test_stage5_confirm_evidence_refreshes_score() -> None:
    reset_db()
    with TestClient(app) as client:
        created = client.post(
            "/api/browser-tasks",
            json={
                "task_type": "verify_profile",
                "query": "周宇 ByteDance AI Infra",
                "target_site": "maimai",
                "candidate_id": "cand_zhou_yu",
                "company_id": "company_bytedance",
            },
        ).json()
        confirmed = client.post(f"/api/browser-tasks/{created['id']}/confirm-evidence")
        evidence = client.get("/api/evidence?candidate_id=cand_zhou_yu")
        score = client.get("/api/candidates/cand_zhou_yu/score")

    assert confirmed.status_code == 200
    assert confirmed.json()["source"] == "maimai_visible"
    assert len(evidence.json()) >= 2
    assert score.json()["model_version"] == "rules-v2"


def test_stage5_edit_evidence_draft_before_confirming() -> None:
    reset_db()
    with TestClient(app) as client:
        created = client.post(
            "/api/browser-tasks",
            json={
                "task_type": "verify_profile",
                "query": "Maya Singh agent systems",
                "target_site": "company_site",
                "candidate_id": "cand_maya_singh",
                "company_id": "company_deepmind",
            },
        ).json()
        edited = client.patch(
            f"/api/browser-tasks/{created['id']}/evidence-draft",
            json={
                "title": "Edited public page signal",
                "summary": "User reviewed the draft and corrected the public page evidence.",
                "confidence": 0.91,
            },
        )
        confirmed = client.post(f"/api/browser-tasks/{created['id']}/confirm-evidence")

    assert edited.status_code == 200
    assert edited.json()["evidence_draft"]["title"] == "Edited public page signal"
    assert confirmed.status_code == 200
    assert confirmed.json()["title"] == "Edited public page signal"
    assert confirmed.json()["confidence"] == 0.91


def test_stage5_cancel_browser_task() -> None:
    reset_db()
    with TestClient(app) as client:
        created = client.post(
            "/api/browser-tasks",
            json={
                "task_type": "search_candidate",
                "query": "Agent research scientist",
                "target_site": "search_engine",
            },
        ).json()
        cancelled = client.post(f"/api/browser-tasks/{created['id']}/cancel")

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_stage5_unassigned_search_clue_cannot_create_candidate_or_pool_item() -> None:
    reset_db()
    with TestClient(app) as client:
        before = client.get("/api/candidates").json()
        created = client.post(
            "/api/browser-tasks",
            json={
                "task_type": "search_candidate",
                "query": "Agent research scientist",
                "target_site": "search_engine",
            },
        ).json()
        added = client.post(f"/api/browser-tasks/{created['id']}/add-to-pool")
        after = client.get("/api/candidates").json()

    assert added.status_code == 400
    assert added.json()["error"]["code"] == "CANDIDATE_REQUIRED_FOR_POOL"
    assert len(after) == len(before)


def test_stage5_real_browser_success_generates_page_metadata(monkeypatch) -> None:
    from app.services.browser_task import BrowserTaskService

    reset_db()

    def fake_run_playwright(self, task_id, target_url):
        return {
            "title": "Example Talent Page",
            "url": target_url,
            "text": "Visible candidate profile text with team and research signals.",
            "screenshot_path": f"artifacts/browser-tasks/{task_id}.png",
        }

    monkeypatch.setattr(BrowserTaskService, "_run_playwright", fake_run_playwright)

    with TestClient(app) as client:
        created = client.post(
            "/api/browser-tasks",
            json={
                "task_type": "verify_profile",
                "query": "https://example.com/profile",
                "target_site": "search_engine",
                "candidate_id": "cand_lin_chen",
                "company_id": "company_openai",
            },
        )

    assert created.status_code == 200
    payload = created.json()
    assert payload["status"] == "waiting_user"
    assert payload["page_title"] == "Example Talent Page"
    assert payload["screenshot_path"].endswith(".png")
    assert payload["evidence_draft"]["raw_text"].startswith("Visible candidate")
    assert any(item["event"] == "draft_ready" for item in payload["execution_log"])


def test_stage5_person_homepage_auto_creates_candidate(monkeypatch) -> None:
    from app.services.browser_task import BrowserTaskService

    reset_db()

    def fake_run_playwright(self, task_id, target_url):
        return {
            "title": "Jane Chen - Research Engineer at Anthropic",
            "url": "https://www.linkedin.com/in/jane-chen-ai/",
            "text": "Jane Chen is a Research Engineer at Anthropic working on LLM inference and AI infrastructure.",
            "screenshot_path": f"artifacts/browser-tasks/{task_id}.png",
        }

    monkeypatch.setattr(BrowserTaskService, "_run_playwright", fake_run_playwright)

    with TestClient(app) as client:
        created = client.post(
            "/api/browser-tasks",
            json={
                "task_type": "search_candidate",
                "query": "site:linkedin.com/in Anthropic research engineer",
                "target_site": "search_engine",
            },
        )
        candidates = client.get("/api/candidates")

    assert created.status_code == 200
    payload = created.json()
    assert payload["status"] == "waiting_user"
    assert payload["evidence_draft"]["candidate_id"]
    assert payload["evidence_draft"]["company_id"]
    assert "Jane Chen" in payload["evidence_draft"]["summary"]
    assert any(item["name"] == "Jane Chen" for item in candidates.json())


def test_stage5_llm_profile_extraction_fills_linkedin_candidate_fields(monkeypatch) -> None:
    from app.services.browser_task import BrowserTaskService

    reset_db()

    def fake_run_playwright(self, task_id, target_url):
        return {
            "title": "LinkedIn",
            "url": "https://www.linkedin.com/in/alex-kim-llm/",
            "text": "Alex Kim Senior Research Engineer Anthropic San Francisco Bay Area",
            "screenshot_path": f"artifacts/browser-tasks/{task_id}.png",
        }

    def fake_extract(self, **kwargs):
        return {
            "is_person_profile": True,
            "name": "Alex Kim",
            "company": "Anthropic",
            "title": "Senior Research Engineer",
            "department": "Research",
            "location": "San Francisco Bay Area",
            "domain": "LLM / AI Infrastructure",
            "profile_summary": "Research engineer working on LLM infrastructure.",
            "confidence": 0.91,
            "rejection_reason": None,
        }, type("Runtime", (), {"used_fallback": False})()

    monkeypatch.setattr(BrowserTaskService, "_run_playwright", fake_run_playwright)
    monkeypatch.setattr("app.services.llm_gateway.LLMGateway.extract_candidate_profile", fake_extract)

    with TestClient(app) as client:
        created = client.post(
            "/api/browser-tasks",
            json={
                "task_type": "search_candidate",
                "query": "find Anthropic LLM engineers LinkedIn",
                "target_site": "search_engine",
            },
        ).json()
        candidate_id = created["evidence_draft"]["candidate_id"]
        candidate = client.get(f"/api/candidates/{candidate_id}").json()

    assert candidate["name"] == "Alex Kim"
    assert candidate["company_name"] == "Anthropic"
    assert candidate["title"] == "Senior Research Engineer"
    assert candidate["department"] == "Research"
    assert candidate["location"] == "San Francisco Bay Area"
    assert candidate["domain"] == "LLM / AI Infrastructure"


def test_stage5_linkedin_auth_or_signup_page_is_not_a_candidate(monkeypatch) -> None:
    from app.services.browser_task import BrowserTaskService

    reset_db()

    def fake_run_playwright(self, task_id, target_url):
        return {
            "title": "注册 | LinkedIn",
            "url": "https://www.linkedin.com/in/some-profile/",
            "text": "注册 登录 加入 LinkedIn，查看完整档案。没有公开个人资料。",
            "screenshot_path": f"artifacts/browser-tasks/{task_id}.png",
        }

    monkeypatch.setattr(BrowserTaskService, "_run_playwright", fake_run_playwright)

    with TestClient(app) as client:
        before = client.get("/api/candidates").json()
        created = client.post(
            "/api/browser-tasks",
            json={
                "task_type": "search_candidate",
                "query": "site:linkedin.com/in Anthropic engineer",
                "target_site": "search_engine",
            },
        ).json()
        after = client.get("/api/candidates").json()

    assert created["status"] == "failed"
    assert created["evidence_draft"] is None
    assert len(after) == len(before)
    assert all(item["name"] != "注册" for item in after)


def test_stage5_browser_failure_falls_back_and_can_retry(monkeypatch) -> None:
    from app.services.browser_task import BrowserTaskService

    reset_db()

    def fail_playwright(self, task_id, target_url):
        raise RuntimeError("browser unavailable")

    monkeypatch.setattr(BrowserTaskService, "_run_playwright", fail_playwright)

    with TestClient(app) as client:
        created = client.post(
            "/api/browser-tasks",
            json={
                "task_type": "search_candidate",
                "query": "Fallback Query",
                "target_site": "search_engine",
                "candidate_id": "cand_maya_singh",
                "company_id": "company_deepmind",
            },
        ).json()
        retried = client.post(f"/api/browser-tasks/{created['id']}/retry")

    assert created["status"] == "waiting_user"
    assert created["error_message"] == "browser unavailable"
    assert created["evidence_draft"]["confidence"] == 0.45
    assert retried.status_code == 200
    assert retried.json()["status"] == "waiting_user"


def test_stage5_search_page_without_concrete_result_does_not_create_clue(monkeypatch) -> None:
    from app.services.browser_task import BrowserTaskService, NoConcreteResultError

    reset_db()

    def no_result(self, task_id, target_url):
        raise NoConcreteResultError("no concrete result")

    monkeypatch.setattr(BrowserTaskService, "_run_playwright", no_result)

    with TestClient(app) as client:
        created = client.post(
            "/api/browser-tasks",
            json={
                "task_type": "search_candidate",
                "query": "site:linkedin.com/in Anthropic engineer",
                "target_site": "search_engine",
            },
        )

    assert created.status_code == 200
    payload = created.json()
    assert payload["status"] == "failed"
    assert payload["evidence_draft"] is None
    assert "具体候选人相关页面" in payload["result_summary"]


def test_stage5_target_url_encodes_non_ascii_query() -> None:
    from app.services.browser_task import BrowserTaskService

    service = BrowserTaskService()

    url = service._target_url("linkedin", "林晨 OpenAI post-training")

    assert url == (
        "https://www.linkedin.com/search/results/all/?"
        "keywords=%E6%9E%97%E6%99%A8+OpenAI+post-training"
    )
