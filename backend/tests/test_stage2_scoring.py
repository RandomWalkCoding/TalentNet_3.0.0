from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_stage2_get_latest_score() -> None:
    reset_db()
    with TestClient(app) as client:
        response = client.get("/api/candidates/cand_lin_chen/score")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_id"] == "cand_lin_chen"
    assert payload["risk_level"] == "high"


def test_stage2_refresh_score_persists_rules_model() -> None:
    reset_db()
    with TestClient(app) as client:
        response = client.post("/api/candidates/cand_lin_chen/refresh-score")
        detail = client.get("/api/candidates/cand_lin_chen")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_version"] == "rules-v2"
    assert payload["risk_score"] >= 70
    assert "profile_activity" in payload["reason_codes"]
    assert detail.json()["latest_score"]["id"] == payload["id"]
    assert payload["input_snapshot"]["evidence_count"] >= 2
    assert payload["input_snapshot"]["confirmed_count"] >= 2


def test_stage2_missing_candidate_returns_404() -> None:
    reset_db()
    with TestClient(app) as client:
        response = client.get("/api/candidates/missing/score")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CANDIDATE_NOT_FOUND"


def test_stage3_unconfirmed_evidence_forces_review_context() -> None:
    reset_db()
    with TestClient(app) as client:
        created = client.post(
            "/api/evidence",
            json={
                "candidate_id": "cand_maya_singh",
                "company_id": "company_deepmind",
                "source": "manual",
                "title": "Unconfirmed peer movement signal",
                "summary": "A peer movement signal needs manual review before recruiting action.",
                "confidence": 0.52,
                "confirmed_by_user": False,
            },
        )
        score = client.post("/api/candidates/cand_maya_singh/refresh-score")

    assert created.status_code == 201
    assert score.status_code == 200
    payload = score.json()
    assert payload["model_version"] == "rules-v2"
    assert payload["risk_level"] == "needs_review"
    assert payload["input_snapshot"]["unconfirmed_count"] == 1
    assert any("未确认" in item for item in payload["limitations"])


def test_stage3_stale_evidence_is_exposed_in_snapshot() -> None:
    reset_db()
    with TestClient(app) as client:
        created = client.post(
            "/api/evidence",
            json={
                "candidate_id": "cand_zhou_yu",
                "company_id": "company_bytedance",
                "source": "job_site",
                "title": "Old team hiring signal",
                "summary": "Old hiring change signal from the same team.",
                "confidence": 0.78,
                "observed_at": "2025-01-01T00:00:00Z",
                "confirmed_by_user": True,
            },
        )
        score = client.post("/api/candidates/cand_zhou_yu/refresh-score")

    assert created.status_code == 201
    assert score.status_code == 200
    payload = score.json()
    assert payload["input_snapshot"]["stale_count"] >= 1
    assert any("过期证据" in item for item in payload["limitations"])
