from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import httpx

from app.schemas.gain import LibraryInfo, LoudnessInfo, TrackInfo

logger = logging.getLogger(__name__)


class JellyfinService:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._user_id: str | None = None
        logger.info("jellyfin: connecting to %s", self.base_url)
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "X-Emby-Token": api_key,
                "Accept": "application/json",
            },
            timeout=60.0,
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            r = self._client.get(path, params=params or {})
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.warning(
                "jellyfin: request failed: GET %s%s -> %d",
                self.base_url,
                path,
                e.response.status_code,
            )
            raise
        except httpx.RequestError as e:
            logger.warning(
                "jellyfin: request failed: GET %s%s -> %s", self.base_url, path, e
            )
            raise
        return r.json()

    def _ensure_user_id(self) -> str:
        if self._user_id is None:
            # Prefer the first admin / first user
            users = self._get("/Users")
            if not users:
                raise RuntimeError("No Jellyfin users found")
            self._user_id = users[0]["Id"]
        return self._user_id

    def get_music_libraries(self) -> list[LibraryInfo]:
        uid = self._ensure_user_id()
        views = self._get(f"/Users/{uid}/Views")
        libs = []
        for item in views.get("Items", []):
            # CollectionType can be "music"
            if item.get("CollectionType") == "music":
                libs.append(LibraryInfo(id=item["Id"], name=item["Name"]))
        return libs

    def iter_audio_items(
        self, library_id: str | None = None
    ) -> Iterator[dict[str, Any]]:
        uid = self._ensure_user_id()
        start = 0
        limit = 200
        while True:
            params = {
                "IncludeItemTypes": "Audio",
                "Recursive": "true",
                "Fields": "Path,MediaSources,NormalizationGain,LUFS,AlbumNormalizationGain",
                "StartIndex": start,
                "Limit": limit,
            }
            if library_id:
                params["ParentId"] = library_id
            data = self._get(f"/Users/{uid}/Items", params=params)
            items = data.get("Items", [])
            if not items:
                break
            yield from items
            start += limit
            if start >= data.get("TotalRecordCount", 0):
                break

    def _extract_loudness(self, item: dict[str, Any]) -> LoudnessInfo | None:
        # Prefer explicit NormalizationGain (already in dB relative to -18 LUFS)
        track_gain = item.get("NormalizationGain")
        album_gain = item.get("AlbumNormalizationGain")

        # Fallback: derive from LUFS if present
        lufs = item.get("LUFS")
        if track_gain is None and lufs is not None:
            track_gain = -18.0 - float(lufs)

        if track_gain is None and album_gain is None:
            return None

        return LoudnessInfo(
            track_gain_db=float(track_gain) if track_gain is not None else None,
            album_gain_db=float(album_gain) if album_gain is not None else None,
            loudness_lufs=float(lufs) if lufs is not None else None,
            # Jellyfin does not currently expose peak in the same way
            track_peak=None,
            album_peak=None,
        )

    def get_track_info(self, item: dict[str, Any]) -> TrackInfo:
        artists = item.get("Artists") or []
        return TrackInfo(
            id=item["Id"],
            title=item.get("Name") or "",
            artist=artists[0] if artists else item.get("AlbumArtist"),
            album=item.get("Album"),
            path=item.get("Path"),
            loudness=self._extract_loudness(item),
        )

    def test_connection(self) -> dict[str, Any]:
        info = self._get("/System/Info/Public")
        logger.info(
            "jellyfin: connection test succeeded for %s (server=%s, version=%s)",
            self.base_url,
            info.get("ServerName"),
            info.get("Version"),
        )
        return {
            "ok": True,
            "server_name": info.get("ServerName"),
            "version": info.get("Version"),
        }

    def close(self) -> None:
        self._client.close()
