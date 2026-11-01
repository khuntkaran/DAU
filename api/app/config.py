"""Settings from the environment. Each variable here is also listed in `.env.example`."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./suryasetu.db"
    upload_dir: Path = Path("./uploads")
    web_origins: str = "http://localhost:3000"
    jwt_secret: str = ""
    jwt_ttl_s: int = 12 * 60 * 60
    # With no SMS provider yet, every login code is this value. Leave empty in production.
    demo_otp: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.web_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
