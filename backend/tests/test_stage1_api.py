from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.core.seed import seed_demo_data
from app.main import app


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_stage1_list_companies_and_candidates() -> None:
    reset_db()
    with TestClient(app) as client:
        companies = client.get("/api/companies")
        candidates = client.get("/api/candidates")

    assert companies.status_code == 200
    assert candidates.status_code == 200
    assert len(companies.json()) >= 3
    assert any(item["id"] == "cand_lin_chen" for item in candidates.json())


def test_stage1_candidate_detail_and_evidence() -> None:
    reset_db()
    with TestClient(app) as client:
        detail = client.get("/api/candidates/cand_lin_chen")
        evidence = client.get("/api/evidence?candidate_id=cand_lin_chen")

    assert detail.status_code == 200
    payload = detail.json()
    assert payload["name"] == "林晨"
    assert payload["latest_score"]["risk_level"] == "high"
    assert len(payload["evidence"]) >= 2
    assert evidence.status_code == 200
    assert len(evidence.json()) >= 2


def test_stage1_create_update_and_confirm_evidence_refreshes_score() -> None:
    reset_db()
    with TestClient(app) as client:
        before = client.get("/api/candidates/cand_zhou_yu/score").json()
        created = client.post(
            "/api/evidence",
            json={
                "candidate_id": "cand_zhou_yu",
                "company_id": "company_bytedance",
                "source": "linkedin_visible",
                "title": "Visible profile update requires review",
                "url": "https://example.com/manual/zhou-visible-profile",
                "summary": "Manual evidence says the candidate recently updated AI infra profile tags.",
                "confidence": 0.82,
            },
        )

        assert created.status_code == 201
        payload = created.json()
        assert payload["confirmed_by_user"] is False
        assert payload["confidence"] == 0.82

        updated = client.patch(
            f"/api/evidence/{payload['id']}",
            json={
                "summary": "Manual evidence says the candidate recently updated inference profile tags.",
                "confidence": 0.9,
            },
        )
        assert updated.status_code == 200
        assert updated.json()["confidence"] == 0.9

        confirmed = client.post(f"/api/evidence/{payload['id']}/confirm")
        after = client.get("/api/candidates/cand_zhou_yu/score").json()

    assert confirmed.status_code == 200
    assert confirmed.json()["confirmed_by_user"] is True
    assert after["id"] != before["id"]
    assert after["model_version"] == "rules-v2"


def test_stage1_duplicate_evidence_is_rejected() -> None:
    reset_db()
    body = {
        "candidate_id": "cand_maya_singh",
        "company_id": "company_deepmind",
        "source": "company_site",
        "title": "Same company page signal",
        "url": "https://example.com/manual/maya-same-signal",
        "summary": "Company page shows the same public project signal.",
        "confidence": 0.7,
    }
    with TestClient(app) as client:
        first = client.post("/api/evidence", json=body)
        duplicate = client.post("/api/evidence", json=body)

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EVIDENCE_DUPLICATED"
