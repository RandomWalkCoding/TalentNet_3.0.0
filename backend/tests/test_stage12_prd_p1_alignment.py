from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_stage12_org_graph_returns_company_department_candidate_nodes() -> None:
    reset_db()
    with TestClient(app) as client:
        response = client.get("/api/org-graph?company_id=company_openai")

    assert response.status_code == 200
    payload = response.json()
    assert payload["nodes"]
    assert payload["edges"]
    node_types = {item["type"] for item in payload["nodes"]}
    assert {"company", "department", "candidate"}.issubset(node_types)


def test_stage12_manager_summary_returns_team_metrics() -> None:
    reset_db()
    with TestClient(app) as client:
        client.post("/api/candidates/cand_lin_chen/add-to-pool")
        client.post(
            "/api/feedback",
            json={
                "candidate_id": "cand_lin_chen",
                "outcome": "contacted",
                "contact_channel": "linkedin",
            },
        )
        response = client.get("/api/manager/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"]
    assert payload["team_rows"]
    assert payload["recommended_actions"]
