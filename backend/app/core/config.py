"""Application configuration.

Reads settings from environment variables (and an optional `.env` file at the
repository root). Never hard-code credentials anywhere else in the codebase.

Why a settings object instead of reading os.environ directly?
    * One place to see every setting the app understands.
    * Values are typed and validated at startup, so a typo fails loudly and early.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings, loaded from the environment / `.env`."""

    model_config = SettingsConfigDict(
        # Look for `.env` in the repository root (two levels above this file).
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- General ----
    app_name: str = "ElderLife AI"
    environment: str = "development"  # "development" | "test" | "production"

    # ---- Database ----
    # Default targets the Docker Compose service defined in docker-compose.yml.
    # Override with the DATABASE_URL variable in your local `.env`.
    database_url: str = (
        "postgresql+psycopg://elderlife_dev:change_me_local_only@localhost:5432/elderlife"
    )

    # ---- Backend ----
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    allowed_origins: str = "http://localhost:5173"

    @property
    def is_production(self) -> bool:
        """True when running in production — used to block destructive scripts."""
        return self.environment.strip().lower() == "production"

    @property
    def is_test(self) -> bool:
        """True when running the automated test suite."""
        return self.environment.strip().lower() == "test"


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings object (created once per process)."""
    return Settings()
