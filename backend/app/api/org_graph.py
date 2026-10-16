from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.org_graph import OrgGraphResponse
from app.services.org_graph import OrgGraphService

router = APIRouter(prefix="/org-graph", tags=["org-graph"])
service = OrgGraphService()


@router.get("", response_model=OrgGraphResponse)
def get_org_graph(
    company_id: str | None = Query(default=None), db: Session = Depends(get_db)
) -> OrgGraphResponse:
    return service.get_graph(db, company_id)
