from io import BytesIO

from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_stage11_upload_document_creates_confirmed_evidence() -> None:
    reset_db()
    content = (
        "Recent public document notes that the candidate updated profile scope, "
        "reduced publication cadence, and moved toward platform ownership."
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/evidence/upload-document",
            data={
                "candidate_id": "cand_lin_chen",
                "company_id": "company_openai",
                "confirmed_by_user": "true",
            },
            files={
                "file": (
                    "lin-chen-signal.txt",
                    BytesIO(content.encode("utf-8")),
                    "text/plain",
                )
            },
        )
        evidence = client.get("/api/evidence?candidate_id=cand_lin_chen")
        score = client.get("/api/candidates/cand_lin_chen/score")

    assert response.status_code == 200
    payload = response.json()
    assert payload["confirmed"] is True
    assert payload["extracted_characters"] > 20
    assert payload["evidence"]["source"] == "uploaded_document"
    assert payload["evidence"]["confirmed_by_user"] is True
    assert any(item["source"] == "uploaded_document" for item in evidence.json())
    assert score.status_code == 200


def test_stage11_upload_empty_document_returns_validation_error() -> None:
    reset_db()
    with TestClient(app) as client:
        response = client.post(
            "/api/evidence/upload-document",
            data={"candidate_id": "cand_lin_chen"},
            files={"file": ("empty.txt", BytesIO(b"   "), "text/plain")},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "DOCUMENT_TEXT_EMPTY"
