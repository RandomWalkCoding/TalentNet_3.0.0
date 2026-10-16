from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_stage7_analytics_summary_uses_real_feedback_and_pool() -> None:
    reset_db()
    with TestClient(app) as client:
        client.post("/api/candidates/cand_lin_chen/add-to-pool")
        client.post(
            "/api/feedback",
            json={
                "candidate_id": "cand_lin_chen",
                "outcome": "in_process",
                "contact_channel": "linkedin",
                "note": "进入流程",
            },
        )
        response = client.get("/api/analytics/summary")

    assert response.status_code == 200
    payload = response.json()
    metric_keys = {item["key"] for item in payload["metrics"]}
    assert "feedback_rate" in metric_keys
    assert "success_rate" in metric_keys
    assert "high_risk_coverage_rate" in metric_keys
    assert payload["funnel"][0]["key"] == "high_risk"
    assert any(step["key"] == "success" and step["count"] >= 1 for step in payload["funnel"])
    assert payload["trend"]
