import logging

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import Job
from app.schemas.gain import LoudnessInfo, TrackInfo, WriteResult
from app.services import jobs as jobs_module
from app.services.jobs import JobManager


@pytest.fixture
def manager(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(jobs_module, "engine", engine)
    manager = JobManager()
    with Session(engine) as session:
        yield manager, session, engine


def _add_job(session, job_id="job-1", **overrides):
    job = Job(id=job_id, source_name="lib", status="running", **overrides)
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
        "[job job-1] skipped" in r.message
        and "existing ReplayGain tags" in r.message
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

    manager._run_plex("job-1", "http://x", "t", None, False, "fix", [])

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
