from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.llm_eval import DatasetSeedResponse, LLMEvalCaseRead, LLMEvalRunRead
from app.services.llm_eval import LLMEvalService

router = APIRouter(prefix="/llm/evals", tags=["llm-evals"])
service = LLMEvalService()


@router.post("/dataset/seed", response_model=DatasetSeedResponse)
def seed_eval_dataset(db: Session = Depends(get_db)) -> DatasetSeedResponse:
    return service.seed_dataset(db)


@router.get("/cases", response_model=list[LLMEvalCaseRead])
def list_eval_cases(db: Session = Depends(get_db)) -> list[LLMEvalCaseRead]:
    return service.list_cases(db)


@router.post("/run", response_model=LLMEvalRunRead)
def run_eval(db: Session = Depends(get_db)) -> LLMEvalRunRead:
    return service.run_eval(db)


@router.get("/latest", response_model=LLMEvalRunRead | None)
def latest_eval(db: Session = Depends(get_db)) -> LLMEvalRunRead | None:
    return service.latest_run(db)
