from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.browser_task import BrowserTaskCreate, BrowserTaskRead, EvidenceDraftUpdate
from app.schemas.evidence import EvidenceRead
from app.services.browser_task import BrowserTaskService

router = APIRouter(prefix="/browser-tasks", tags=["browser-tasks"])
service = BrowserTaskService()


@router.post("", response_model=BrowserTaskRead)
def create_browser_task(
    payload: BrowserTaskCreate, db: Session = Depends(get_db)
) -> BrowserTaskRead:
    return service.create_task(db, payload)


@router.get("", response_model=list[BrowserTaskRead])
def list_browser_tasks(
    show_history: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[BrowserTaskRead]:
    if not show_history:
        return []
    return service.list_tasks(db)


@router.get("/{task_id}", response_model=BrowserTaskRead)
def get_browser_task(task_id: str, db: Session = Depends(get_db)) -> BrowserTaskRead:
    return service.get_task(db, task_id)


@router.post("/{task_id}/cancel", response_model=BrowserTaskRead)
def cancel_browser_task(task_id: str, db: Session = Depends(get_db)) -> BrowserTaskRead:
    return service.cancel_task(db, task_id)


@router.post("/{task_id}/retry", response_model=BrowserTaskRead)
def retry_browser_task(task_id: str, db: Session = Depends(get_db)) -> BrowserTaskRead:
    return service.retry_task(db, task_id)


@router.patch("/{task_id}/evidence-draft", response_model=BrowserTaskRead)
def update_browser_task_evidence_draft(
    task_id: str,
    payload: EvidenceDraftUpdate,
    db: Session = Depends(get_db),
) -> BrowserTaskRead:
    return service.update_evidence_draft(db, task_id, payload)


@router.post("/{task_id}/confirm-evidence", response_model=EvidenceRead)
def confirm_browser_task_evidence(
    task_id: str, db: Session = Depends(get_db)
) -> EvidenceRead:
    return EvidenceRead.model_validate(service.confirm_evidence(db, task_id))


@router.post("/{task_id}/add-to-pool")
def add_browser_task_result_to_pool(
    task_id: str, db: Session = Depends(get_db)
) -> dict:
    return service.add_result_to_pool(db, task_id)
