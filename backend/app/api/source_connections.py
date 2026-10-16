from fastapi import APIRouter

from app.core.errors import AppError
from app.schemas.source_connection import SourceConnectionRead, SourceConnectionUpdate
from app.services.source_connections import SourceConnectionService

router = APIRouter(prefix="/source-connections", tags=["source-connections"])
service = SourceConnectionService()


@router.get("", response_model=list[SourceConnectionRead])
def list_source_connections() -> list[SourceConnectionRead]:
    return service.list_connections()


@router.patch("/{provider}", response_model=SourceConnectionRead)
def update_source_connection(
    provider: str, payload: SourceConnectionUpdate
) -> SourceConnectionRead:
    if payload.status not in {"available", "needs_login", "connected", "paused"}:
        raise AppError(
            code="SOURCE_STATUS_INVALID",
            message="Unsupported source connection status.",
            status_code=422,
        )
    try:
        return service.update_status(provider, payload.status)
    except KeyError as exc:
        raise AppError(
            code="SOURCE_NOT_FOUND",
            message="Source provider does not exist.",
            status_code=404,
        ) from exc
