from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class SourceType(str, Enum):
    plex = "plex"
    jellyfin = "jellyfin"


class LoudnessInfo(BaseModel):
    """Normalized loudness data"""
    track_gain_db: Optional[float] = None
    track_peak: Optional[float] = None
    album_gain_db: Optional[float] = None
    album_peak: Optional[float] = None
    loudness_lufs: Optional[float] = None
    lra: Optional[float] = None


class TrackInfo(BaseModel):
    id: str
    title: str
    artist: Optional[str] = None
    album: Optional[str] = None
    path: Optional[str] = None 
    loudness: Optional[LoudnessInfo] = None
    has_existing_rg_tags: bool = False


class LibraryInfo(BaseModel):
    id: str
    name: str
    type: str = "music"


class SourceConfig(BaseModel):
    type: SourceType
    name: str
    base_url: str
    # Plex token or Jellyfin API key
    token: str
    enabled: bool = True


class WriteResult(BaseModel):
    path: str
    success: bool
    message: str = ""
    tags_written: dict[str, str] = Field(default_factory=dict)


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class JobCreate(BaseModel):
    source_name: str
    library_id: Optional[str] = None
    dry_run: bool = True
    overwrite_existing: bool = False


class JobInfo(BaseModel):
    id: str
    status: JobStatus
    source_name: str
    dry_run: bool
    total: int = 0
    processed: int = 0
    written: int = 0
    skipped: int = 0
    errors: int = 0
    message: str = ""