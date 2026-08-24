from pydantic import BaseModel, Field
from typing import Optional


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


class WriteResult(BaseModel):
    path: str
    success: bool
    message: str = ""
    tags_written: dict[str, str] = Field(default_factory=dict)