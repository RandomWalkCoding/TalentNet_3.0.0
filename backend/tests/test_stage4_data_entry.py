from io import BytesIO

from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_stage4_create_and_update_company() -> None:
    reset_db()
    with TestClient(app) as client:
        created = client.post(
            "/api/companies",
            json={
                "name": "Anthropic",
                "industry": "AI Foundation Model",
                "website": "https://www.anthropic.com",
            },
        )
        updated = client.patch(
            f"/api/companies/{created.json()['id']}",
            json={"monitor_status": "paused"},
        )
        duplicated = client.post(
            "/api/companies",
            json={"name": "Anthropic", "industry": "AI"},
        )

    assert created.status_code == 201
    assert updated.status_code == 200
    assert updated.json()["monitor_status"] == "paused"
    assert duplicated.status_code == 409
    assert duplicated.json()["error"]["code"] == "COMPANY_DUPLICATED"


def test_stage4_create_and_update_candidate_refreshes_score() -> None:
    reset_db()
    with TestClient(app) as client:
        company = client.post(
            "/api/companies",
            json={"name": "Moonshot AI", "industry": "AI Application"},
        ).json()
        created = client.post(
            "/api/candidates",
            json={
                "name": "Li Wei",
                "current_company_id": company["id"],
                "title": "Inference Engineer",
                "department": "Infra",
                "domain": "Inference Infrastructure",
                "location": "Beijing",
                "profile_summary": "Manual entry candidate for stage 4.",
            },
        )
        updated = client.patch(
            f"/api/candidates/{created.json()['id']}",
            json={"title": "Senior Inference Engineer"},
        )
        score = client.get(f"/api/candidates/{created.json()['id']}/score")

    assert created.status_code == 201
    assert created.json()["latest_score"]["model_version"] == "rules-v2"
    assert updated.status_code == 200
    assert updated.json()["title"] == "Senior Inference Engineer"
    assert score.status_code == 200
    assert score.json()["risk_level"] == "needs_review"


def test_stage4_import_candidates_csv_reports_duplicates() -> None:
    reset_db()
    csv_content = (
        "name,company_name,industry,title,department,location,domain,profile_summary\n"
        "Ada Chen,MiniMax,AI Application,Research Engineer,Agents,Shanghai,AI Agents,CSV import one\n"
        "Ada Chen,MiniMax,AI Application,Research Engineer,Agents,Shanghai,AI Agents,Duplicate row\n"
        "Bo Zhang,Zhipu AI,AI Foundation Model,Platform Lead,Infra,Beijing,LLM Infra,CSV import two\n"
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/candidates/import-csv",
            files={"file": ("candidates.csv", BytesIO(csv_content.encode("utf-8")), "text/csv")},
        )
        listed = client.get("/api/candidates")

    assert response.status_code == 200
    payload = response.json()
    assert payload["created_count"] == 2
    assert payload["duplicate_count"] == 1
    assert payload["failed_count"] == 0
    names = {item["name"] for item in listed.json()}
    assert {"Ada Chen", "Bo Zhang"}.issubset(names)


def test_stage4_import_candidates_csv_validates_schema() -> None:
    reset_db()
    with TestClient(app) as client:
        response = client.post(
            "/api/candidates/import-csv",
            files={"file": ("bad.csv", BytesIO(b"name,title\nNo Company,Engineer\n"), "text/csv")},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CSV_SCHEMA_INVALID"
