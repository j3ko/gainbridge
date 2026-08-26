from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from plexapi.audio import Track
from plexapi.server import PlexServer

from app.schemas.gain import LibraryInfo, LoudnessInfo, TrackInfo

logger = logging.getLogger(__name__)

# Plex stores gain relative to its own reference (~-18 LUFS ReplayGain 2.0 style).
# The `gain` / `albumGain` fields on the audio stream are already in dB.


class PlexService:
    def __init__(self, base_url: str, token: str):
        logger.info("plex: connecting to %s", base_url)
        try:
            # plexapi declares py.typed but PlexServer.__init__ itself has no
            # parameter annotations, so mypy strict can't type-check this call.
            self.server = PlexServer(base_url, token)  # type: ignore[no-untyped-call]
        except Exception as e:
            logger.warning("plex: connection failed for %s: %s", base_url, e)
            raise
        logger.info(
            "plex: connected to %s (server=%s)", base_url, self.server.friendlyName
        )

    def get_music_libraries(self) -> list[LibraryInfo]:
        libs = []
        for section in self.server.library.sections():
            if section.type == "artist":  # music library
                libs.append(LibraryInfo(id=str(section.key), name=section.title))
        return libs

    def iter_tracks(self, library_id: str | None = None) -> Iterator[Track]:
        """Yield all tracks, optionally limited to one library."""
        sections = self.server.library.sections()
        for section in sections:
            if section.type != "artist":
                continue
            if library_id and str(section.key) != str(library_id):
                continue
            # section.all() returns tracks when called on music lib with type filter
            yield from section.search(libtype="track")

    def _extract_loudness(self, track: Track) -> LoudnessInfo | None:
        try:
            media_list = getattr(track, "media", None) or []
            if not media_list:
                return None

            media = media_list[0]
            parts = getattr(media, "parts", None) or []
            if not parts:
                return None

            part = parts[0]
            streams = getattr(part, "streams", None) or []
            audio_streams = [s for s in streams if getattr(s, "STREAMTYPE", None) == 2]
            if not audio_streams:
                return None

            stream = audio_streams[0]

            gain = getattr(stream, "gain", None)
            peak = getattr(stream, "peak", None)
            album_gain = getattr(stream, "albumGain", None)
            album_peak = getattr(stream, "albumPeak", None)
            loudness = getattr(stream, "loudness", None)
            lra = getattr(stream, "lra", None)

            if gain is None and loudness is None:
                return None

            return LoudnessInfo(
                track_gain_db=float(gain) if gain is not None else None,
                track_peak=float(peak) if peak is not None else None,
                album_gain_db=float(album_gain) if album_gain is not None else None,
                album_peak=float(album_peak) if album_peak is not None else None,
                loudness_lufs=float(loudness) if loudness is not None else None,
                lra=float(lra) if lra is not None else None,
            )
        except Exception:
            return None

    def _file_path(self, track: Track) -> str | None:
        try:
            media_list = getattr(track, "media", None) or []
            if not media_list:
                return None
            media = media_list[0]
            parts = getattr(media, "parts", None) or []
            if not parts:
                return None
            return getattr(parts[0], "file", None)
        except Exception:
            return None

    def get_track_info(self, track: Track) -> TrackInfo:
        # Tracks from section.search()/iter_tracks() are partial objects: the
        # bulk listing XML omits nested <Stream> elements (streamType, gain,
        # peak, loudness), so track.media[...].parts[...].streams is empty
        # until we reload the full item metadata.
        if track.isPartialObject():  # type: ignore[no-untyped-call]
            track.reload()  # type: ignore[no-untyped-call]

        path = self._file_path(track)
        return TrackInfo(
            id=str(track.ratingKey),
            title=track.title or "",
            artist=getattr(track, "grandparentTitle", None)
            or getattr(track, "originalTitle", None),
            album=getattr(track, "parentTitle", None),
            path=path,
            loudness=self._extract_loudness(track),
        )

    def test_connection(self) -> dict[str, Any]:
        return {
            "ok": True,
            "server_name": self.server.friendlyName,
            "version": self.server.version,
        }
