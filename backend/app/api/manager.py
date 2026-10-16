from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.identity import require_admin
from app.schemas.manager import ManagerSummary
from app.services.manager_analytics import ManagerAnalyticsService

router = APIRouter(prefix="/manager", tags=["manager"], dependencies=[Depends(require_admin)])
service = ManagerAnalyticsService()


@router.get("/summary", response_model=ManagerSummary)
def get_manager_summary(db: Session = Depends(get_db)) -> ManagerSummary:
    return service.get_summary(db)
