import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import PathMappingCreate, Source, SourceCreate
from app.services import jobs as jobs_module
from app.services.jobs import JobManager, _remap_path, _validate_path_mapping


@pytest.fixture
def manager(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(jobs_module, "engine", engine)
    manager = JobManager()
    monkeypatch.setattr(manager._executor, "submit", lambda *a, **kw: None)
    with Session(engine) as session:
        yield manager, session


# ----- _remap_path -----


def test_remap_path_no_mapping_passthrough():
    assert _remap_path("/data/music/a.flac", []) == "/data/music/a.flac"


def test_remap_path_exact_match():
    assert _remap_path("/data/music", [("/data/music", "/mnt/music")]) == "/mnt/music"


def test_remap_path_nested_subpath():
    assert (
        _remap_path(
            "/data/music/Artist/track.flac", [("/data/music", "/mnt/music")]
        )
        == "/mnt/music/Artist/track.flac"
    )


def test_remap_path_non_matching_passthrough():
    assert (
        _remap_path("/other/track.flac", [("/data/music", "/mnt/music")])
        == "/other/track.flac"
    )


def test_remap_path_false_prefix_not_matched():
    # "/data/music" must not match "/data/music2/..."
    assert (
        _remap_path("/data/music2/track.mp3", [("/data/music", "/mnt/music")])
        == "/data/music2/track.mp3"
    )


def test_remap_path_trailing_slash_tolerance():
    assert (
        _remap_path(
            "/data/music/Artist/track.flac", [("/data/music/", "/mnt/music/")]
        )
        == "/mnt/music/Artist/track.flac"
    )


def test_remap_path_multiple_mappings_first_match_wins():
    mappings = [
        ("/data/music1", "/mnt/music1"),
        ("/data/music2", "/mnt/music2"),
    ]
    assert (
        _remap_path("/data/music2/Artist/track.flac", mappings)
        == "/mnt/music2/Artist/track.flac"
    )
    assert (
        _remap_path("/data/music1/Artist/track.flac", mappings)
        == "/mnt/music1/Artist/track.flac"
    )
    assert _remap_path("/other/track.flac", mappings) == "/other/track.flac"


# ----- _validate_path_mapping -----


def test_validate_path_mapping_rejects_nonexistent_local_path(tmp_path):
    missing = tmp_path / "does-not-exist"
    with pytest.raises(ValueError):
        _validate_path_mapping("/data/music", str(missing))


def test_validate_path_mapping_accepts_valid_pair(tmp_path):
    _validate_path_mapping("/data/music", str(tmp_path))


def test_validate_path_mapping_rejects_empty_remote_path(tmp_path):
    with pytest.raises(ValueError):
        _validate_path_mapping("   ", str(tmp_path))


# ----- add_source -----


def test_add_source_rejects_nonexistent_local_path(manager, tmp_path):
    manager, session = manager
    missing = tmp_path / "does-not-exist"
    with pytest.raises(ValueError):
        manager.add_source(
            session,
            SourceCreate(
                name="lib",
                type="plex",
                base_url="http://x",
                token="t",
                path_mappings=[
                    PathMappingCreate(remote_path="/data/music", local_path=str(missing))
                ],
            ),
        )


def test_add_source_with_no_mappings(manager):
    manager, session = manager
    source = manager.add_source(
        session,
        SourceCreate(name="lib", type="plex", base_url="http://x", token="t"),
    )
    assert isinstance(source, Source)
    assert source.path_mappings == []


def test_add_source_persists_multiple_mappings(manager, tmp_path):
    manager, session = manager
    d1 = tmp_path / "music1"
    d2 = tmp_path / "music2"
    d1.mkdir()
    d2.mkdir()
    source = manager.add_source(
        session,
        SourceCreate(
            name="lib",
            type="plex",
            base_url="http://x",
            token="t",
            path_mappings=[
                PathMappingCreate(remote_path="/data/music1", local_path=str(d1)),
                PathMappingCreate(remote_path="/data/music2", local_path=str(d2)),
            ],
        ),
    )
    assert {(m.remote_path, m.local_path) for m in source.path_mappings} == {
        ("/data/music1", str(d1)),
        ("/data/music2", str(d2)),
    }


def test_add_source_edit_replaces_mappings_wholesale(manager, tmp_path):
    manager, session = manager
    d1 = tmp_path / "music1"
    d2 = tmp_path / "music2"
    d1.mkdir()
    d2.mkdir()

    manager.add_source(
        session,
        SourceCreate(
            name="lib",
            type="plex",
            base_url="http://x",
            token="t",
            path_mappings=[
                PathMappingCreate(remote_path="/data/music1", local_path=str(d1))
            ],
        ),
    )

    # editing (upsert by name) with a different mapping list should fully
    # replace the old one, not append to it
    updated = manager.add_source(
        session,
        SourceCreate(
            name="lib",
            type="plex",
            base_url="http://x",
            token="t",
            path_mappings=[
                PathMappingCreate(remote_path="/data/music2", local_path=str(d2))
            ],
        ),
    )
    assert [(m.remote_path, m.local_path) for m in updated.path_mappings] == [
        ("/data/music2", str(d2))
    ]

    # and clearing entirely (no mappings) should leave none behind
    cleared = manager.add_source(
        session,
        SourceCreate(name="lib", type="plex", base_url="http://x", token="t"),
    )
    assert cleared.path_mappings == []
