from app.schemas.source_connection import SourceConnectionRead
from app.core.database import SessionLocal
from app.models.workspace import SourceState


class SourceConnectionService:
    providers = {
        "public_web": ("公开网页", "available", "public", False, "不需要绑定账号，使用公开搜索页面。"),
        "linkedin": ("LinkedIn", "needs_login", "user_authorized", True, "用户自行登录后，AI 只读取用户可见页面。"),
        "maimai": ("脉脉", "needs_login", "user_authorized", True, "用户自行登录后，AI 只读取用户可见页面。"),
        "arxiv": ("arXiv", "available", "public", False, "公开页面和公开 API，适合作为稳定证据源。"),
        "patent": ("专利", "available", "public", False, "公开专利检索源。"),
        "job_site": ("招聘网站", "available", "public", False, "使用公开搜索或手动确认样例。"),
        "company_site": ("公司官网", "available", "public", False, "公开公司页面、公告和团队页面。"),
    }

    def list_connections(self) -> list[SourceConnectionRead]:
        return [
            self._read(provider)
            for provider in [
                "public_web",
                "linkedin",
                "maimai",
                "arxiv",
                "patent",
                "job_site",
                "company_site",
            ]
        ]

    def update_status(self, provider: str, status: str) -> SourceConnectionRead:
        if provider not in self.providers:
            raise KeyError(provider)
        with SessionLocal() as db:
            state = db.get(SourceState, provider)
            if state is None:
                db.add(SourceState(provider=provider, status=status))
            else:
                state.status = status
            db.commit()
        return self._read(provider)

    def connected_private_sources(self) -> list[str]:
        return [
            item.provider
            for item in self.list_connections()
            if item.requires_user_login and item.status == "connected"
        ]

    def _read(self, provider: str) -> SourceConnectionRead:
        label, default_status, mode, requires_login, notes = self.providers[provider]
        with SessionLocal() as db:
            state = db.get(SourceState, provider)
            status = state.status if state else default_status
        return SourceConnectionRead(
            provider=provider,
            label=label,
            status=status,
            mode=mode,
            requires_user_login=requires_login,
            notes=notes,
        )
