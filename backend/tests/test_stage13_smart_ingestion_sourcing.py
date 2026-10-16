from io import BytesIO

from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_stage13_extract_candidates_from_unstructured_document() -> None:
    reset_db()
    content = (
        "Maya Patel, Senior Inference Engineer at OpenAI, San Francisco, GPU inference.\n"
        "Name: Ravi Singh; Company: Google DeepMind; Title: Agent Systems Engineer; London."
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/evidence/extract-candidates-document",
            files={"file": ("talent-notes.any", BytesIO(content.encode("utf-8")), "application/octet-stream")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_count"] >= 2
    assert any(item["company_name"] == "OpenAI" for item in payload["candidates"])


def test_stage13_sourcing_public_web_and_connected_sources(monkeypatch) -> None:
    from app.services.browser_task import BrowserTaskService

    reset_db()

    def fake_run_playwright(self, task_id, target_url):
        return {
            "title": "Synthetic sourcing result",
            "url": target_url,
            "text": "Candidate profile search result with AI infrastructure signals.",
            "screenshot_path": f"artifacts/browser-tasks/{task_id}.png",
        }

    def fake_discover(self, query, target_site="search_engine", limit=8):
        return [f"https://www.linkedin.com/in/synthetic-candidate-{index}/" for index in range(limit)]

    def fake_collect(self, query, target_site="search_engine", limit=10):
        return []

    monkeypatch.setattr(BrowserTaskService, "_run_playwright", fake_run_playwright)
    monkeypatch.setattr(BrowserTaskService, "discover_candidate_pages", fake_discover)
    monkeypatch.setattr(BrowserTaskService, "collect_search_results", fake_collect)

    with TestClient(app) as client:
        public_response = client.post(
            "/api/sourcing/run",
            json={
                "talent_profile": "LLM inference engineer San Francisco GPU optimization",
                "target_count": 25,
                "public_site_scope": "linkedin.com/in",
                "max_tasks": 4,
            },
        )
        client.patch("/api/source-connections/linkedin", json={"status": "connected"})
        connected_response = client.post(
            "/api/sourcing/run",
            json={
                "talent_profile": "AI agent research scientist London",
                "target_count": 10,
                "max_tasks": 3,
            },
        )

    assert public_response.status_code == 200
    public_payload = public_response.json()
    assert public_payload["tasks"]
    assert all(task["query"].startswith("https://www.linkedin.com/in/") for task in public_payload["tasks"])
    assert "site:linkedin.com/in" in public_payload["query_plan"][0]["query"]
    assert connected_response.status_code == 200
    assert any(
        item["target_site"] == "linkedin"
        for item in connected_response.json()["query_plan"]
    )


def test_stage13_sourcing_prompt_is_transformed_into_search_query(monkeypatch) -> None:
    from app.services.browser_task import BrowserTaskService

    reset_db()

    def fake_run_playwright(self, task_id, target_url):
        return {
            "title": "Synthetic AI retrieval result",
            "url": target_url,
            "text": "LinkedIn public profile result for Anthropic AI infrastructure engineer.",
            "screenshot_path": f"artifacts/browser-tasks/{task_id}.png",
        }

    def fake_discover(self, query, target_site="search_engine", limit=8):
        return []

    def fake_collect(self, query, target_site="search_engine", limit=10):
        return []

    monkeypatch.setattr(BrowserTaskService, "_run_playwright", fake_run_playwright)
    monkeypatch.setattr(BrowserTaskService, "discover_candidate_pages", fake_discover)
    monkeypatch.setattr(BrowserTaskService, "collect_search_results", fake_collect)

    prompt = "帮我去 Google 检索 LinkedIn 页面，找到 Claude 的全部技术人员"
    with TestClient(app) as client:
        response = client.post(
            "/api/sourcing/run",
            json={
                "talent_profile": prompt,
                "target_count": 20,
                "max_tasks": 2,
            },
        )

    assert response.status_code == 200
    query = response.json()["query_plan"][0]["query"]
    assert query != prompt
    assert "site:linkedin.com/in" in query
    assert "Claude" in query


def test_stage13_sourcing_does_not_turn_search_query_into_candidate_when_no_results(monkeypatch) -> None:
    from app.services.browser_task import BrowserTaskService

    reset_db()

    def fake_collect(self, query, target_site="search_engine", limit=10):
        return []

    def fake_discover(self, query, target_site="search_engine", limit=8):
        return []

    monkeypatch.setattr(BrowserTaskService, "collect_search_results", fake_collect)
    monkeypatch.setattr(BrowserTaskService, "discover_candidate_pages", fake_discover)

    prompt = "帮我检索 LinkedIn 公开 Claude Anthropic 的技术人员"
    with TestClient(app) as client:
        response = client.post(
            "/api/sourcing/run",
            json={
                "talent_profile": prompt,
                "target_count": 5,
                "max_tasks": 2,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tasks"] == []
    assert payload["extracted_candidates"] == []


def test_stage13_sourcing_extracts_structured_candidate_leads(monkeypatch) -> None:
    from app.services.browser_task import BrowserTaskService
    from app.services.llm_gateway import LLMGateway, LLMRuntime

    reset_db()

    def fake_plan(self, **kwargs):
        return [
            {
                "target_site": "search_engine",
                "query": "site:linkedin.com/in Anthropic research engineer",
                "mode": "public_web",
                "reason": "Find profile pages.",
            }
        ], LLMRuntime("minimax", "MiniMax-M2", False)

    def fake_run_playwright(self, task_id, target_url):
        return {
            "title": "Jane Chen - Research Engineer at Anthropic",
            "url": target_url,
            "text": "Jane Chen is a Research Engineer at Anthropic working on LLM inference.",
            "screenshot_path": f"artifacts/browser-tasks/{task_id}.png",
        }

    def fake_discover(self, query, target_site="search_engine", limit=8):
        return ["https://www.linkedin.com/in/jane-chen-ai/"]

    def fake_collect(self, query, target_site="search_engine", limit=10):
        return []

    def fake_extract_leads(self, **kwargs):
        return [
            {
                "full_name": "Jane Chen",
                "current_company": "Anthropic",
                "title": "Research Engineer",
                "profile_links": ["https://www.linkedin.com/in/jane-chen-ai/"],
                "source_snippet": "Jane Chen is a Research Engineer at Anthropic.",
                "confidence": 0.93,
            }
        ], LLMRuntime("minimax", "MiniMax-M2", False)

    monkeypatch.setattr(LLMGateway, "generate_sourcing_plan", fake_plan)
    monkeypatch.setattr(LLMGateway, "extract_candidate_leads_from_search_results", fake_extract_leads)
    monkeypatch.setattr(BrowserTaskService, "_run_playwright", fake_run_playwright)
    monkeypatch.setattr(BrowserTaskService, "discover_candidate_pages", fake_discover)
    monkeypatch.setattr(BrowserTaskService, "collect_search_results", fake_collect)

    with TestClient(app) as client:
        response = client.post(
            "/api/sourcing/run",
            json={
                "talent_profile": "Find Anthropic research engineers on LinkedIn",
                "target_count": 5,
                "max_tasks": 1,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_used"] is True
    assert payload["model_provider"] == "minimax"
    assert payload["extracted_candidates"][0]["full_name"] == "Jane Chen"
    assert payload["extracted_candidates"][0]["current_company"] == "Anthropic"
    assert payload["extracted_candidates"][0]["task_id"] == payload["tasks"][0]["id"]
    assert payload["tasks"][0]["query"] == "https://www.linkedin.com/in/jane-chen-ai/"


def test_stage13_sourcing_uses_search_result_cards_without_opening_profiles(monkeypatch) -> None:
    from app.services.browser_task import BrowserTaskService
    from app.services.llm_gateway import LLMGateway, LLMRuntime

    reset_db()

    def fake_plan(self, **kwargs):
        return [
            {
                "target_site": "search_engine",
                "query": "site:linkedin.com/in Anthropic research engineer",
                "mode": "public_web",
                "reason": "Find profile pages.",
            }
        ], LLMRuntime("minimax", "MiniMax-M2", False)

    def fake_collect(self, query, target_site="search_engine", limit=10):
        return [
            {
                "title": "Jane Chen - Research Engineer at Anthropic | LinkedIn",
                "url": "https://www.linkedin.com/in/jane-chen-ai/",
                "snippet": "Jane Chen is a Research Engineer at Anthropic working on LLM inference systems.",
                "source": "search_result",
            }
        ]

    def fail_if_open_profile(self, task_id, target_url):
        raise AssertionError("profile page should not be opened when Google result cards are enough")

    def fake_extract_leads(self, **kwargs):
        assert kwargs["search_results"][0]["source"] == "search_result"
        return [
            {
                "full_name": "Jane Chen",
                "current_company": "Anthropic",
                "title": "Research Engineer",
                "profile_links": ["https://www.linkedin.com/in/jane-chen-ai/"],
                "source_snippet": "Jane Chen is a Research Engineer at Anthropic.",
                "confidence": 0.94,
            }
        ], LLMRuntime("minimax", "MiniMax-M2", False)

    monkeypatch.setattr(LLMGateway, "generate_sourcing_plan", fake_plan)
    monkeypatch.setattr(LLMGateway, "extract_candidate_leads_from_search_results", fake_extract_leads)
    monkeypatch.setattr(BrowserTaskService, "collect_search_results", fake_collect)
    monkeypatch.setattr(BrowserTaskService, "_run_playwright", fail_if_open_profile)

    with TestClient(app) as client:
        response = client.post(
            "/api/sourcing/run",
            json={
                "talent_profile": "Find Anthropic research engineers on LinkedIn",
                "target_count": 5,
                "max_tasks": 1,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tasks"] == []
    assert payload["extracted_candidates"][0]["full_name"] == "Jane Chen"
    assert payload["extracted_candidates"][0]["task_id"] is None


def test_stage13_google_result_cards_fill_company_and_title() -> None:
    from app.services.llm_gateway import LLMGateway

    gateway = LLMGateway()
    results = [
        {
            "title": "Lin Chen - Senior Research Engineer at OpenAI | LinkedIn",
            "url": "https://www.linkedin.com/in/lin-chen-ai/",
            "snippet": "OpenAI · Post-training Platform · San Francisco. Works on LLM reasoning systems.",
            "source": "search_result",
        },
        {
            "title": "Ravi Singh - Member of Technical Staff at Anthropic | LinkedIn",
            "url": "https://www.linkedin.com/in/ravi-singh-llm/",
            "snippet": "Anthropic · AI safety and inference infrastructure · London.",
            "source": "search_result",
        },
    ]

    leads = gateway._local_candidate_leads(results, 10)

    assert leads[0]["full_name"] == "Lin Chen"
    assert leads[0]["current_company"] == "OpenAI"
    assert leads[0]["title"] == "Senior Research Engineer"
    assert leads[1]["current_company"] == "Anthropic"
    assert leads[1]["title"] == "Member of Technical Staff"


def test_stage13_linkedin_google_card_extracts_location_role_company_order() -> None:
    from app.services.llm_gateway import LLMGateway

    gateway = LLMGateway()
    results = [
        {
            "title": "Sarah Tsetsilas - Vice President of AI Infrastructure at ...",
            "url": "https://www.linkedin.com/in/sarah-tsetsilas/",
            "snippet": (
                "United States · Vice President, AI Infrastructure · Anthropic "
                "AI executive with nearly two decades of experience building scalable distributed systems."
            ),
            "source": "search_result",
        }
    ]

    leads = gateway._local_candidate_leads(results, 10)

    assert leads[0]["full_name"] == "Sarah Tsetsilas"
    assert leads[0]["current_company"] == "Anthropic"
    assert leads[0]["title"] == "Vice President, AI Infrastructure"


def test_stage13_google_result_cards_keep_education_empty_in_stable_mode() -> None:
    from app.services.llm_gateway import LLMGateway

    gateway = LLMGateway()
    results = [
        {
            "title": "Maya Rao - Research Engineer at Anthropic | LinkedIn",
            "url": "https://www.linkedin.com/in/maya-rao-ai/",
            "snippet": "Research Engineer at Anthropic. Education: Stanford University. Works on inference systems.",
            "source": "search_result",
        }
    ]

    leads = gateway._local_candidate_leads(results, 10)

    assert leads[0]["full_name"] == "Maya Rao"
    assert leads[0]["current_company"] == "Anthropic"
    assert leads[0]["title"] == "Research Engineer"
    assert leads[0]["education"] is None


def test_stage13_incomplete_google_result_does_not_reuse_name_as_company() -> None:
    from app.services.llm_gateway import LLMGateway

    gateway = LLMGateway()
    results = [
        {
            "title": "Peter Lofgren | LinkedIn",
            "url": "https://www.linkedin.com/in/peterlofgren/",
            "snippet": "Peter Lofgren LinkedIn profile result.",
            "source": "search_result",
        }
    ]

    leads = gateway._local_candidate_leads(results, 10)

    assert leads[0]["full_name"] == "Peter Lofgren"
    assert leads[0]["current_company"] is None
    assert leads[0]["title"] is None
    assert leads[0]["education"] is None


def test_stage13_complete_google_result_extracts_name_company_and_title() -> None:
    from app.services.llm_gateway import LLMGateway

    gateway = LLMGateway()
    results = [
        {
            "title": "Peter Lofgren - Staff Software Engineer at Anthropic | LinkedIn",
            "url": "https://www.linkedin.com/in/peterlofgren/",
            "snippet": "Staff Software Engineer at Anthropic. Education: Stanford University.",
            "source": "search_result",
        }
    ]

    leads = gateway._local_candidate_leads(results, 10)

    assert leads[0]["full_name"] == "Peter Lofgren"
    assert leads[0]["current_company"] == "Anthropic"
    assert leads[0]["title"] == "Staff Software Engineer"
    assert leads[0]["education"] is None


def test_stage13_sparse_result_uses_search_context_for_company_and_title() -> None:
    from app.services.llm_gateway import LLMGateway

    gateway = LLMGateway()
    results = [
        {
            "title": "Scott Emmons | LinkedIn",
            "url": "https://www.linkedin.com/in/scott-emmons-5258005b",
            "snippet": "Scott Emmons B",
            "query": 'site:linkedin.com/in Anthropic "AI safety" "Research Scientist"',
            "user_intent": "搜索 Anthropic AI safety research scientist LinkedIn 个人主页",
            "source": "search_result",
        },
        {
            "title": "Jiatong Han | LinkedIn",
            "url": "https://uk.linkedin.com/in/jiatong-han-",
            "snippet": "Jiatong Han",
            "query": 'site:linkedin.com/in "Google DeepMind" "Research Engineer" Gemini',
            "user_intent": "寻找 Google DeepMind Gemini 相关的 research engineer LinkedIn 页面",
            "source": "search_result",
        },
    ]

    leads = gateway._local_candidate_leads(results, 10)

    assert leads[0]["current_company"] == "Anthropic"
    assert leads[0]["title"] == "Research Scientist"
    assert leads[1]["current_company"] == "Google DeepMind"
    assert leads[1]["title"] == "Research Engineer"


def test_stage13_sparse_result_understands_ai_company_and_role_aliases() -> None:
    from app.services.llm_gateway import LLMGateway

    gateway = LLMGateway()
    results = [
        {
            "title": "Pratham Reddy | LinkedIn",
            "url": "https://www.linkedin.com/in/prathamreddy9441",
            "snippet": "Prathamreddy",
            "query": "site:linkedin.com/in Perplexity AI LLM engineer",
            "user_intent": "找 Perplexity AI 的搜索/推荐/LLM 工程师个人主页",
            "source": "search_result",
        },
        {
            "title": "Xinyu Wang | LinkedIn",
            "url": "https://www.linkedin.com/in/xinyuwang1126",
            "snippet": "Xinyuwang",
            "query": 'site:linkedin.com/in Google DeepMind CMU "ML Engineer"',
            "user_intent": "找 CMU 校友在 Google DeepMind 做 ML Engineer 的候选人",
            "source": "search_result",
        },
    ]

    leads = gateway._local_candidate_leads(results, 10)

    assert leads[0]["current_company"] == "Perplexity AI"
    assert leads[0]["title"] == "LLM Engineer"
    assert leads[1]["current_company"] == "Google DeepMind"
    assert leads[1]["title"] == "Machine Learning Engineer"
    assert leads[1]["education"] is None


def test_stage13_linkedin_slug_id_suffix_is_not_part_of_name() -> None:
    from app.services.llm_gateway import LLMGateway

    gateway = LLMGateway()
    results = [
        {
            "title": "Scott Emmons B | LinkedIn",
            "url": "https://www.linkedin.com/in/scott-emmons-5258005b",
            "snippet": "Scott Emmons B",
            "query": 'site:linkedin.com/in Anthropic "AI safety" "Research Scientist"',
            "user_intent": "Find Anthropic AI safety research scientists",
            "source": "search_result",
        },
        {
            "title": "Kaiwen Zhou Abbb | LinkedIn",
            "url": "https://www.linkedin.com/in/kaiwen-zhou-a21b241bb",
            "snippet": "Kaiwen Zhou Abbb",
            "query": 'site:linkedin.com/in Anthropic "AI safety" "Research Scientist"',
            "user_intent": "Find Anthropic AI safety research scientists",
            "source": "search_result",
        },
    ]

    leads = gateway._local_candidate_leads(results, 10)

    assert leads[0]["full_name"] == "Scott Emmons"
    assert leads[1]["full_name"] == "Kaiwen Zhou"


def test_stage13_aggressive_inference_from_noisy_chinese_and_mixed_snippets() -> None:
    from app.services.llm_gateway import LLMGateway

    gateway = LLMGateway()
    results = [
        {
            "title": "Rahul V Mishra | LinkedIn",
            "url": "https://www.linkedin.com/in/rahulvmishra/",
            "snippet": "Rahul V Mishra | 字节跳动前沿技术负责人。Rahul曾就读于上海交大，目前带领团队。",
            "source": "search_result",
        },
        {
            "title": "Madeleine Shea B - AI Researcher",
            "url": "https://www.linkedin.com/in/madeleine-shea-b/",
            "snippet": "曾在微软亚洲研究院实习，现就读于 CMU 计算机系。",
            "source": "search_result",
        },
        {
            "title": "Michaeltingley 个人履历 - 百度资深架构师的博客",
            "url": "https://www.linkedin.com/in/michaeltingley/",
            "snippet": "Michaeltingley 个人履历 - 百度资深架构师的博客",
            "source": "search_result",
        },
    ]

    leads = gateway._local_candidate_leads(results, 10)

    assert leads[0]["current_company"] == "字节跳动"
    assert leads[0]["title"] == "前沿技术负责人"
    assert leads[0]["education"] is None
    assert leads[1]["current_company"] == "微软亚洲研究院"
    assert leads[1]["title"] == "AI Researcher"
    assert leads[1]["education"] is None
    assert leads[2]["current_company"] == "百度"
    assert leads[2]["title"] == "资深架构师"


def test_stage13_llm_leads_are_enriched_from_matching_google_result() -> None:
    from app.services.llm_gateway import LLMGateway

    gateway = LLMGateway()
    search_results = [
        {
            "title": "Lin Chen - Senior Research Engineer at OpenAI | LinkedIn",
            "url": "https://www.linkedin.com/in/lin-chen-ai/",
            "snippet": "OpenAI · Post-training Platform · San Francisco.",
            "source": "search_result",
        }
    ]

    lead = gateway._clean_candidate_lead(
        {
            "full_name": "Lin Chen",
            "current_company": None,
            "title": None,
            "profile_links": ["https://www.linkedin.com/in/lin-chen-ai/"],
            "source_snippet": None,
            "confidence": 0.1,
        },
        search_results,
    )

    assert lead["current_company"] == "OpenAI"
    assert lead["title"] == "Senior Research Engineer"
    assert lead["confidence"] >= 0.72


def test_stage13_linkedin_profile_text_enriches_required_fields() -> None:
    from app.services.llm_gateway import LLMGateway

    gateway = LLMGateway()
    search_results = [
        {
            "title": "Maya Rao | LinkedIn",
            "url": "https://www.linkedin.com/in/maya-rao-ai/",
            "snippet": "Maya Rao LinkedIn profile.",
            "profile_page_title": "Maya Rao - Research Engineer at Anthropic | LinkedIn",
            "profile_page_text": "\n".join(
                [
                    "Maya Rao",
                    "Research Engineer at Anthropic",
                    "San Francisco",
                    "Experience",
                    "Anthropic",
                    "Research Engineer",
                    "Education",
                    "Stanford University",
                ]
            ),
            "source": "search_result",
        }
    ]

    lead = gateway._clean_candidate_lead(
        {
            "full_name": None,
            "current_company": None,
            "title": None,
            "education": None,
            "profile_links": ["https://www.linkedin.com/in/maya-rao-ai/"],
            "source_snippet": None,
            "confidence": 0.1,
        },
        search_results,
    )

    assert lead["full_name"] == "Maya Rao"
    assert lead["current_company"] == "Anthropic"
    assert lead["title"] == "Research Engineer"
    assert lead["education"] is None


def test_stage13_linkedin_slug_names_are_split_when_title_is_url_only() -> None:
    from app.services.llm_gateway import LLMGateway

    gateway = LLMGateway()
    results = [
        {
            "title": "https://www.linkedin.com/in/tylerlacroix",
            "url": "https://www.linkedin.com/in/tylerlacroix",
            "snippet": "LinkedIn public profile result.",
            "source": "search_result",
        },
        {
            "title": "https://www.linkedin.com/in/scottgoodfriend",
            "url": "https://www.linkedin.com/in/scottgoodfriend",
            "snippet": "LinkedIn public profile result.",
            "source": "search_result",
        },
        {
            "title": "Craig Citro - Staff Software Engineer | LinkedIn",
            "url": "https://www.linkedin.com/in/craigcitro",
            "snippet": "Staff Software Engineer at Anthropic.",
            "source": "search_result",
        },
    ]

    leads = gateway._local_candidate_leads(results, 10)

    assert leads[0]["full_name"] == "Tyler Lacroix"
    assert leads[1]["full_name"] == "Scott Goodfriend"
    assert leads[2]["full_name"] == "Craig Citro"


def test_stage13_llm_compact_name_is_cleaned_from_profile_link() -> None:
    from app.services.llm_gateway import LLMGateway

    gateway = LLMGateway()
    lead = gateway._clean_candidate_lead(
        {
            "full_name": "tylerlacroix",
            "current_company": None,
            "title": None,
            "profile_links": ["https://www.linkedin.com/in/tylerlacroix"],
            "source_snippet": "LinkedIn profile result.",
            "confidence": 0.5,
        },
        [],
    )

    assert lead["full_name"] == "Tyler Lacroix"


def test_stage13_save_candidate_lead_creates_candidate() -> None:
    reset_db()
    with TestClient(app) as client:
        response = client.post(
            "/api/sourcing/leads/save",
            json={
                "full_name": "Jane Chen",
                "current_company": "Anthropic",
                "title": "Research Engineer",
                "education": "Stanford University",
                "profile_links": ["https://www.linkedin.com/in/jane-chen-ai/"],
                "source_snippet": "Jane Chen is a Research Engineer at Anthropic.",
                "confidence": 0.94,
            },
        )
        candidates = client.get("/api/candidates").json()
        talent_pool = client.get("/api/talent-pool").json()

    assert response.status_code == 200
    assert any(item["name"] == "Jane Chen" and item["company_name"] == "Anthropic" for item in candidates)
    assert any(item["candidate_name"] == "Jane Chen" and item["company_name"] == "Anthropic" for item in talent_pool)
