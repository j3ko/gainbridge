from __future__ import annotations

from pathlib import Path
from typing import Optional

from mutagen import File as MutagenFile
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TXXX, ID3NoHeaderError

from app.schemas.gain import LoudnessInfo, WriteResult


class TaggerService:
    """Write standard ReplayGain tags into audio files."""

    def read_existing_rg(self, path: str) -> dict[str, str]:
        audio = MutagenFile(path, easy=False)
        if audio is None:
            return {}
        tags = {}
        # Easy access for Vorbis/FLAC style
        if hasattr(audio, "tags") and audio.tags is not None:
            for key in (
                "REPLAYGAIN_TRACK_GAIN",
                "REPLAYGAIN_TRACK_PEAK",
                "REPLAYGAIN_ALBUM_GAIN",
                "REPLAYGAIN_ALBUM_PEAK",
                "replaygain_track_gain",
                "replaygain_track_peak",
                "replaygain_album_gain",
                "replaygain_album_peak",
            ):
                val = audio.tags.get(key)
                if val:
                    tags[key.upper()] = str(val[0] if isinstance(val, list) else val)
        return tags

    def has_replaygain(self, path: str) -> bool:
        existing = self.read_existing_rg(path)
        return any("GAIN" in k for k in existing)

    def write_replaygain(
        self,
        path: str,
        loudness: LoudnessInfo,
        *,
        overwrite: bool = False,
        dry_run: bool = False,
    ) -> WriteResult:
        p = Path(path)
        if not p.is_file():
            return WriteResult(path=path, success=False, message="File not found")

        if not overwrite and self.has_replaygain(path):
            return WriteResult(
                path=path,
                success=True,
                message="Skipped – existing ReplayGain tags",
            )

        if loudness.track_gain_db is None:
            return WriteResult(
                path=path,
                success=False,
                message="No track gain available",
            )

        tags_to_write = {
            "REPLAYGAIN_TRACK_GAIN": f"{loudness.track_gain_db:.2f} dB",
        }
        if loudness.track_peak is not None:
            tags_to_write["REPLAYGAIN_TRACK_PEAK"] = f"{loudness.track_peak:.6f}"
        if loudness.album_gain_db is not None:
            tags_to_write["REPLAYGAIN_ALBUM_GAIN"] = f"{loudness.album_gain_db:.2f} dB"
        if loudness.album_peak is not None:
            tags_to_write["REPLAYGAIN_ALBUM_PEAK"] = f"{loudness.album_peak:.6f}"

        if dry_run:
            return WriteResult(
                path=path,
                success=True,
                message="Dry run – tags not written",
                tags_written=tags_to_write,
            )

        try:
            suffix = p.suffix.lower()
            if suffix == ".flac":
                self._write_flac(path, tags_to_write)
            elif suffix in {".ogg", ".oga"}:
                self._write_ogg(path, tags_to_write)
            elif suffix == ".mp3":
                self._write_mp3(path, tags_to_write)
            else:
                # Generic fallback via mutagen.File
                self._write_generic(path, tags_to_write)

            return WriteResult(
                path=path,
                success=True,
                message="Tags written",
                tags_written=tags_to_write,
            )
        except Exception as e:
            return WriteResult(path=path, success=False, message=str(e))

    def _write_flac(self, path: str, tags: dict[str, str]) -> None:
        audio = FLAC(path)
        for k, v in tags.items():
            audio[k] = v
        audio.save()

    def _write_ogg(self, path: str, tags: dict[str, str]) -> None:
        audio = OggVorbis(path)
        for k, v in tags.items():
            audio[k] = v
        audio.save()

    def _write_mp3(self, path: str, tags: dict[str, str]) -> None:
        try:
            audio = ID3(path)
        except ID3NoHeaderError:
            audio = ID3()
        for k, v in tags.items():
            # Remove existing then add
            audio.delall(f"TXXX:{k}")
            audio.add(TXXX(encoding=3, desc=k, text=v))
        audio.save(path)

    def _write_generic(self, path: str, tags: dict[str, str]) -> None:
        audio = MutagenFile(path, easy=True)
        if audio is None:
            raise ValueError(f"Unsupported format: {path}")
        for k, v in tags.items():
            audio[k.lower()] = v
        audio.save()