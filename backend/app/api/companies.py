from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.companies import create_company, list_companies, update_company
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyRead])
def get_companies(db: Session = Depends(get_db)) -> list[CompanyRead]:
    return list_companies(db)


@router.post("", response_model=CompanyRead, status_code=201)
def post_company(payload: CompanyCreate, db: Session = Depends(get_db)) -> CompanyRead:
    return create_company(db, payload)


@router.patch("/{company_id}", response_model=CompanyRead)
def patch_company(
    company_id: str, payload: CompanyUpdate, db: Session = Depends(get_db)
) -> CompanyRead:
    return update_company(db, company_id, payload)
