import pytest
from mutagen.id3 import ID3, TXXX, ID3NoHeaderError
from mutagen.mp4 import MP4FreeForm

from app.schemas.gain import LoudnessInfo
from app.services.tagger import TaggerService


def _tagger(monkeypatch, existing: dict[str, str]):
    tagger = TaggerService()
    monkeypatch.setattr(tagger, "read_existing_rg", lambda path: existing)
    monkeypatch.setattr(tagger, "_write_flac", lambda path, tags: None)
    return tagger


def test_write_replaygain_file_not_found():
    tagger = TaggerService()
    result = tagger.write_replaygain(
        "/nonexistent/track.flac", LoudnessInfo(track_gain_db=-6.0)
    )
    assert result.success is False
    assert result.message == "File not found"


def test_no_existing_tags_and_no_loudness_fails(tmp_path, monkeypatch):
    path = tmp_path / "track.flac"
    path.touch()
    tagger = _tagger(monkeypatch, existing={})

    result = tagger.write_replaygain(str(path), LoudnessInfo(track_gain_db=None))

    assert result.success is False
    assert result.message == "No track gain available"


def test_existing_tags_but_no_fresh_loudness_is_skipped_safely(tmp_path, monkeypatch):
    path = tmp_path / "track.flac"
    path.touch()
    tagger = _tagger(monkeypatch, existing={"REPLAYGAIN_TRACK_GAIN": "-6.00 dB"})

    result = tagger.write_replaygain(str(path), LoudnessInfo(track_gain_db=None))

    assert result.success is True
    assert result.message == "Skipped – existing ReplayGain tags"


def test_existing_tags_within_tolerance_are_skipped(tmp_path, monkeypatch):
    path = tmp_path / "track.flac"
    path.touch()
    tagger = _tagger(monkeypatch, existing={"REPLAYGAIN_TRACK_GAIN": "-6.05 dB"})

    result = tagger.write_replaygain(str(path), LoudnessInfo(track_gain_db=-6.0))

    assert result.success is True
    assert result.message == "Skipped – existing ReplayGain tags already match"


def test_existing_tags_outside_tolerance_are_rewritten(tmp_path, monkeypatch):
    path = tmp_path / "track.flac"
    path.touch()
    tagger = _tagger(monkeypatch, existing={"REPLAYGAIN_TRACK_GAIN": "-3.00 dB"})

    result = tagger.write_replaygain(str(path), LoudnessInfo(track_gain_db=-6.0))

    assert result.success is True
    assert result.message == "Tags written"
    assert result.tags_written["REPLAYGAIN_TRACK_GAIN"] == "-6.00 dB"


def test_overwrite_mode_rewrites_even_when_matching(tmp_path, monkeypatch):
    path = tmp_path / "track.flac"
    path.touch()
    tagger = _tagger(monkeypatch, existing={"REPLAYGAIN_TRACK_GAIN": "-6.00 dB"})

    result = tagger.write_replaygain(
        str(path), LoudnessInfo(track_gain_db=-6.0), mode="overwrite"
    )

    assert result.success is True
    assert result.message == "Tags written"


def test_skip_mode_never_rewrites_existing_tags(tmp_path, monkeypatch):
    path = tmp_path / "track.flac"
    path.touch()
    tagger = _tagger(monkeypatch, existing={"REPLAYGAIN_TRACK_GAIN": "-3.00 dB"})

    result = tagger.write_replaygain(
        str(path), LoudnessInfo(track_gain_db=-6.0), mode="skip"
    )

    assert result.success is True
    assert result.message == "Skipped – existing ReplayGain tags"


def test_skip_mode_writes_when_no_existing_tags(tmp_path, monkeypatch):
    path = tmp_path / "track.flac"
    path.touch()
    tagger = _tagger(monkeypatch, existing={})

    result = tagger.write_replaygain(
        str(path), LoudnessInfo(track_gain_db=-6.0), mode="skip"
    )

    assert result.success is True
    assert result.message == "Tags written"


def test_dry_run_does_not_write(tmp_path, monkeypatch):
    path = tmp_path / "track.flac"
    path.touch()
    tagger = _tagger(monkeypatch, existing={})

    result = tagger.write_replaygain(
        str(path), LoudnessInfo(track_gain_db=-6.0), dry_run=True
    )

    assert result.success is True
    assert result.message == "Dry run – tags not written"


def test_read_existing_rg_finds_id3_txxx_frames(monkeypatch):
    """MP3 ReplayGain tags are stored as ID3 TXXX frames, keyed
    "TXXX:<desc>" rather than the plain field name used by Vorbis/FLAC
    comments -- read_existing_rg must recognize both, or a "fix"/"skip"
    rerun on MP3s never sees its own previously-written tags and
    rewrites every track every time."""
    id3 = ID3()
    id3.add(TXXX(encoding=3, desc="REPLAYGAIN_TRACK_GAIN", text="-6.00 dB"))
    id3.add(TXXX(encoding=3, desc="REPLAYGAIN_TRACK_PEAK", text="0.987"))

    class FakeAudio:
        tags = id3

    monkeypatch.setattr(
        "app.services.tagger.MutagenFile", lambda path, easy=False: FakeAudio()
    )

    existing = TaggerService().read_existing_rg("track.mp3")

    assert existing == {
        "REPLAYGAIN_TRACK_GAIN": "-6.00 dB",
        "REPLAYGAIN_TRACK_PEAK": "0.987",
    }


def test_read_existing_rg_finds_mp4_freeform_atoms(monkeypatch):
    """MP4/M4A has no ReplayGain atom, so it's stored as a freeform
    "----:mean:name" atom whose value is bytes, not str -- and other
    taggers (e.g. mp4gain) write the name in lowercase. Both must be
    recognized or a "fix"/"skip" rerun never sees its own (or a third
    party's) previously-written tags."""

    class FakeAudio:
        tags = {
            "----:com.apple.iTunes:REPLAYGAIN_TRACK_GAIN": [MP4FreeForm(b"-6.00 dB")],
            "----:com.apple.iTunes:replaygain_track_peak": [MP4FreeForm(b"0.987")],
        }

    monkeypatch.setattr(
        "app.services.tagger.MutagenFile", lambda path, easy=False: FakeAudio()
    )

    existing = TaggerService().read_existing_rg("track.m4a")

    assert existing == {
        "REPLAYGAIN_TRACK_GAIN": "-6.00 dB",
        "REPLAYGAIN_TRACK_PEAK": "0.987",
    }


def test_write_replaygain_includes_peak_and_album_fields(tmp_path, monkeypatch):
    path = tmp_path / "track.flac"
    path.touch()
    tagger = _tagger(monkeypatch, existing={})

    result = tagger.write_replaygain(
        str(path),
        LoudnessInfo(
            track_gain_db=-6.0, track_peak=0.9, album_gain_db=-7.0, album_peak=0.95
        ),
    )

    assert result.tags_written == {
        "REPLAYGAIN_TRACK_GAIN": "-6.00 dB",
        "REPLAYGAIN_TRACK_PEAK": "0.900000",
        "REPLAYGAIN_ALBUM_GAIN": "-7.00 dB",
        "REPLAYGAIN_ALBUM_PEAK": "0.950000",
    }


def test_write_replaygain_dispatches_by_extension(tmp_path, monkeypatch):
    tagger = TaggerService()
    monkeypatch.setattr(tagger, "read_existing_rg", lambda path: {})
    calls = []
    for method in (
        "_write_flac",
        "_write_ogg",
        "_write_mp3",
        "_write_mp4",
        "_write_generic",
    ):
        monkeypatch.setattr(
            tagger, method, lambda path, tags, m=method: calls.append(m)
        )

    for suffix in (
        ".flac",
        ".ogg",
        ".oga",
        ".mp3",
        ".m4a",
        ".m4b",
        ".m4p",
        ".mp4",
        ".wav",
    ):
        path = tmp_path / f"track{suffix}"
        path.touch()
        result = tagger.write_replaygain(str(path), LoudnessInfo(track_gain_db=-6.0))
        assert result.success is True

    assert calls == [
        "_write_flac",
        "_write_ogg",
        "_write_ogg",
        "_write_mp3",
        "_write_mp4",
        "_write_mp4",
        "_write_mp4",
        "_write_mp4",
        "_write_generic",
    ]


def test_write_replaygain_catches_writer_errors(tmp_path, monkeypatch):
    path = tmp_path / "track.flac"
    path.touch()
    tagger = _tagger(monkeypatch, existing={})
    monkeypatch.setattr(
        tagger,
        "_write_flac",
        lambda path, tags: (_ for _ in ()).throw(OSError("disk full")),
    )

    result = tagger.write_replaygain(str(path), LoudnessInfo(track_gain_db=-6.0))

    assert result.success is False
    assert result.message == "disk full"


def test_read_existing_rg_returns_empty_when_mutagen_cannot_open(monkeypatch):
    monkeypatch.setattr(
        "app.services.tagger.MutagenFile", lambda path, easy=False: None
    )
    assert TaggerService().read_existing_rg("track.xyz") == {}


def test_gain_matches_false_when_no_fresh_gain():
    tagger = TaggerService()
    assert (
        tagger._gain_matches(
            {"REPLAYGAIN_TRACK_GAIN": "-6.00 dB"}, LoudnessInfo(track_gain_db=None)
        )
        is False
    )


def test_gain_matches_false_when_no_existing_tag():
    tagger = TaggerService()
    assert tagger._gain_matches({}, LoudnessInfo(track_gain_db=-6.0)) is False


def test_gain_matches_false_when_existing_tag_unparseable():
    tagger = TaggerService()
    assert (
        tagger._gain_matches(
            {"REPLAYGAIN_TRACK_GAIN": "garbage"}, LoudnessInfo(track_gain_db=-6.0)
        )
        is False
    )


def test_write_flac(monkeypatch):
    class FakeFLAC(dict):
        def __init__(self, path):
            super().__init__()
            self.saved = False

        def save(self):
            self.saved = True

    instances = []
    monkeypatch.setattr(
        "app.services.tagger.FLAC",
        lambda path: instances.append(FakeFLAC(path)) or instances[-1],
    )

    TaggerService()._write_flac("track.flac", {"REPLAYGAIN_TRACK_GAIN": "-6.00 dB"})

    assert instances[0]["REPLAYGAIN_TRACK_GAIN"] == "-6.00 dB"
    assert instances[0].saved is True


def test_write_ogg(monkeypatch):
    class FakeOggVorbis(dict):
        def __init__(self, path):
            super().__init__()
            self.saved = False

        def save(self):
            self.saved = True

    instances = []
    monkeypatch.setattr(
        "app.services.tagger.OggVorbis",
        lambda path: instances.append(FakeOggVorbis(path)) or instances[-1],
    )

    TaggerService()._write_ogg("track.ogg", {"REPLAYGAIN_TRACK_GAIN": "-6.00 dB"})

    assert instances[0]["REPLAYGAIN_TRACK_GAIN"] == "-6.00 dB"
    assert instances[0].saved is True


def test_write_mp3_creates_new_tag_when_file_has_none(monkeypatch):
    written = {}

    class FakeID3(dict):
        def __init__(self, *args):
            super().__init__()
            if args:
                raise ID3NoHeaderError()

        def delall(self, key):
            self.pop(key, None)

        def add(self, frame):
            self[f"TXXX:{frame.desc}"] = frame

        def save(self, path):
            written["path"] = path
            written["tags"] = dict(self)

    monkeypatch.setattr("app.services.tagger.ID3", FakeID3)

    TaggerService()._write_mp3("track.mp3", {"REPLAYGAIN_TRACK_GAIN": "-6.00 dB"})

    assert written["path"] == "track.mp3"
    assert "TXXX:REPLAYGAIN_TRACK_GAIN" in written["tags"]


def test_write_mp3_reuses_existing_tag(monkeypatch):
    written = {}

    class FakeID3(dict):
        def __init__(self, *args):
            super().__init__()

        def delall(self, key):
            self.pop(key, None)

        def add(self, frame):
            self[f"TXXX:{frame.desc}"] = frame

        def save(self, path):
            written["path"] = path
            written["tags"] = dict(self)

    monkeypatch.setattr("app.services.tagger.ID3", FakeID3)

    TaggerService()._write_mp3("track.mp3", {"REPLAYGAIN_TRACK_GAIN": "-6.00 dB"})

    assert written["path"] == "track.mp3"
    assert "TXXX:REPLAYGAIN_TRACK_GAIN" in written["tags"]


def test_write_generic_writes_via_easy_mutagen(monkeypatch):
    class FakeAudio(dict):
        def save(self):
            self.saved = True

    audio = FakeAudio()
    monkeypatch.setattr(
        "app.services.tagger.MutagenFile", lambda path, easy=True: audio
    )

    TaggerService()._write_generic("track.wav", {"REPLAYGAIN_TRACK_GAIN": "-6.00 dB"})

    assert audio["replaygain_track_gain"] == "-6.00 dB"
    assert audio.saved is True


def test_write_generic_raises_for_unsupported_format(monkeypatch):
    monkeypatch.setattr("app.services.tagger.MutagenFile", lambda path, easy=True: None)

    with pytest.raises(ValueError, match="Unsupported format"):
        TaggerService()._write_generic("track.xyz", {"REPLAYGAIN_TRACK_GAIN": "x"})


def test_write_mp4_stores_freeform_atoms(monkeypatch):
    class FakeMP4(dict):
        def __init__(self, path):
            super().__init__()
            self.saved = False

        def save(self):
            self.saved = True

    instances: list[FakeMP4] = []

    def fake_mp4_ctor(path):
        instance = FakeMP4(path)
        instances.append(instance)
        return instance

    monkeypatch.setattr("app.services.tagger.MP4", fake_mp4_ctor)

    TaggerService()._write_mp4(
        "track.m4a",
        {"REPLAYGAIN_TRACK_GAIN": "-6.00 dB", "REPLAYGAIN_TRACK_PEAK": "0.987000"},
    )

    audio = instances[0]
    assert audio.saved is True
    assert bytes(audio["----:com.apple.iTunes:REPLAYGAIN_TRACK_GAIN"][0]) == (
        b"-6.00 dB"
    )
    assert bytes(audio["----:com.apple.iTunes:REPLAYGAIN_TRACK_PEAK"][0]) == (
        b"0.987000"
    )
