import os
from pathlib import Path
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AnyUrl,
    BeforeValidator,
    Field,
    HttpUrl,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


def _detect_timezone() -> str:
    """Best-effort IANA zone for a TIMEZONE that wasn't explicitly set.

    Checks, in order: the standard TZ env var, Debian-style /etc/timezone
    (what the README's docker run bind-mounts from the host), and the
    /etc/localtime symlink target - falling back to UTC if none resolve.
    """
    if tz := os.environ.get("TZ"):
        return tz
    try:
        return Path("/etc/timezone").read_text().strip()
    except OSError:
        pass
    try:
        return str(Path("/etc/localtime").resolve().relative_to("/usr/share/zoneinfo"))
    except (OSError, ValueError):
        pass
    return "UTC"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    FRONTEND_HOST: str = "http://localhost:9220"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    PROJECT_NAME: str = "Gainbridge"
    SENTRY_DSN: HttpUrl | None = None
    # Relative to backend/ (where the app runs from, in Docker and locally),
    # so this lands in a top-level data/ folder next to backend/ and
    # frontend/ - not inside backend/ itself.
    SQLITE_DB_FILE: str = "../data/gainbridge.db"
    LOG_FILE: str = "../data/gainbridge.log"
    # How long to keep finished (completed/failed/cancelled) job rows before
    # a scheduler tick prunes them, so a long-running cron doesn't grow the
    # jobs table forever.
    JOB_RETENTION_DAYS: int = 30
    # Size threshold at which the log file gets rotated (renamed to .1, .2,
    # ...), and how many rotated backups to keep around.
    LOG_MAX_BYTES: int = 10 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 5
    # IANA zone name (e.g. "America/Toronto") that source schedule_cron
    # expressions are evaluated in. Everything is still stored/served as
    # UTC; this only controls what wall-clock time a cron's fields mean.
    # Auto-detected from the container's system timezone (or TZ) when unset
    # - see _detect_timezone - so set this only to override that.
    TIMEZONE: str = Field(default_factory=_detect_timezone)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"sqlite:///{self.SQLITE_DB_FILE}"

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.TIMEZONE)

    @model_validator(mode="after")
    def _validate_timezone(self) -> Self:
        try:
            ZoneInfo(self.TIMEZONE)
        except ZoneInfoNotFoundError as e:
            raise ValueError(f"Unknown TIMEZONE: {self.TIMEZONE!r}") from e
        return self

    @model_validator(mode="after")
    def _ensure_data_dirs(self) -> Self:
        Path(self.SQLITE_DB_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(self.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
        return self


settings = Settings()
