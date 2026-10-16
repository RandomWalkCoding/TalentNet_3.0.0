from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.repositories.candidates import (
    create_candidate,
    get_candidate_detail,
    import_candidates_csv,
    list_candidates,
    update_candidate,
)
from app.schemas.candidate import (
    CandidateCreate,
    CandidateDetail,
    CandidateImportResult,
    CandidateListItem,
    CandidateUpdate,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=list[CandidateListItem])
def get_candidates(
    company_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CandidateListItem]:
    return list_candidates(db, company_id=company_id)


@router.post("", response_model=CandidateDetail, status_code=201)
def post_candidate(
    payload: CandidateCreate, db: Session = Depends(get_db)
) -> CandidateDetail:
    return create_candidate(db, payload)


@router.post("/import-csv", response_model=CandidateImportResult)
async def post_candidates_import_csv(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> CandidateImportResult:
    raw = await file.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        raise AppError("IMPORT_TOO_LARGE", "CSV 文件不能超过 5 MB。", 413)
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            content = raw.decode("gb18030")
        except UnicodeDecodeError as exc:
            raise AppError("CSV_ENCODING_INVALID", "请上传 UTF-8 或 GB18030 编码的 CSV。", 422) from exc
    return import_candidates_csv(db, content)


@router.get("/{candidate_id}", response_model=CandidateDetail)
def get_candidate(candidate_id: str, db: Session = Depends(get_db)) -> CandidateDetail:
    return get_candidate_detail(db, candidate_id)


@router.patch("/{candidate_id}", response_model=CandidateDetail)
def patch_candidate(
    candidate_id: str,
    payload: CandidateUpdate,
    db: Session = Depends(get_db),
) -> CandidateDetail:
    return update_candidate(db, candidate_id, payload)
