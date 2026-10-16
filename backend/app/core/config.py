import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "TalentNet API"
    app_version: str = "0.1.0"
    database_url: str = "sqlite:///./talentnet.db"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "http://localhost:3002",
            "http://127.0.0.1:3002",
            "http://localhost:3003",
            "http://127.0.0.1:3003",
            "http://localhost:3004",
            "http://127.0.0.1:3004",
            "http://localhost:3005",
            "http://127.0.0.1:3005",
        ]
    )
    cors_origin_regex: str = r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+):\d+"
    llm_provider: str = "openai"
    llm_model: str = "gpt-5.4-mini"
    llm_api_key: str | None = None
    llm_base_url: str = "https://cnapi.maolaoapi.com/v1"
    llm_timeout_seconds: float = 20
    llm_max_tokens: int = 4096
    llm_retry_count: int = 2
    browser_headless: bool = False
    browser_user_data_dir: str = str(ROOT_DIR / ".talentnet-browser-profile")
    browser_executable: str | None = None
    browser_cdp_url: str | None = "http://127.0.0.1:9222"

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"),
        env_prefix="TALENTNET_",
    )

    def model_post_init(self, __context: object) -> None:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.llm_api_key and openai_api_key:
            self.llm_api_key = openai_api_key
        if self.llm_provider == "local" and openai_api_key:
            self.llm_provider = "openai"
        if self.llm_provider == "openai" and self.llm_model == "local-structured-v1":
            self.llm_model = "gpt-4.1-mini"


settings = Settings()
