import pytest

from app.services import plex as plex_module
from app.services.plex import PlexService


class _FakeStream:
    def __init__(
        self,
        STREAMTYPE=2,
        gain=None,
        peak=None,
        albumGain=None,
        albumPeak=None,
        loudness=None,
        lra=None,
    ):
        self.STREAMTYPE = STREAMTYPE
        self.gain = gain
        self.peak = peak
        self.albumGain = albumGain
        self.albumPeak = albumPeak
        self.loudness = loudness
        self.lra = lra


class _FakePart:
    def __init__(self, streams=None, file=None):
        self.streams = streams if streams is not None else []
        self.file = file


class _FakeMedia:
    def __init__(self, parts=None):
        self.parts = parts if parts is not None else []


class _FakeTrack:
    def __init__(
        self,
        media=None,
        ratingKey="1",
        title="Song",
        grandparentTitle=None,
        originalTitle=None,
        parentTitle=None,
        partial=False,
    ):
        self.media = media if media is not None else []
        self.ratingKey = ratingKey
        self.title = title
        self.grandparentTitle = grandparentTitle
        self.originalTitle = originalTitle
        self.parentTitle = parentTitle
        self._partial = partial
        self.reloaded = False

    def isPartialObject(self):
        return self._partial

    def reload(self):
        self.reloaded = True
        self._partial = False


class _ExplodingTrack:
    @property
    def media(self):
        raise RuntimeError("boom")


class _FakeSection:
    def __init__(self, key, title, type_, tracks=None):
        self.key = key
        self.title = title
        self.type = type_
        self._tracks = tracks if tracks is not None else []

    def search(self, libtype=None):
        return self._tracks


class _FakeLibrary:
    def __init__(self, sections):
        self._sections = sections

    def sections(self):
        return self._sections


class _FakeServer:
    def __init__(self, sections=(), friendlyName="My Plex", version="1.0"):
        self.library = _FakeLibrary(list(sections))
        self.friendlyName = friendlyName
        self.version = version


def _service(monkeypatch, server: _FakeServer):
    monkeypatch.setattr(plex_module, "PlexServer", lambda base_url, token: server)
    return PlexService("http://x", "t")


def test_init_connects(monkeypatch):
    service = _service(monkeypatch, _FakeServer())
    assert service.server.friendlyName == "My Plex"


def test_init_failure_propagates(monkeypatch):
    def raiser(_base_url, _token):
        raise RuntimeError("unreachable")

    monkeypatch.setattr(plex_module, "PlexServer", raiser)
    with pytest.raises(RuntimeError):
        PlexService("http://x", "t")


def test_get_music_libraries_filters_to_artist_sections(monkeypatch):
    sections = [
        _FakeSection("1", "Music", "artist"),
        _FakeSection("2", "Movies", "movie"),
    ]
    service = _service(monkeypatch, _FakeServer(sections))
    libs = service.get_music_libraries()
    assert [lib.name for lib in libs] == ["Music"]


def test_iter_tracks_skips_non_artist_sections(monkeypatch):
    t1 = _FakeTrack(ratingKey="1")
    sections = [_FakeSection("1", "Movies", "movie", tracks=[t1])]
    service = _service(monkeypatch, _FakeServer(sections))
    assert list(service.iter_tracks()) == []


def test_iter_tracks_filters_by_library_id(monkeypatch):
    t1 = _FakeTrack(ratingKey="1")
    t2 = _FakeTrack(ratingKey="2")
    sections = [
        _FakeSection("1", "Music", "artist", tracks=[t1]),
        _FakeSection("2", "Other Music", "artist", tracks=[t2]),
    ]
    service = _service(monkeypatch, _FakeServer(sections))
    assert list(service.iter_tracks(library_id="2")) == [t2]


def test_iter_tracks_no_library_id_yields_all_artist_sections(monkeypatch):
    t1 = _FakeTrack(ratingKey="1")
    t2 = _FakeTrack(ratingKey="2")
    sections = [
        _FakeSection("1", "Music", "artist", tracks=[t1]),
        _FakeSection("2", "Other Music", "artist", tracks=[t2]),
    ]
    service = _service(monkeypatch, _FakeServer(sections))
    assert list(service.iter_tracks()) == [t1, t2]


def test_extract_loudness_no_media_returns_none(monkeypatch):
    service = _service(monkeypatch, _FakeServer())
    assert service._extract_loudness(_FakeTrack(media=[])) is None


def test_extract_loudness_no_parts_returns_none(monkeypatch):
    service = _service(monkeypatch, _FakeServer())
    track = _FakeTrack(media=[_FakeMedia(parts=[])])
    assert service._extract_loudness(track) is None


def test_extract_loudness_no_streams_returns_none(monkeypatch):
    service = _service(monkeypatch, _FakeServer())
    track = _FakeTrack(media=[_FakeMedia(parts=[_FakePart(streams=[])])])
    assert service._extract_loudness(track) is None


def test_extract_loudness_no_audio_streams_returns_none(monkeypatch):
    service = _service(monkeypatch, _FakeServer())
    non_audio = _FakeStream(STREAMTYPE=1)
    track = _FakeTrack(media=[_FakeMedia(parts=[_FakePart(streams=[non_audio])])])
    assert service._extract_loudness(track) is None


def test_extract_loudness_gain_and_loudness_both_missing_returns_none(monkeypatch):
    service = _service(monkeypatch, _FakeServer())
    stream = _FakeStream(gain=None, loudness=None)
    track = _FakeTrack(media=[_FakeMedia(parts=[_FakePart(streams=[stream])])])
    assert service._extract_loudness(track) is None


def test_extract_loudness_full_values(monkeypatch):
    service = _service(monkeypatch, _FakeServer())
    stream = _FakeStream(
        gain="-6.0",
        peak="0.9",
        albumGain="-7.0",
        albumPeak="0.95",
        loudness="-14",
        lra="5",
    )
    track = _FakeTrack(media=[_FakeMedia(parts=[_FakePart(streams=[stream])])])
    loudness = service._extract_loudness(track)
    assert loudness is not None
    assert loudness.track_gain_db == -6.0
    assert loudness.album_gain_db == -7.0
    assert loudness.loudness_lufs == -14.0
    assert loudness.lra == 5.0


def test_extract_loudness_swallows_unexpected_errors(monkeypatch):
    service = _service(monkeypatch, _FakeServer())
    assert service._extract_loudness(_ExplodingTrack()) is None


def test_file_path_no_media_returns_none(monkeypatch):
    service = _service(monkeypatch, _FakeServer())
    assert service._file_path(_FakeTrack(media=[])) is None


def test_file_path_no_parts_returns_none(monkeypatch):
    service = _service(monkeypatch, _FakeServer())
    track = _FakeTrack(media=[_FakeMedia(parts=[])])
    assert service._file_path(track) is None


def test_file_path_returns_file(monkeypatch):
    service = _service(monkeypatch, _FakeServer())
    track = _FakeTrack(media=[_FakeMedia(parts=[_FakePart(file="/music/a.flac")])])
    assert service._file_path(track) == "/music/a.flac"


def test_file_path_swallows_unexpected_errors(monkeypatch):
    service = _service(monkeypatch, _FakeServer())
    assert service._file_path(_ExplodingTrack()) is None


def test_get_track_info_reloads_partial_objects(monkeypatch):
    service = _service(monkeypatch, _FakeServer())
    track = _FakeTrack(
        media=[_FakeMedia(parts=[_FakePart(file="/a.flac")])],
        grandparentTitle="Artist",
        parentTitle="Album",
        partial=True,
    )
    info = service.get_track_info(track)
    assert track.reloaded is True
    assert info.artist == "Artist"
    assert info.album == "Album"
    assert info.path == "/a.flac"


def test_get_track_info_falls_back_to_original_title(monkeypatch):
    service = _service(monkeypatch, _FakeServer())
    track = _FakeTrack(grandparentTitle=None, originalTitle="Solo Artist")
    info = service.get_track_info(track)
    assert info.artist == "Solo Artist"


def test_test_connection(monkeypatch):
    service = _service(
        monkeypatch, _FakeServer(friendlyName="Home Server", version="1.2.3")
    )
    result = service.test_connection()
    assert result == {"ok": True, "server_name": "Home Server", "version": "1.2.3"}
