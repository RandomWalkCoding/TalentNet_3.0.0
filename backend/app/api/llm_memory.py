from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.llm_memory import LLMMemoryCreate, LLMMemoryRead, MemoryBuildResponse
from app.services.llm_memory import LLMMemoryService

router = APIRouter(prefix="/llm/memories", tags=["llm-memory"])
service = LLMMemoryService()


@router.get("", response_model=list[LLMMemoryRead])
def list_memories(
    candidate_id: str | None = None, db: Session = Depends(get_db)
) -> list[LLMMemoryRead]:
    return service.list_memories(db, candidate_id)


@router.post("", response_model=LLMMemoryRead)
def create_memory(
    payload: LLMMemoryCreate, db: Session = Depends(get_db)
) -> LLMMemoryRead:
    return service.create_memory(db, payload)


@router.post("/build/{candidate_id}", response_model=MemoryBuildResponse)
def build_candidate_memory(
    candidate_id: str, db: Session = Depends(get_db)
) -> MemoryBuildResponse:
    return service.build_candidate_memory(db, candidate_id)
