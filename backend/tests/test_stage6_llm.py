from fastapi.testclient import TestClient
from pydantic_settings import SettingsConfigDict

from app.core.config import Settings
from app.core.database import Base, engine
from app.main import app
from app.services import llm_gateway


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_stage6_generate_summary_cites_evidence() -> None:
    reset_db()
    with TestClient(app) as client:
        response = client.post("/api/candidates/cand_lin_chen/generate-summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "cand_lin_chen"
    assert payload["cited_evidence_ids"]
    assert payload["limitations"]
    assert payload["model_provider"] == "local"
    assert payload["used_fallback"] is True


def test_stage6_generate_outreach_variants() -> None:
    reset_db()
    with TestClient(app) as client:
        response = client.post("/api/candidates/cand_lin_chen/generate-outreach")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "cand_lin_chen"
    assert len(payload["variants"]) == 3
    assert "不会自动发送" in payload["compliance_note"]
    assert all(item["evidence_ids"] for item in payload["variants"])


def test_stage6_missing_candidate_returns_404() -> None:
    reset_db()
    with TestClient(app) as client:
        response = client.post("/api/candidates/missing/generate-summary")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CANDIDATE_NOT_FOUND"


def test_stage6_llm_status_exposes_configuration() -> None:
    reset_db()
    with TestClient(app) as client:
        response = client.get("/api/llm/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["fallback_model"] == "local-structured-v1"
    assert "configured" in payload
    assert "last_error" in payload


def test_stage6_gateway_accepts_openai_compatible_json(monkeypatch) -> None:
    reset_db()
    monkeypatch.setattr(llm_gateway.settings, "llm_provider", "openai")
    monkeypatch.setattr(llm_gateway.settings, "llm_model", "test-model")
    monkeypatch.setattr(llm_gateway.settings, "llm_api_key", "test-key")
    monkeypatch.setattr(llm_gateway.settings, "llm_base_url", "https://llm.example.test/v1")

    def fake_chat_json(self, messages):
        return {
            "summary": "Model summary cited current evidence.",
            "risk_explanation": "Model explanation cited current evidence.",
            "conflict_notes": [],
            "cited_evidence_ids": ["ev_lin_profile"],
            "limitations": ["Human review required."],
        }

    monkeypatch.setattr(llm_gateway.LLMGateway, "_chat_json", fake_chat_json)

    with TestClient(app) as client:
        response = client.post("/api/candidates/cand_lin_chen/generate-summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_provider"] == "openai"
    assert payload["model_name"] == "test-model"
    assert payload["used_fallback"] is False
    assert payload["cited_evidence_ids"] == ["ev_lin_profile"]


def test_stage6_openai_api_key_enables_real_llm_configuration(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.delenv("TALENTNET_LLM_API_KEY", raising=False)
    monkeypatch.delenv("TALENTNET_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("TALENTNET_LLM_MODEL", raising=False)
    monkeypatch.setattr(Settings, "model_config", SettingsConfigDict(env_prefix="TALENTNET_"))

    settings = Settings()

    assert settings.llm_api_key == "test-openai-key"
    assert settings.llm_provider == "openai"
    assert settings.llm_model == "gpt-5.4-mini"


def test_stage6_llm_gateway_uses_relay_json_mode(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(llm_gateway.settings, "llm_provider", "openai")
    monkeypatch.setattr(llm_gateway.settings, "llm_model", "gpt-4o-mini")
    monkeypatch.setattr(llm_gateway.settings, "llm_api_key", "test-key")
    monkeypatch.setattr(llm_gateway.settings, "llm_base_url", "https://cnapi.maolaoapi.com/v1")
    monkeypatch.setattr(llm_gateway.settings, "llm_timeout_seconds", 30)
    monkeypatch.setattr(llm_gateway.settings, "llm_retry_count", 0)

    class FakeResponse:
        headers = {"content-type": "application/json"}
        text = '{"choices":[{"message":{"content":"{\\"ok\\":true}"}}]}'
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"choices": [{"message": {"content": '{"ok":true}'}}]}

    class FakeClient:
        def __init__(self, timeout: float) -> None:
            captured["timeout"] = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, *, headers: dict[str, str], json: dict[str, object]) -> FakeResponse:
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(llm_gateway.httpx, "Client", FakeClient)

    payload = llm_gateway.LLMGateway()._chat_json(
        [{"role": "user", "content": "Return JSON."}],
        temperature=0.1,
        max_tokens=1234,
    )

    assert payload == {"ok": True}
    assert captured["url"] == "https://cnapi.maolaoapi.com/v1/chat/completions"
    assert captured["headers"] == {
        "Authorization": "Bearer test-key",
        "Content-Type": "application/json",
    }
    assert captured["json"] == {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Return JSON."}],
        "temperature": 0.1,
        "max_tokens": 1234,
        "response_format": {"type": "json_object"},
    }
