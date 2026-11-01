"""Settings from the environment. Each variable here is also listed in `.env.example`."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # An empty value in .env, such as `GEMINI_RPM_LIMIT=`, means "not set".
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_parse_none_str="")

    database_url: str = "sqlite:///./suryasetu.db"
    upload_dir: Path = Path("./uploads")
    web_origins: str = "http://localhost:3000"
    jwt_secret: str = ""
    jwt_ttl_s: int = 12 * 60 * 60
    # With no SMS provider yet, every login code is this value. Leave empty in production.
    demo_otp: str | None = None

    # AI. Model names and limits come from each provider's console, never from code.
    ai_provider: Literal["gemini", "groq", "fake"] = "fake"
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    # A lighter model tried when the main one is overloaded; it has its own quota.
    gemini_fallback_model: str | None = None
    gemini_rpm_limit: int | None = None
    groq_api_key: str | None = None
    groq_text_model: str | None = None
    groq_whisper_model: str | None = None
    groq_rpm_limit: int | None = None
    # How long a job waits for a free request slot before trying the next provider.
    llm_max_wait_s: float = 20.0
    # A provider call that takes longer is abandoned and retried by the gateway.
    llm_timeout_s: float = 30.0

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.web_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
