from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.evidence import EvidenceRepository
from app.schemas.evidence import (
    DocumentCandidateExtractionResponse,
    EvidenceCreate,
    EvidenceDocumentUploadResponse,
    EvidenceRead,
    EvidenceUpdate,
)
from app.services.document_ingestion import DocumentIngestionService
from app.core.errors import AppError
from app.models import Evidence

router = APIRouter(prefix="/evidence", tags=["evidence"])
repository = EvidenceRepository()
document_service = DocumentIngestionService()


@router.get("", response_model=list[EvidenceRead])
def get_evidence(
    candidate_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[EvidenceRead]:
    return repository.list(db, candidate_id=candidate_id)


@router.post("", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED)
def create_evidence(
    payload: EvidenceCreate,
    db: Session = Depends(get_db),
) -> EvidenceRead:
    return EvidenceRead.model_validate(repository.create(db, payload))


@router.post("/upload-document", response_model=EvidenceDocumentUploadResponse)
async def upload_evidence_document(
    candidate_id: str = Form(...),
    company_id: str | None = Form(default=None),
    confirmed_by_user: bool = Form(default=False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> EvidenceDocumentUploadResponse:
    content = await file.read(document_service.max_file_bytes + 1)
    return document_service.upload_document(
        db,
        candidate_id=candidate_id,
        company_id=company_id,
        filename=file.filename or "uploaded-document",
        content_type=file.content_type,
        content=content,
        confirmed_by_user=confirmed_by_user,
    )


@router.post("/extract-candidates-document", response_model=DocumentCandidateExtractionResponse)
async def extract_candidates_document(
    file: UploadFile = File(...),
) -> DocumentCandidateExtractionResponse:
    content = await file.read(document_service.max_file_bytes + 1)
    return document_service.extract_candidate_drafts(
        filename=file.filename or "uploaded-document",
        content_type=file.content_type,
        content=content,
    )


@router.get("/{evidence_id}/document")
def download_evidence_document(evidence_id: str, db: Session = Depends(get_db)) -> FileResponse:
    evidence = db.get(Evidence, evidence_id)
    if evidence is None or evidence.source != "uploaded_document":
        raise AppError("DOCUMENT_NOT_FOUND", "上传文档不存在。", 404)
    path = document_service.document_path(evidence.screenshot_path)
    if path is None or not path.is_file():
        raise AppError("DOCUMENT_NOT_FOUND", "原始文件未保存或不可用。", 404)
    return FileResponse(path, filename=path.name)


@router.patch("/{evidence_id}", response_model=EvidenceRead)
def update_evidence(
    evidence_id: str,
    payload: EvidenceUpdate,
    db: Session = Depends(get_db),
) -> EvidenceRead:
    return EvidenceRead.model_validate(repository.update(db, evidence_id, payload))


@router.post("/{evidence_id}/confirm", response_model=EvidenceRead)
def confirm_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
) -> EvidenceRead:
    return EvidenceRead.model_validate(repository.confirm(db, evidence_id))
