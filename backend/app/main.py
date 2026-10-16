from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.api.workspace import router as workspace_router
from app.api.relationships import router as relationships_router
from app.core.identity import current_user_id, resolve_user, seed_users
from app.models.workspace import AuditLog

from app.api.candidates import router as candidates_router
from app.api.browser_tasks import router as browser_tasks_router
from app.api.analytics import router as analytics_router
from app.api.companies import router as companies_router
from app.api.evidence import router as evidence_router
from app.api.feedback import router as feedback_router
from app.api.health import router as health_router
from app.api.llm import router as llm_router
from app.api.llm_eval import router as llm_eval_router
from app.api.llm_memory import router as llm_memory_router
from app.api.manager import router as manager_router
from app.api.org_graph import router as org_graph_router
from app.api.scoring import router as scoring_router
from app.api.source_connections import router as source_connections_router
from app.api.sourcing import router as sourcing_router
from app.api.talent_pool import router as talent_pool_router
from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.core.seed import seed_demo_data


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    with SessionLocal() as db:
        seed_demo_data(db)
        seed_users(db)
    yield


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="TalentNet API",
        version="0.1.0",
        description="Backend API for the TalentNet MVP demo.",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def workspace_context(request: Request, call_next):
        if not request.url.path.startswith("/api") or request.method == "OPTIONS":
            return await call_next(request)
        try:
            with SessionLocal() as db:
                user = resolve_user(db, request.cookies.get("talentnet_session")
                                    if not (request.url.path == "/api/session" and request.method in {"POST", "DELETE"}) else None)
                request.state.user_id, request.state.user_role = user.id, user.role
        except AppError as exc:
            return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message}})
        marker = current_user_id.set(request.state.user_id)
        try:
            response = await call_next(request)
            with SessionLocal() as db:
                db.add(AuditLog(id=f"audit_{uuid4().hex}", user_id=request.state.user_id,
                                method=request.method, path=request.url.path, status_code=response.status_code))
                db.commit()
            return response
        finally:
            current_user_id.reset(marker)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": jsonable_encoder(exc.errors(), custom_encoder={ValueError: str}),
                }
            },
        )

    app.include_router(health_router, prefix="/api")
    app.include_router(browser_tasks_router, prefix="/api")
    app.include_router(analytics_router, prefix="/api")
    app.include_router(companies_router, prefix="/api")
    app.include_router(candidates_router, prefix="/api")
    app.include_router(evidence_router, prefix="/api")
    app.include_router(scoring_router, prefix="/api")
    app.include_router(talent_pool_router, prefix="/api")
    app.include_router(feedback_router, prefix="/api")
    app.include_router(llm_router, prefix="/api")
    app.include_router(llm_memory_router, prefix="/api")
    app.include_router(llm_eval_router, prefix="/api")
    app.include_router(org_graph_router, prefix="/api")
    app.include_router(manager_router, prefix="/api")
    app.include_router(source_connections_router, prefix="/api")
    app.include_router(sourcing_router, prefix="/api")
    app.include_router(workspace_router, prefix="/api")
    app.include_router(relationships_router, prefix="/api")

    return app


app = create_app()
