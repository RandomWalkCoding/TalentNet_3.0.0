from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_stage9_seed_eval_dataset_and_run_eval() -> None:
    reset_db()
    with TestClient(app) as client:
        seeded = client.post("/api/llm/evals/dataset/seed")
        cases = client.get("/api/llm/evals/cases")
        run = client.post("/api/llm/evals/run")
        latest = client.get("/api/llm/evals/latest")

    assert seeded.status_code == 200
    assert seeded.json()["created_cases"] >= 3
    assert cases.status_code == 200
    assert len(cases.json()) >= 3
    assert run.status_code == 200
    payload = run.json()
    assert payload["total_cases"] == len(cases.json())
    assert payload["average_score"] >= 0
    assert payload["results"]
    assert latest.status_code == 200
    assert latest.json()["id"] == payload["id"]


def test_stage9_build_and_list_candidate_memory() -> None:
    reset_db()
    with TestClient(app) as client:
        built = client.post("/api/llm/memories/build/cand_lin_chen")
        listed = client.get("/api/llm/memories?candidate_id=cand_lin_chen")
        created = client.post(
            "/api/llm/memories",
            json={
                "candidate_id": "cand_lin_chen",
                "scope": "candidate",
                "kind": "outreach_preference",
                "content": "Prefer concise, evidence-backed outreach.",
                "evidence_ids": ["ev_lin_profile"],
                "weight": 1.2,
                "source": "user",
            },
        )

    assert built.status_code == 200
    assert built.json()["memories"]
    assert listed.status_code == 200
    assert listed.json()[0]["candidate_id"] == "cand_lin_chen"
    assert created.status_code == 200
    assert created.json()["kind"] == "outreach_preference"
