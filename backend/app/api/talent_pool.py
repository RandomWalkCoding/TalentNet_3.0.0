from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.talent_pool import (
    add_candidate_to_pool,
    delete_talent_pool_item,
    list_talent_pool,
    update_talent_pool_item,
)
from app.schemas.talent_pool import TalentPoolItemRead, TalentPoolUpdate

router = APIRouter(tags=["talent-pool"])


@router.post("/candidates/{candidate_id}/add-to-pool", response_model=TalentPoolItemRead)
def add_to_pool(candidate_id: str, db: Session = Depends(get_db)) -> TalentPoolItemRead:
    return add_candidate_to_pool(db, candidate_id)


@router.get("/talent-pool", response_model=list[TalentPoolItemRead])
def get_talent_pool(
    company_id: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    pending_feedback: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[TalentPoolItemRead]:
    return list_talent_pool(
        db,
        company_id=company_id,
        risk_level=risk_level,
        status=status_filter,
        pending_feedback=pending_feedback,
    )


@router.patch("/talent-pool/{item_id}", response_model=TalentPoolItemRead)
def patch_talent_pool_item(
    item_id: str, payload: TalentPoolUpdate, db: Session = Depends(get_db)
) -> TalentPoolItemRead:
    return update_talent_pool_item(db, item_id, payload)


@router.delete("/talent-pool/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_talent_pool_item(item_id: str, db: Session = Depends(get_db)) -> Response:
    delete_talent_pool_item(db, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
