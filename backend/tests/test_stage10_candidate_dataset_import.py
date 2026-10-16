from pathlib import Path
import csv

from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


DATASET_DIR = Path(__file__).resolve().parents[2] / "outputs" / "candidate_dataset"


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_stage10_import_generated_candidate_dataset() -> None:
    reset_db()
    csv_path = DATASET_DIR / "talentnet_candidates_500_import.csv"
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        first_import_name = next(csv.DictReader(handle))["name"]

    with TestClient(app) as client:
        response = client.post(
            "/api/candidates/import-csv",
            files={
                "file": (
                    csv_path.name,
                    csv_path.read_bytes(),
                    "text/csv",
                )
            },
        )
        listed = client.get("/api/candidates")

    assert response.status_code == 200
    payload = response.json()
    assert payload["created_count"] == 500
    assert payload["duplicate_count"] == 0
    assert payload["failed_count"] == 0
    names = {item["name"] for item in listed.json()}
    assert len(listed.json()) == 503
    assert first_import_name in names
