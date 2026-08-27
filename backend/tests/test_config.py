import pytest

from app.core.config import parse_cors


def test_parse_cors_splits_comma_separated_string():
    assert parse_cors("http://a,http://b") == ["http://a", "http://b"]


def test_parse_cors_passes_through_list():
    assert parse_cors(["http://a", "http://b"]) == ["http://a", "http://b"]


def test_parse_cors_passes_through_json_looking_string():
    assert parse_cors('["http://a"]') == '["http://a"]'


def test_parse_cors_rejects_other_types():
    with pytest.raises(ValueError):
        parse_cors(123)
