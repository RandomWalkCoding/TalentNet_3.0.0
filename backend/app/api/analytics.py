from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.analytics import AnalyticsSummary
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])
service = AnalyticsService()


@router.get("/summary", response_model=AnalyticsSummary)
def get_analytics_summary(db: Session = Depends(get_db)) -> AnalyticsSummary:
    return service.get_summary(db)
