import logging
import threading

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.models import Job, JobCreate, Source
from app.schemas.gain import LoudnessInfo, TrackInfo, WriteResult
from app.services import jobs as jobs_module
from app.services.jobs import JobManager


@pytest.fixture
def manager(monkeypatch):
    # StaticPool: an in-memory sqlite db is otherwise per-connection, so the
    # real executor worker thread used by the shutdown/cancellation tests
    # would see an empty database without a single shared connection.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(jobs_module, "engine", engine)
    manager = JobManager()
    with Session(engine) as session:
        yield manager, session, engine


def _add_job(session, job_id="job-1", **overrides):
    fields = {"source_name": "lib", "status": "running", **overrides}
    job = Job(id=job_id, **fields)
    session.add(job)
    session.commit()
    return job


def _track(path="/music/track.flac", gain=-6.0):
    return TrackInfo(
        id=path,
        title="Some Track",
        path=path,
        loudness=LoudnessInfo(track_gain_db=gain) if gain is not None else None,
    )


# ----- log emission -----


def test_process_track_logs_missing_path_or_loudness(manager, caplog):
    manager, session, _ = manager
    _add_job(session)
    caplog.set_level(logging.INFO)

    manager._process_track("job-1", _track(gain=None), False, "fix", [])

    assert any(
        "[job job-1] skipped" in r.message and "missing path or loudness" in r.message
        for r in caplog.records
    )


def test_process_track_logs_tagger_skip(manager, caplog, monkeypatch):
    manager, session, _ = manager
    _add_job(session)
    monkeypatch.setattr(
        manager._tagger,
        "write_replaygain",
        lambda *a, **kw: WriteResult(
            path="x", success=True, message="Skipped – existing ReplayGain tags"
        ),
    )
    caplog.set_level(logging.INFO)

    manager._process_track("job-1", _track(), False, "fix", [])

    assert any(
        "[job job-1] skipped" in r.message and "existing ReplayGain tags" in r.message
        for r in caplog.records
    )


def test_process_track_logs_tagger_error(manager, caplog, monkeypatch):
    manager, session, _ = manager
    _add_job(session)
    monkeypatch.setattr(
        manager._tagger,
        "write_replaygain",
        lambda *a, **kw: WriteResult(
            path="x", success=False, message="No track gain available"
        ),
    )
    caplog.set_level(logging.INFO)

    manager._process_track("job-1", _track(), False, "fix", [])

    assert any(
        "[job job-1] error" in r.message and "No track gain available" in r.message
        for r in caplog.records
    )


def test_process_track_successful_write_is_not_logged(manager, caplog, monkeypatch):
    manager, session, _ = manager
    _add_job(session)
    monkeypatch.setattr(
        manager._tagger,
        "write_replaygain",
        lambda *a, **kw: WriteResult(path="x", success=True, message="Tags written"),
    )
    caplog.set_level(logging.INFO)

    manager._process_track("job-1", _track(), False, "fix", [])

    assert not any("[job job-1]" in r.message for r in caplog.records)


# ----- reliability: one bad track doesn't kill the job -----


class _FakePlexService:
    def __init__(self, base_url, token):
        pass

    def iter_tracks(self, library_id):
        return [1, 2, 3]

    def get_track_info(self, track):
        if track == 2:
            raise RuntimeError("boom")
        return _track(path=f"/music/{track}.flac")


def test_run_plex_continues_past_a_bad_track(manager, caplog, monkeypatch):
    manager, session, engine = manager
    _add_job(session)
    monkeypatch.setattr(jobs_module, "PlexService", _FakePlexService)
    monkeypatch.setattr(
        manager._tagger,
        "write_replaygain",
        lambda *a, **kw: WriteResult(path="x", success=True, message="Tags written"),
    )
    caplog.set_level(logging.WARNING)

    manager._run_plex(
        "job-1", "http://x", "t", None, False, "fix", [], threading.Event()
    )

    with Session(engine) as check_session:
        job = check_session.get(Job, "job-1")
        assert job.processed == 3
        assert job.written == 2
        assert job.errors == 1
        assert job.status != "failed"

    assert any(
        "[job job-1] error (track fetch failed): boom" in r.message
        for r in caplog.records
    )


# ----- cancellation -----


def test_run_plex_stops_when_cancel_event_is_set(manager, monkeypatch):
    manager, session, engine = manager
    _add_job(session)
    monkeypatch.setattr(jobs_module, "PlexService", _FakePlexService)
    monkeypatch.setattr(
        manager._tagger,
        "write_replaygain",
        lambda *a, **kw: WriteResult(path="x", success=True, message="Tags written"),
    )
    cancel_event = threading.Event()
    cancel_event.set()

    manager._run_plex("job-1", "http://x", "t", None, False, "fix", [], cancel_event)

    with Session(engine) as check_session:
        job = check_session.get(Job, "job-1")
        assert job.processed == 0
        assert job.written == 0


def test_cancel_job_not_found_returns_none(manager):
    manager, session, _ = manager
    assert manager.cancel_job(session, "missing") is None


def test_cancel_job_already_completed_raises(manager):
    manager, session, _ = manager
    _add_job(session, status="completed")
    with pytest.raises(ValueError, match="not running"):
        manager.cancel_job(session, "job-1")


def test_cancel_job_pending_marks_cancelled_immediately(manager):
    manager, session, _ = manager
    _add_job(session, status="pending")

    job = manager.cancel_job(session, "job-1")

    assert job is not None
    assert job.status == "cancelled"
    assert job.message == "Cancelled"


def test_cancel_job_running_only_sets_event_leaves_status_to_worker(manager):
    manager, session, _ = manager
    _add_job(session, status="running")
    event = threading.Event()
    manager._cancel_events["job-1"] = event

    job = manager.cancel_job(session, "job-1")

    assert event.is_set()
    assert job is not None
    assert job.status == "running"  # the worker thread finalizes this, not cancel_job


def test_run_job_already_cancelled_finishes_as_cancelled_without_running(manager):
    manager, session, engine = manager
    _add_job(session, status="pending")
    event = threading.Event()
    event.set()
    manager._cancel_events["job-1"] = event

    manager._run_job("job-1")

    with Session(engine) as check_session:
        job = check_session.get(Job, "job-1")
        assert job.status == "cancelled"
        assert job.message == "Cancelled"
    assert "job-1" not in manager._cancel_events
    assert "job-1" not in manager._futures


def test_create_job_registers_cancel_event(manager, monkeypatch):
    manager, session, _ = manager
    monkeypatch.setattr(manager._executor, "submit", lambda *a, **kw: None)
    session.add(Source(name="lib", type="plex", base_url="http://x", token="t"))
    session.commit()

    job = manager.create_job(session, JobCreate(source_name="lib"))

    assert job is not None
    assert job.id in manager._cancel_events
    assert not manager._cancel_events[job.id].is_set()


def test_shutdown_with_no_active_jobs_returns_immediately(manager):
    manager, _, _ = manager
    manager.shutdown()  # should not raise or hang


def test_shutdown_cancels_and_waits_for_a_running_job(manager, monkeypatch):
    """Simulates the SIGTERM path: a job is actively processing tracks when
    shutdown() is called, and it should stop cooperatively rather than being
    left running or racing to completion."""
    manager, session, engine = manager
    session.add(Source(name="lib", type="plex", base_url="http://x", token="t"))
    session.commit()

    started = threading.Event()
    release = threading.Event()

    class _BlockingFakePlexService:
        def __init__(self, base_url, token):
            pass

        def iter_tracks(self, library_id):
            return list(range(5))

        def get_track_info(self, track):
            started.set()
            assert release.wait(timeout=5), "test setup: release was never set"
            return _track(path=f"/music/{track}.flac")

    monkeypatch.setattr(jobs_module, "PlexService", _BlockingFakePlexService)
    monkeypatch.setattr(
        manager._tagger,
        "write_replaygain",
        lambda *a, **kw: WriteResult(path="x", success=True, message="Tags written"),
    )

    job = manager.create_job(session, JobCreate(source_name="lib"))
    assert job is not None
    assert started.wait(timeout=5), "worker never reached the first track"

    # Flag cancellation while the worker is still blocked fetching track 0,
    # then let it proceed -- it must observe cancellation before track 1.
    manager.cancel_all_active()
    release.set()
    manager.shutdown()

    with Session(engine) as check_session:
        final = check_session.get(Job, job.id)
        assert final.status == "cancelled"
        assert final.processed == 1


def test_shutdown_logs_warning_when_a_job_does_not_stop_in_time(
    manager, monkeypatch, caplog
):
    manager, session, _ = manager
    session.add(Source(name="lib", type="plex", base_url="http://x", token="t"))
    session.commit()
    manager._SHUTDOWN_TIMEOUT = 0.05

    started = threading.Event()
    release = threading.Event()

    class _StuckFetchingPlexService:
        def __init__(self, base_url, token):
            pass

        def iter_tracks(self, library_id):
            # Blocked before the per-track loop even starts, so it never
            # notices cancel_event -- exactly what should time out shutdown.
            started.set()
            assert release.wait(timeout=5), "test setup: release was never set"
            return []

    monkeypatch.setattr(jobs_module, "PlexService", _StuckFetchingPlexService)
    job = manager.create_job(session, JobCreate(source_name="lib"))
    assert job is not None
    assert started.wait(timeout=5), "worker never started fetching tracks"

    caplog.set_level(logging.WARNING)
    manager.cancel_all_active()
    manager.shutdown()

    assert any("did not stop within" in r.message for r in caplog.records)
    release.set()  # let the worker thread finish so it doesn't linger


# ----- read_log -----


def test_read_log_missing_file_returns_empty_string(manager, tmp_path, monkeypatch):
    manager, _, _ = manager
    monkeypatch.setattr(jobs_module.settings, "LOG_FILE", str(tmp_path / "none.log"))
    assert manager.read_log() == ""


def test_read_log_filters_by_job_id(manager, tmp_path, monkeypatch):
    manager, _, _ = manager
    log_file = tmp_path / "test.log"
    log_file.write_text(
        "2026-01-01 INFO app: [job job-1] skipped /a: reason a\n"
        "2026-01-01 INFO app: [job job-2] skipped /b: reason b\n"
        "2026-01-01 INFO app: [job job-1] error /c: reason c\n"
    )
    monkeypatch.setattr(jobs_module.settings, "LOG_FILE", str(log_file))

    result = manager.read_log("job-1")

    lines = result.splitlines()
    assert len(lines) == 2
    assert all("job job-1" in line for line in lines)


def test_read_log_without_job_id_returns_capped_tail(manager, tmp_path, monkeypatch):
    manager, _, _ = manager
    log_file = tmp_path / "test.log"
    total_lines = jobs_module.MAX_LOG_LINES + 50
    log_file.write_text("\n".join(f"line {i}" for i in range(total_lines)) + "\n")
    monkeypatch.setattr(jobs_module.settings, "LOG_FILE", str(log_file))

    result = manager.read_log()

    lines = result.splitlines()
    assert len(lines) == jobs_module.MAX_LOG_LINES
    assert lines[0] == f"line {total_lines - jobs_module.MAX_LOG_LINES}"
    assert lines[-1] == f"line {total_lines - 1}"
