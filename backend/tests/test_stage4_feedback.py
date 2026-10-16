from sqlalchemy import select
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.models import Badcase, Candidate, TalentPoolItem


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_stage4_create_and_list_feedback_updates_status() -> None:
    reset_db()
    with TestClient(app) as client:
        pool = client.post("/api/candidates/cand_lin_chen/add-to-pool").json()
        created = client.post(
            "/api/feedback",
            json={
                "candidate_id": "cand_lin_chen",
                "outcome": "interested",
                "contact_channel": "linkedin",
                "note": "愿意进一步了解",
            },
        )
        listed = client.get("/api/feedback?candidate_id=cand_lin_chen")

    assert created.status_code == 200
    assert created.json()["outcome"] == "interested"
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    with SessionLocal() as db:
        candidate = db.get(Candidate, "cand_lin_chen")
        pool_item = db.get(TalentPoolItem, pool["id"])
        assert candidate is not None
        assert pool_item is not None
        assert candidate.follow_status == "contacted"
        assert pool_item.status == "contacted"


def test_stage4_bad_prediction_writes_badcase() -> None:
    reset_db()
    with TestClient(app) as client:
        created = client.post(
            "/api/feedback",
            json={
                "candidate_id": "cand_zhou_yu",
                "outcome": "bad_prediction",
                "note": "实际并无流动意愿，团队缩编判断过重",
            },
        )

    assert created.status_code == 200
    with SessionLocal() as db:
        badcase = db.scalar(select(Badcase).where(Badcase.candidate_id == "cand_zhou_yu"))
        assert badcase is not None
        assert badcase.feedback_id == created.json()["id"]
        assert "团队缩编" in (badcase.user_reason or "")


def test_stage4_invalid_outcome_returns_error() -> None:
    reset_db()
    with TestClient(app) as client:
        response = client.post(
            "/api/feedback",
            json={"candidate_id": "cand_lin_chen", "outcome": "unknown"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_OUTCOME"
