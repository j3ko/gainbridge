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
    tagger = _tagger(
        monkeypatch, existing={"REPLAYGAIN_TRACK_GAIN": "-6.00 dB"}
    )

    result = tagger.write_replaygain(str(path), LoudnessInfo(track_gain_db=None))

    assert result.success is True
    assert result.message == "Skipped – existing ReplayGain tags"


def test_existing_tags_within_tolerance_are_skipped(tmp_path, monkeypatch):
    path = tmp_path / "track.flac"
    path.touch()
    tagger = _tagger(
        monkeypatch, existing={"REPLAYGAIN_TRACK_GAIN": "-6.05 dB"}
    )

    result = tagger.write_replaygain(str(path), LoudnessInfo(track_gain_db=-6.0))

    assert result.success is True
    assert result.message == "Skipped – existing ReplayGain tags already match"


def test_existing_tags_outside_tolerance_are_rewritten(tmp_path, monkeypatch):
    path = tmp_path / "track.flac"
    path.touch()
    tagger = _tagger(
        monkeypatch, existing={"REPLAYGAIN_TRACK_GAIN": "-3.00 dB"}
    )

    result = tagger.write_replaygain(str(path), LoudnessInfo(track_gain_db=-6.0))

    assert result.success is True
    assert result.message == "Tags written"
    assert result.tags_written["REPLAYGAIN_TRACK_GAIN"] == "-6.00 dB"


def test_overwrite_mode_rewrites_even_when_matching(tmp_path, monkeypatch):
    path = tmp_path / "track.flac"
    path.touch()
    tagger = _tagger(
        monkeypatch, existing={"REPLAYGAIN_TRACK_GAIN": "-6.00 dB"}
    )

    result = tagger.write_replaygain(
        str(path), LoudnessInfo(track_gain_db=-6.0), mode="overwrite"
    )

    assert result.success is True
    assert result.message == "Tags written"


def test_skip_mode_never_rewrites_existing_tags(tmp_path, monkeypatch):
    path = tmp_path / "track.flac"
    path.touch()
    tagger = _tagger(
        monkeypatch, existing={"REPLAYGAIN_TRACK_GAIN": "-3.00 dB"}
    )

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
