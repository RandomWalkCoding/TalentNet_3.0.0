import csv
import json
import re
from hashlib import sha256
from pathlib import Path
from datetime import datetime, timezone
from io import BytesIO, StringIO

from docx import Document
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.config import BACKEND_DIR
from app.repositories.evidence import EvidenceRepository
from app.schemas.evidence import (
    DocumentCandidateExtractionResponse,
    EvidenceCreate,
    EvidenceDocumentUploadResponse,
    ExtractedCandidateDraft,
)


class DocumentIngestionService:
    max_text_chars = 12000
    max_file_bytes = 10 * 1024 * 1024
    upload_dir = BACKEND_DIR / "data" / "uploads"

    def __init__(self) -> None:
        self.evidence_repository = EvidenceRepository()

    def upload_document(
        self,
        db: Session,
        *,
        candidate_id: str,
        company_id: str | None,
        filename: str,
        content_type: str | None,
        content: bytes,
        confirmed_by_user: bool,
    ) -> EvidenceDocumentUploadResponse:
        self._check_file_size(content)
        text = self._extract_text(filename, content_type, content)
        if not text.strip():
            raise AppError(
                code="DOCUMENT_TEXT_EMPTY",
                message="Uploaded document did not contain readable text.",
                status_code=422,
            )
        self.evidence_repository._validate_candidate_and_company(db, candidate_id, company_id)
        trimmed = " ".join(text.split())[: self.max_text_chars]
        suffix = Path(filename).suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,8}", suffix):
            suffix = ".bin"
        stored_name = f"{sha256(content).hexdigest()}{suffix}"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        stored_path = self.upload_dir / stored_name
        if not stored_path.exists():
            stored_path.write_bytes(content)
        evidence = self.evidence_repository.create(
            db,
            EvidenceCreate(
                candidate_id=candidate_id,
                company_id=company_id,
                source="uploaded_document",
                title=f"上传文档：{filename[:180]}",
                url=None,
                screenshot_path=f"upload://{stored_name}",
                observed_at=datetime.now(timezone.utc),
                event_time=None,
                summary=self._summary(trimmed),
                raw_text=trimmed,
                confidence=0.74,
                confirmed_by_user=confirmed_by_user,
            ),
        )
        return EvidenceDocumentUploadResponse(
            evidence=evidence,
            filename=filename,
            content_type=content_type,
            extracted_characters=len(trimmed),
            confirmed=confirmed_by_user,
        )

    def document_path(self, value: str | None) -> Path | None:
        if not value or not re.fullmatch(r"upload://[a-f0-9]{64}\.[a-z0-9]{1,8}", value):
            return None
        return self.upload_dir / value.removeprefix("upload://")

    def _check_file_size(self, content: bytes) -> None:
        if len(content) > self.max_file_bytes:
            raise AppError("DOCUMENT_TOO_LARGE", "文件不能超过 10 MB。", 413)

    def _extract_text(self, filename: str, content_type: str | None, content: bytes) -> str:
        suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if suffix == "pdf" or content_type == "application/pdf":
            return self._extract_pdf(content)
        if suffix == "docx" or content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return self._extract_docx(content)
        if suffix in {"json", "jsonl"} or content_type == "application/json":
            return self._extract_json(content)
        if suffix in {"html", "htm"} or content_type == "text/html":
            return self._strip_html(self._decode_text(content))
        if suffix == "csv" or content_type in {"text/csv", "application/vnd.ms-excel"}:
            return self._extract_csv(content)
        try:
            return self._decode_text(content)
        except AppError:
            return self._extract_printable_strings(content)

    def extract_candidate_drafts(
        self, *, filename: str, content_type: str | None, content: bytes
    ) -> DocumentCandidateExtractionResponse:
        self._check_file_size(content)
        text = self._extract_text(filename, content_type, content)
        trimmed = " ".join(text.split())[: self.max_text_chars]
        if not trimmed:
            raise AppError(
                code="DOCUMENT_TEXT_EMPTY",
                message="Uploaded document did not contain readable text.",
                status_code=422,
            )
        candidates = self._candidate_drafts_from_text(trimmed)
        return DocumentCandidateExtractionResponse(
            filename=filename,
            content_type=content_type,
            extracted_characters=len(trimmed),
            candidate_count=len(candidates),
            candidates=candidates,
        )

    def _extract_pdf(self, content: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise AppError(
                code="DOCUMENT_PARSE_FAILED",
                message="Could not parse uploaded PDF document.",
                status_code=422,
                details={"error": str(exc)},
            ) from exc

    def _extract_docx(self, content: bytes) -> str:
        try:
            document = Document(BytesIO(content))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)
        except Exception as exc:
            raise AppError(
                code="DOCUMENT_PARSE_FAILED",
                message="Could not parse uploaded Word document.",
                status_code=422,
                details={"error": str(exc)},
            ) from exc

    def _extract_json(self, content: bytes) -> str:
        decoded = self._decode_text(content)
        try:
            data = json.loads(decoded)
        except json.JSONDecodeError:
            return decoded
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _extract_csv(self, content: bytes) -> str:
        decoded = self._decode_text(content)
        try:
            reader = csv.DictReader(StringIO(decoded))
            if reader.fieldnames:
                rows = []
                for index, row in enumerate(reader):
                    if index >= 20:
                        break
                    rows.append("; ".join(f"{key}: {value}" for key, value in row.items()))
                return "\n".join(rows) or decoded
            return decoded
        except csv.Error:
            return decoded

    def _decode_text(self, content: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise AppError(
            code="DOCUMENT_DECODE_FAILED",
            message="Uploaded document encoding is not supported.",
            status_code=422,
        )

    def _strip_html(self, text: str) -> str:
        text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
        return re.sub(r"<[^>]+>", " ", text)

    def _extract_printable_strings(self, content: bytes) -> str:
        text = "".join(chr(byte) if 32 <= byte <= 126 else " " for byte in content)
        return " ".join(part for part in text.split() if len(part) > 2)

    def _summary(self, text: str) -> str:
        if len(text) <= 520:
            return f"用户上传文档提取摘要：{text}"
        return f"用户上传文档提取摘要：{text[:520]}..."

    def _candidate_drafts_from_text(self, text: str) -> list[ExtractedCandidateDraft]:
        lines = [line.strip(" -\t") for line in re.split(r"[\n\r]+|(?<=\.)\s+", text) if line.strip()]
        drafts: list[ExtractedCandidateDraft] = []
        seen: set[str] = set()
        for line in lines:
            draft = self._draft_from_line(line)
            if draft is None:
                continue
            key = "|".join(
                [
                    (draft.name or "").lower(),
                    (draft.company_name or "").lower(),
                    (draft.title or "").lower(),
                ]
            )
            if key in seen:
                continue
            seen.add(key)
            drafts.append(draft)
            if len(drafts) >= 30:
                break
        if drafts:
            return drafts
        return [
            ExtractedCandidateDraft(
                profile_summary=f"Document-level candidate signal extracted from {text[:720]}",
                confidence=0.38,
                source_excerpt=text[:720],
            )
        ]

    def _draft_from_line(self, line: str) -> ExtractedCandidateDraft | None:
        if len(line) < 12:
            return None
        patterns = [
            re.compile(
                r"(?P<name>[A-Z][A-Za-z.\-]+(?:\s+[A-Z][A-Za-z.\-]+){1,2})\s*[,-]\s*(?P<title>[^,@|]{3,80}?)\s+(?:at|@)\s+(?P<company>[A-Za-z0-9 .&+-]{2,80})(?:,|;|\.|$)",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?P<name>[A-Z][A-Za-z.\-]+(?:\s+[A-Z][A-Za-z.\-]+){1,2})\s*[,-]\s*(?P<title>[^,@|]{3,80})\s*(?:at|@|,)\s*(?P<company>[A-Za-z0-9 .&+-]{2,80})",
                re.IGNORECASE,
            ),
            re.compile(
                r"name[:：]\s*(?P<name>[^,;|]+).*?(?:company|公司)[:：]\s*(?P<company>[^,;|]+).*?(?:title|岗位|职位)[:：]\s*(?P<title>[^,;|]+)",
                re.IGNORECASE,
            ),
        ]
        name = company = title = None
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                name = match.groupdict().get("name", "").strip()
                company = match.groupdict().get("company", "").strip()
                title = match.groupdict().get("title", "").strip()
                break
        if not any([name, company, title]):
            keywords = [
                "research",
                "engineer",
                "scientist",
                "infra",
                "agent",
                "llm",
                "算法",
                "工程师",
                "研究员",
                "候选人",
            ]
            if not any(keyword.lower() in line.lower() for keyword in keywords):
                return None
        domain = self._infer_domain(line)
        location = self._infer_location(line)
        return ExtractedCandidateDraft(
            name=name,
            company_name=company,
            title=title,
            department=self._infer_department(line),
            location=location,
            domain=domain,
            profile_summary=f"从上传文档自动识别的人才线索：{line[:520]}",
            confidence=0.72 if name and company and title else 0.48,
            source_excerpt=line[:720],
        )

    def _infer_domain(self, text: str) -> str | None:
        mapping = {
            "agent": "AI Agents",
            "llm": "LLM",
            "inference": "Inference Infrastructure",
            "gpu": "GPU Optimization",
            "eval": "Model Evaluation",
            "alignment": "AI Alignment",
            "算法": "AI Algorithms",
            "推理": "Inference Infrastructure",
        }
        lower = text.lower()
        for key, value in mapping.items():
            if key in lower:
                return value
        return None

    def _infer_department(self, text: str) -> str | None:
        for value in ["Research", "Infra", "Agents", "Evaluation", "Alignment", "Data"]:
            if value.lower() in text.lower():
                return value
        return None

    def _infer_location(self, text: str) -> str | None:
        for value in ["San Francisco", "Seattle", "London", "Beijing", "Shanghai", "Singapore", "Tokyo"]:
            if value.lower() in text.lower():
                return value
        return None
