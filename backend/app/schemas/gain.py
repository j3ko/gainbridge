from pydantic import BaseModel, Field


class LoudnessInfo(BaseModel):
    """Normalized loudness data"""

    track_gain_db: float | None = None
    track_peak: float | None = None
    album_gain_db: float | None = None
    album_peak: float | None = None
    loudness_lufs: float | None = None
    lra: float | None = None


class TrackInfo(BaseModel):
    id: str
    title: str
    artist: str | None = None
    album: str | None = None
    path: str | None = None
    loudness: LoudnessInfo | None = None
    has_existing_rg_tags: bool = False


class LibraryInfo(BaseModel):
    id: str
    name: str
    type: str = "music"


class WriteResult(BaseModel):
    path: str
    success: bool
    message: str = ""
    tags_written: dict[str, str] = Field(default_factory=dict)
