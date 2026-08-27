import httpx
import pytest

from app.services.jellyfin import JellyfinService


def _service(handler, base_url="http://jf", api_key="key"):
    service = JellyfinService(base_url, api_key)
    service._client = httpx.Client(
        base_url=service.base_url,
        headers={"X-Emby-Token": api_key, "Accept": "application/json"},
        transport=httpx.MockTransport(handler),
    )
    return service


def test_init_strips_trailing_slash():
    service = JellyfinService("http://jf/", "key")
    assert service.base_url == "http://jf"


def test_get_returns_json():
    def handler(_request):
        return httpx.Response(200, json={"ok": True})

    service = _service(handler)
    assert service._get("/anything") == {"ok": True}


def test_get_raises_and_logs_http_status_error():
    def handler(_request):
        return httpx.Response(404, json={"error": "nope"})

    service = _service(handler)
    with pytest.raises(httpx.HTTPStatusError):
        service._get("/missing")


def test_get_raises_and_logs_request_error():
    def handler(_request):
        raise httpx.ConnectError("connection refused")

    service = _service(handler)
    with pytest.raises(httpx.RequestError):
        service._get("/anything")


def test_ensure_user_id_caches_first_user():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json=[{"Id": "u1"}, {"Id": "u2"}])

    service = _service(handler)
    assert service._ensure_user_id() == "u1"
    assert service._ensure_user_id() == "u1"
    assert calls == ["/Users"]  # only fetched once, then cached


def test_ensure_user_id_raises_when_no_users():
    def handler(_request):
        return httpx.Response(200, json=[])

    service = _service(handler)
    with pytest.raises(RuntimeError, match="No Jellyfin users found"):
        service._ensure_user_id()


def test_get_music_libraries_filters_music_collections():
    def handler(request):
        if request.url.path == "/Users":
            return httpx.Response(200, json=[{"Id": "u1"}])
        return httpx.Response(
            200,
            json={
                "Items": [
                    {"Id": "1", "Name": "Music", "CollectionType": "music"},
                    {"Id": "2", "Name": "Movies", "CollectionType": "movies"},
                ]
            },
        )

    service = _service(handler)
    libs = service.get_music_libraries()
    assert [lib.name for lib in libs] == ["Music"]


def test_iter_audio_items_paginates_until_total_reached():
    # iter_audio_items fetches a fixed page size of 200 and keeps going while
    # StartIndex hasn't yet reached TotalRecordCount, so a second page is
    # only fetched once there are more than 200 items on the server.
    first_page = [{"Id": str(i)} for i in range(200)]
    second_page = [{"Id": "200"}, {"Id": "201"}]
    total = len(first_page) + len(second_page)

    def handler(request):
        if request.url.path == "/Users":
            return httpx.Response(200, json=[{"Id": "u1"}])
        start = int(request.url.params.get("StartIndex", "0"))
        items = first_page if start == 0 else second_page
        return httpx.Response(200, json={"Items": items, "TotalRecordCount": total})

    service = _service(handler)
    items = list(service.iter_audio_items())
    assert [i["Id"] for i in items] == [str(i) for i in range(total)]


def test_iter_audio_items_stops_on_empty_page():
    def handler(request):
        if request.url.path == "/Users":
            return httpx.Response(200, json=[{"Id": "u1"}])
        return httpx.Response(200, json={"Items": [], "TotalRecordCount": 0})

    service = _service(handler)
    assert list(service.iter_audio_items()) == []


def test_iter_audio_items_scopes_to_library_id():
    seen_params = []

    def handler(request):
        if request.url.path == "/Users":
            return httpx.Response(200, json=[{"Id": "u1"}])
        seen_params.append(dict(request.url.params))
        return httpx.Response(200, json={"Items": [], "TotalRecordCount": 0})

    service = _service(handler)
    list(service.iter_audio_items(library_id="lib-1"))
    assert seen_params[0]["ParentId"] == "lib-1"


def test_extract_loudness_prefers_explicit_normalization_gain():
    service = _service(lambda _request: httpx.Response(200, json={}))
    loudness = service._extract_loudness(
        {"NormalizationGain": -6.0, "AlbumNormalizationGain": -7.0, "LUFS": -14.0}
    )
    assert loudness.track_gain_db == -6.0
    assert loudness.album_gain_db == -7.0
    assert loudness.loudness_lufs == -14.0


def test_extract_loudness_falls_back_to_lufs():
    service = _service(lambda _request: httpx.Response(200, json={}))
    loudness = service._extract_loudness({"LUFS": -20.0})
    assert loudness.track_gain_db == 2.0  # -18.0 - (-20.0)


def test_extract_loudness_returns_none_when_nothing_available():
    service = _service(lambda _request: httpx.Response(200, json={}))
    assert service._extract_loudness({}) is None


def test_get_track_info_uses_first_artist():
    service = _service(lambda _request: httpx.Response(200, json={}))
    info = service.get_track_info(
        {
            "Id": "1",
            "Name": "Song",
            "Artists": ["Band"],
            "Album": "LP",
            "Path": "/a.flac",
        }
    )
    assert info.artist == "Band"
    assert info.album == "LP"


def test_get_track_info_falls_back_to_album_artist():
    service = _service(lambda _request: httpx.Response(200, json={}))
    info = service.get_track_info({"Id": "1", "Name": "Song", "AlbumArtist": "Solo"})
    assert info.artist == "Solo"


def test_test_connection_returns_server_info():
    def handler(_request):
        return httpx.Response(200, json={"ServerName": "Home", "Version": "10.9.0"})

    service = _service(handler)
    result = service.test_connection()
    assert result == {"ok": True, "server_name": "Home", "version": "10.9.0"}


def test_close_closes_underlying_client():
    service = _service(lambda _request: httpx.Response(200, json={}))
    service.close()
    assert service._client.is_closed
