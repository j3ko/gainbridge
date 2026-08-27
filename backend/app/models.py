from datetime import datetime, timezone
from typing import Literal

from pydantic import field_serializer
from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc_isoformat(dt: datetime) -> str:
    """Serialize a datetime as UTC ISO 8601, tagging it with an offset.

    SQLite's DateTime column drops tzinfo on read, so values loaded from the
    DB are naive even though they were written via utcnow(). Without an
    explicit offset, JS's `new Date(...)` on the client parses the string as
    local time instead of UTC, shifting displayed timestamps by the
    browser's UTC offset.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _to_utc_isoformat_optional(dt: datetime | None) -> str | None:
    return None if dt is None else _to_utc_isoformat(dt)


class SourceBase(SQLModel):
    name: str = Field(index=True, unique=True)
    type: str  # "plex" | "jellyfin"
    base_url: str
    token: str
    enabled: bool = True
    # None syncs every music library on the server; set to scope this
    # source to a single library.
    library_id: str | None = None
    # cron schedule; unset means no schedule is active
    schedule_cron: str | None = None


class Source(SourceBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    path_mappings: list["PathMapping"] = Relationship(
        back_populates="source",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class SourceCreate(SourceBase):
    path_mappings: list["PathMappingCreate"] = []


class SourcePublic(SourceBase):
    id: int
    created_at: datetime
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    path_mappings: list["PathMappingPublic"] = []

    @field_serializer("created_at")
    def _serialize_created_at(self, dt: datetime) -> str:
        return _to_utc_isoformat(dt)

    @field_serializer("next_run_at", "last_run_at")
    def _serialize_optional_utc(self, dt: datetime | None) -> str | None:
        return _to_utc_isoformat_optional(dt)


# A single Plex/Jellyfin library can span multiple folders on disk (e.g. a
# Music library made up of both /data/music1 and /data/music2), each of
# which may need its own remote->local translation, so a source can have
# any number of these (Sonarr/Radarr-style remote path mappings).
class PathMappingBase(SQLModel):
    remote_path: str
    local_path: str


class PathMapping(PathMappingBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="source.id", index=True)
    source: Source = Relationship(back_populates="path_mappings")


class PathMappingCreate(PathMappingBase):
    pass


class PathMappingPublic(PathMappingBase):
    id: int


class ScheduleUpdate(SQLModel):
    schedule_cron: str


class SourceTestRequest(SQLModel):
    type: str
    base_url: str
    token: str


class PlexPinCreate(SQLModel):
    id: str
    oauth_url: str


class PlexPinStatus(SQLModel):
    authenticated: bool
    token: str | None = None


class PlexServerConnection(SQLModel):
    uri: str
    local: bool


class PlexServerOption(SQLModel):
    name: str
    connections: list[PlexServerConnection]


class JobBase(SQLModel):
    source_name: str = Field(index=True)
    library_id: str | None = None
    dry_run: bool = True
    write_mode: str = "fix"  # skip|fix|overwrite
    status: str = Field(
        default="pending", index=True
    )  # pending|running|completed|failed|cancelled
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
    write_mode: Literal["skip", "fix", "overwrite"] = "fix"


class JobPublic(JobBase):
    id: str
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def _serialize_utc(self, dt: datetime) -> str:
        return _to_utc_isoformat(dt)


class JobsPublic(SQLModel):
    data: list[JobPublic]
    count: int


class JobLog(SQLModel):
    log: str
