from pathlib import Path

import pytest

from app.core.config import _detect_timezone, parse_cors


def test_parse_cors_splits_comma_separated_string():
    assert parse_cors("http://a,http://b") == ["http://a", "http://b"]


def test_parse_cors_passes_through_list():
    assert parse_cors(["http://a", "http://b"]) == ["http://a", "http://b"]


def test_parse_cors_passes_through_json_looking_string():
    assert parse_cors('["http://a"]') == '["http://a"]'


def test_parse_cors_rejects_other_types():
    with pytest.raises(ValueError):
        parse_cors(123)


def test_detect_timezone_prefers_tz_env_var(monkeypatch):
    monkeypatch.setenv("TZ", "America/Chicago")
    assert _detect_timezone() == "America/Chicago"


def test_detect_timezone_falls_back_to_etc_timezone_file(monkeypatch):
    monkeypatch.delenv("TZ", raising=False)
    monkeypatch.setattr(Path, "read_text", lambda self: "America/Vancouver\n")
    assert _detect_timezone() == "America/Vancouver"


def test_detect_timezone_falls_back_to_etc_localtime_symlink(monkeypatch):
    monkeypatch.delenv("TZ", raising=False)

    def raise_missing(_self):
        raise OSError("no such file")

    monkeypatch.setattr(Path, "read_text", raise_missing)
    monkeypatch.setattr(
        Path, "resolve", lambda self: Path("/usr/share/zoneinfo/Europe/Berlin")
    )
    assert _detect_timezone() == "Europe/Berlin"


def test_detect_timezone_defaults_to_utc_when_nothing_resolves(monkeypatch):
    monkeypatch.delenv("TZ", raising=False)

    def raise_missing(_self):
        raise OSError("no such file")

    monkeypatch.setattr(Path, "read_text", raise_missing)
    monkeypatch.setattr(Path, "resolve", raise_missing)
    assert _detect_timezone() == "UTC"
