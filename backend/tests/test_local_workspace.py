from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.models import Candidate
from app.models.workspace import AuditLog, DemoSession, LLMRun
from app.services.document_ingestion import DocumentIngestionService
from app.services.source_connections import SourceConnectionService


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_member_identity_permissions_audit_and_ownership(monkeypatch):
    reset_db()
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_provider", "local")
    monkeypatch.setattr(settings, "llm_api_key", None)
    with TestClient(app) as client:
        assert client.post("/api/session", json={"user_id": "demo_recruiter"}).status_code == 200
        assert client.get("/api/session").json()["role"] == "member"
        assert client.get("/api/manager/summary").status_code == 403
        assert client.get("/api/audit-logs").status_code == 403
        pool = client.post("/api/candidates/cand_lin_chen/add-to-pool").json()
        assert pool["owner_user_id"] == "demo_recruiter"
        feedback = client.post("/api/feedback", json={"candidate_id": "cand_lin_chen", "outcome": "contacted", "user_id": "demo_manager"}).json()
        assert feedback["user_id"] == "demo_recruiter"
        assert client.post("/api/candidates/cand_lin_chen/generate-summary").status_code == 200
        with SessionLocal() as db:
            run = db.scalar(select(LLMRun))
            assert run.user_id == "demo_recruiter"
            assert db.scalar(select(AuditLog).where(AuditLog.path == "/api/feedback")).user_id == "demo_recruiter"
        assert client.delete("/api/session").status_code == 200
        assert client.get("/api/manager/summary").status_code == 200
        with SessionLocal() as db:
            assert db.scalar(select(DemoSession)) is None


def test_relationship_rebuild_decisions_and_stale_hints():
    reset_db()
    with TestClient(app) as client:
        created = client.post("/api/candidates", json={"name": "Demo teammate", "current_company_id": "company_openai", "title": "Engineer", "department": "Post-training Platform"})
        assert created.status_code == 201
        candidate_id = created.json()["id"]
        relationships = client.post("/api/relationship-graph/rebuild").json()
        row = next(item for item in relationships if candidate_id in (item["source_candidate_id"], item["target_candidate_id"]))
        assert row["status"] == "suspected"
        assert row["confidence"] == 0.35
        assert client.patch(f"/api/relationships/{row['id']}", json={"status": "confirmed"}).status_code == 200
        rebuilt = client.post("/api/relationship-graph/rebuild").json()
        assert next(item for item in rebuilt if item["id"] == row["id"])["status"] == "confirmed"
        client.patch(f"/api/relationships/{row['id']}", json={"status": "suspected"})
        with SessionLocal() as db:
            db.get(Candidate, candidate_id).department = "Other"
            db.commit()
        assert not any(item["id"] == row["id"] for item in client.post("/api/relationship-graph/rebuild").json())


def test_source_states_survive_new_service_instances():
    reset_db()
    with TestClient(app):
        SourceConnectionService().update_status("linkedin", "connected")
        assert "linkedin" in SourceConnectionService().connected_private_sources()


def test_uploaded_file_download_and_path_validation(tmp_path, monkeypatch):
    reset_db()
    monkeypatch.setattr(DocumentIngestionService, "upload_dir", tmp_path)
    content = b"Public profile indicates research platform responsibilities."
    with TestClient(app) as client:
        uploaded = client.post("/api/evidence/upload-document", data={"candidate_id": "cand_lin_chen"}, files={"file": ("../../profile.txt", content, "text/plain")})
        assert uploaded.status_code == 200
        evidence_id = uploaded.json()["evidence"]["id"]
        assert client.get(f"/api/evidence/{evidence_id}/document").content == content
        assert client.patch(f"/api/evidence/{evidence_id}", json={}).status_code == 422
        assert client.patch(f"/api/evidence/{evidence_id}", json={"screenshot_path": "upload://../../secrets.txt"}).status_code == 200
        assert client.get(f"/api/evidence/{evidence_id}/document").status_code == 404
        oversized = client.post("/api/evidence/extract-candidates-document", files={"file": ("large.txt", b"x" * (DocumentIngestionService.max_file_bytes + 1), "text/plain")})
        assert oversized.status_code == 413


def test_invalid_updates_and_cancelled_task_cannot_write_evidence(monkeypatch):
    reset_db()
    from app.services.browser_task import BrowserTaskService

    def unavailable(*_args, **_kwargs):
        raise RuntimeError("Browser unavailable in test")

    monkeypatch.setattr(BrowserTaskService, "_run_playwright", unavailable)
    with TestClient(app) as client:
        assert client.patch("/api/candidates/cand_lin_chen", json={"name": None}).status_code == 422
        assert client.patch("/api/companies/company_openai", json={"name": None}).status_code == 422
        created = client.post("/api/browser-tasks", json={
            "task_type": "candidate_update", "query": "Lin Chen latest",
            "target_site": "search_engine", "candidate_id": "cand_lin_chen",
            "company_id": "company_openai",
        })
        assert created.status_code == 200
        task = created.json()
        assert task["status"] == "waiting_user"
        assert task["screenshot_path"] is None
        assert task["evidence_draft"]["screenshot_path"] is None
        client.post(f"/api/browser-tasks/{task['id']}/cancel")
        assert client.post(f"/api/browser-tasks/{task['id']}/confirm-evidence").status_code == 409


def test_analytics_counts_distinct_post_contact_and_usage_events(monkeypatch):
    reset_db()
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_provider", "local")
    monkeypatch.setattr(settings, "llm_api_key", None)
    with TestClient(app) as client:
        client.post("/api/candidates/cand_lin_chen/add-to-pool")
        client.post("/api/feedback", json={"candidate_id": "cand_lin_chen", "outcome": "contacted"})
        client.post("/api/feedback", json={"candidate_id": "cand_maya_singh", "outcome": "contacted"})
        before = {m["key"]: m["value"] for m in client.get("/api/analytics/summary").json()["metrics"]}
        assert before["contact_rate"] == 1
        assert before["feedback_rate"] == 0
        assert before["high_risk_view_rate"] == 0
        assert before["outreach_adoption_rate"] == 0

        client.post("/api/usage-events", json={"candidate_id": "cand_lin_chen", "kind": "candidate_view"})
        client.post("/api/feedback", json={"candidate_id": "cand_lin_chen", "outcome": "interested"})
        assert client.post("/api/candidates/cand_lin_chen/generate-outreach").status_code == 200
        client.post("/api/usage-events", json={"candidate_id": "cand_lin_chen", "kind": "outreach_copy"})
        after = {m["key"]: m["value"] for m in client.get("/api/analytics/summary").json()["metrics"]}
        assert after["feedback_rate"] == 0.5
        assert after["high_risk_view_rate"] > 0
        assert after["outreach_adoption_rate"] == 1
