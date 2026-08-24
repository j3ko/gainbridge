from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SourceBase(SQLModel):
    name: str = Field(index=True, unique=True)
    type: str  # "plex" | "jellyfin"
    base_url: str
    token: str
    enabled: bool = True
    # jellyfin optional
    user_id: str | None = None
    # cron schedule
    schedule_cron: str | None = None
    schedule_enabled: bool = False


class Source(SourceBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None


class SourceCreate(SourceBase):
    pass


class SourcePublic(SourceBase):
    id: int
    created_at: datetime
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None


class ScheduleUpdate(SQLModel):
    schedule_cron: str
    schedule_enabled: bool = True

class JobBase(SQLModel):
    source_name: str = Field(index=True)
    library_id: str | None = None
    dry_run: bool = True
    overwrite_existing: bool = False
    status: str = Field(default="pending", index=True)  # pending|running|completed|failed|cancelled
    total: int = 0
    processed: int = 0
    written: int = 0
    skipped: int = 0
    errors: int = 0
    message: str = ""


class Job(JobBase, table=True):
    id: str | None = Field(default=None, primary_key=True)  # uuid string
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class JobCreate(SQLModel):
    source_name: str
    library_id: str | None = None
    dry_run: bool = True
    overwrite_existing: bool = False


class JobPublic(JobBase):
    id: str
    created_at: datetime
    updated_at: datetime
