from __future__ import annotations

from pathlib import Path

from mutagen import File as MutagenFile
from mutagen.flac import FLAC
from mutagen.id3 import ID3, TXXX, ID3NoHeaderError
from mutagen.oggvorbis import OggVorbis

from app.schemas.gain import LoudnessInfo, WriteResult


class TaggerService:
    """Write standard ReplayGain tags into audio files."""

    # mutagen declares py.typed but its format classes (FLAC, OggVorbis, ID3,
    # TXXX) and ID3.delall/add have no parameter annotations, so mypy strict
    # can't type-check these calls; the `# type: ignore[no-untyped-call]`
    # comments below are for those, not a project-wide typing gap.

    # Below this, an existing REPLAYGAIN_TRACK_GAIN tag is considered
    # up to date rather than stale/mismatched.
    GAIN_TOLERANCE_DB = 0.1

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

    def _gain_matches(self, existing: dict[str, str], loudness: LoudnessInfo) -> bool:
        """Return True if an existing REPLAYGAIN_TRACK_GAIN tag is already
        within tolerance of the freshly computed value."""
        if loudness.track_gain_db is None:
            return False
        raw = existing.get("REPLAYGAIN_TRACK_GAIN")
        if not raw:
            return False
        try:
            existing_db = float(raw.split()[0])
        except (ValueError, IndexError):
            return False
        return abs(existing_db - loudness.track_gain_db) <= self.GAIN_TOLERANCE_DB

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

        if not overwrite:
            existing = self.read_existing_rg(path)
            if any("GAIN" in k for k in existing):
                if loudness.track_gain_db is None:
                    return WriteResult(
                        path=path,
                        success=True,
                        message="Skipped – existing ReplayGain tags",
                    )
                if self._gain_matches(existing, loudness):
                    return WriteResult(
                        path=path,
                        success=True,
                        message="Skipped – existing ReplayGain tags already match",
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
        audio = FLAC(path)  # type: ignore[no-untyped-call]
        for k, v in tags.items():
            audio[k] = v
        audio.save()

    def _write_ogg(self, path: str, tags: dict[str, str]) -> None:
        audio = OggVorbis(path)  # type: ignore[no-untyped-call]
        for k, v in tags.items():
            audio[k] = v
        audio.save()

    def _write_mp3(self, path: str, tags: dict[str, str]) -> None:
        try:
            audio = ID3(path)  # type: ignore[no-untyped-call]
        except ID3NoHeaderError:
            audio = ID3()  # type: ignore[no-untyped-call]
        for k, v in tags.items():
            # Remove existing then add
            audio.delall(f"TXXX:{k}")  # type: ignore[no-untyped-call]
            audio.add(TXXX(encoding=3, desc=k, text=v))  # type: ignore[no-untyped-call]
        audio.save(path)

    def _write_generic(self, path: str, tags: dict[str, str]) -> None:
        audio = MutagenFile(path, easy=True)
        if audio is None:
            raise ValueError(f"Unsupported format: {path}")
        for k, v in tags.items():
            audio[k.lower()] = v
        audio.save()
