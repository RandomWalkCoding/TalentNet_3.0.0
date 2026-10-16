from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_stage3_add_and_list_talent_pool_sorted() -> None:
    reset_db()
    with TestClient(app) as client:
        add_response = client.post("/api/candidates/cand_lin_chen/add-to-pool")
        list_response = client.get("/api/talent-pool")

    assert add_response.status_code == 200
    assert list_response.status_code == 200
    items = list_response.json()
    assert items[0]["candidate_id"] == "cand_lin_chen"
    assert items[0]["risk_level"] == "high"


def test_stage3_update_talent_pool_item() -> None:
    reset_db()
    with TestClient(app) as client:
        item = client.post("/api/candidates/cand_zhou_yu/add-to-pool").json()
        updated = client.patch(
            f"/api/talent-pool/{item['id']}",
            json={"status": "contacted", "priority": "medium", "note": "已加入本周触达"},
        )

    assert updated.status_code == 200
    payload = updated.json()
    assert payload["status"] == "contacted"
    assert payload["priority"] == "medium"
    assert payload["note"] == "已加入本周触达"


def test_stage3_delete_talent_pool_item() -> None:
    reset_db()
    with TestClient(app) as client:
        item = client.post("/api/candidates/cand_maya_singh/add-to-pool").json()
        removed = client.delete(f"/api/talent-pool/{item['id']}")
        listed = client.get("/api/talent-pool")

    assert removed.status_code == 204
    assert all(entry["id"] != item["id"] for entry in listed.json())
