from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Job, Source
from app.services import jobs as jobs_module
from app.services.jobs import JobManager


@pytest.fixture
def manager(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(jobs_module, "engine", engine)
    manager = JobManager()
    monkeypatch.setattr(manager._executor, "submit", lambda *a, **kw: None)
    with Session(engine) as session:
        yield manager, session, engine


def _add_source(session, name="lib", **overrides):
    fields = {"type": "plex", "base_url": "http://x", "token": "t", **overrides}
    source = Source(name=name, **fields)
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def _add_job(session, job_id="job-1", **overrides):
    fields = {"source_name": "lib", "status": "running", **overrides}
    job = Job(id=job_id, **fields)
    session.add(job)
    session.commit()
    return job


# ----- get_libraries: jellyfin branch -----


class _FakeJellyfinService:
    def __init__(self, base_url, token):
        self.closed = False

    def get_music_libraries(self):
        return [{"id": "1", "name": "Music", "type": "music"}]

    def close(self):
        self.closed = True


def test_get_libraries_jellyfin_closes_client(manager, monkeypatch):
    manager, _, _ = manager
    instances = []

    def factory(base_url, token):
        svc = _FakeJellyfinService(base_url, token)
        instances.append(svc)
        return svc

    monkeypatch.setattr(jobs_module, "JellyfinService", factory)
    libs = manager.get_libraries("jellyfin", "http://y", "k")
    assert libs == [{"id": "1", "name": "Music", "type": "music"}]
    assert instances[0].closed is True


class _FailingJellyfinService:
    def __init__(self, base_url, token):
        self.closed = False

    def get_music_libraries(self):
        raise RuntimeError("unreachable")

    def close(self):
        self.closed = True


def test_get_libraries_jellyfin_failure_still_closes_client(manager, monkeypatch):
    manager, _, _ = manager
    instances = []

    def factory(base_url, token):
        svc = _FailingJellyfinService(base_url, token)
        instances.append(svc)
        return svc

    monkeypatch.setattr(jobs_module, "JellyfinService", factory)
    with pytest.raises(RuntimeError):
        manager.get_libraries("jellyfin", "http://y", "k")
    assert instances[0].closed is True


# ----- cancel_all_active -----


def test_cancel_all_active_cancels_pending_and_skips_terminal(manager):
    manager, session, engine = manager
    _add_job(session, job_id="pending-1", status="pending")
    _add_job(session, job_id="running-1", status="running")
    _add_job(session, job_id="done-1", status="completed")

    manager.cancel_all_active()

    with Session(engine) as check:
        assert check.get(Job, "pending-1").status == "cancelled"
        assert check.get(Job, "running-1").status == "running"  # worker finalizes it
        assert check.get(Job, "done-1").status == "completed"


def test_cancel_all_active_ignores_a_job_that_finishes_mid_sweep(manager, monkeypatch):
    """A job can transition to a terminal state (finalized by its own worker
    thread) between cancel_all_active's query and its cancel_job call for
    that row; cancel_job's ValueError for that race is swallowed rather than
    aborting the sweep for the rest of the active jobs."""
    manager, session, _ = manager
    _add_job(session, job_id="pending-1", status="pending")
    _add_job(session, job_id="running-1", status="running")

    real_cancel_job = manager.cancel_job

    def flaky_cancel_job(session, job_id):
        if job_id == "running-1":
            raise ValueError("Job is not running (status=completed)")
        return real_cancel_job(session, job_id)

    monkeypatch.setattr(manager, "cancel_job", flaky_cancel_job)

    manager.cancel_all_active()  # should not raise despite running-1's ValueError


# ----- prune_old_jobs -----


def test_prune_old_jobs_deletes_only_stale_terminal_jobs(manager):
    manager, session, engine = manager
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=31)

    stale_completed = _add_job(session, job_id="stale", status="completed")
    stale_completed.updated_at = old
    recent_completed = _add_job(session, job_id="recent", status="completed")
    recent_completed.updated_at = now
    stale_pending = _add_job(session, job_id="stale-pending", status="pending")
    stale_pending.updated_at = old
    session.add_all([stale_completed, recent_completed, stale_pending])
    session.commit()

    deleted = manager.prune_old_jobs()

    assert deleted == 1
    with Session(engine) as check:
        remaining = {j.id for j in check.exec(select(Job)).all()}
    assert remaining == {"recent", "stale-pending"}


def test_prune_old_jobs_returns_zero_when_nothing_stale(manager):
    manager, session, _ = manager
    _add_job(session, job_id="recent", status="completed")

    assert manager.prune_old_jobs() == 0


# ----- _update_job -----


def test_update_job_missing_job_is_a_no_op(manager):
    manager, _, _ = manager
    manager._update_job("does-not-exist", status="failed")  # should not raise


# ----- _run_job -----


def test_run_job_missing_job_row_is_a_no_op(manager):
    manager, _, _ = manager
    manager._run_job("does-not-exist")  # should not raise


def test_bump_missing_job_is_a_no_op(manager):
    manager, _, _ = manager
    manager._bump("does-not-exist", processed=1)  # should not raise


class _PlexFetchFailsService:
    def __init__(self, base_url, token):
        pass

    def iter_tracks(self, library_id):
        raise RuntimeError("plex unreachable")


def test_run_plex_reraises_when_fetching_tracks_fails(manager, monkeypatch):
    import threading

    manager, session, _ = manager
    _add_job(session, job_id="job-1")
    monkeypatch.setattr(jobs_module, "PlexService", _PlexFetchFailsService)

    with pytest.raises(RuntimeError, match="plex unreachable"):
        manager._run_plex(
            "job-1", "http://x", "t", None, False, "fix", [], threading.Event()
        )


def test_run_job_marks_failed_when_the_run_raises(manager, monkeypatch):
    manager, session, engine = manager
    _add_source(session)
    _add_job(session, job_id="job-1", source_name="lib", status="pending")
    monkeypatch.setattr(jobs_module, "PlexService", _PlexFetchFailsService)

    manager._run_job("job-1")

    with Session(engine) as check:
        job = check.get(Job, "job-1")
        assert job.status == "failed"
        assert job.message == "plex unreachable"


def test_run_job_full_lifecycle_for_jellyfin_source(manager, monkeypatch):
    from app.schemas.gain import LoudnessInfo, TrackInfo, WriteResult

    manager, session, engine = manager
    _add_source(session, type="jellyfin")
    _add_job(session, job_id="job-1", source_name="lib", status="pending")

    class _OneTrackJellyfinService:
        def __init__(self, base_url, token):
            self.closed = False

        def iter_audio_items(self, library_id):
            return [{"Id": "1"}]

        def get_track_info(self, item):
            return TrackInfo(
                id="1",
                title="Song",
                path="/music/1.flac",
                loudness=LoudnessInfo(track_gain_db=-6.0),
            )

        def close(self):
            self.closed = True

    monkeypatch.setattr(jobs_module, "JellyfinService", _OneTrackJellyfinService)
    monkeypatch.setattr(
        manager._tagger,
        "write_replaygain",
        lambda *a, **kw: WriteResult(path="x", success=True, message="Tags written"),
    )

    manager._run_job("job-1")

    with Session(engine) as check:
        job = check.get(Job, "job-1")
        assert job.status == "completed"
        assert job.written == 1


class _JellyfinFetchFailsService:
    def __init__(self, base_url, token):
        self.closed = False

    def iter_audio_items(self, library_id):
        raise RuntimeError("jellyfin unreachable")

    def close(self):
        self.closed = True


def test_run_jellyfin_reraises_and_closes_when_fetching_items_fails(
    manager, monkeypatch
):
    import threading

    manager, session, _ = manager
    _add_job(session, job_id="job-1")
    instances = []

    def factory(base_url, token):
        svc = _JellyfinFetchFailsService(base_url, token)
        instances.append(svc)
        return svc

    monkeypatch.setattr(jobs_module, "JellyfinService", factory)

    with pytest.raises(RuntimeError, match="jellyfin unreachable"):
        manager._run_jellyfin(
            "job-1", "http://y", "k", None, False, "fix", [], threading.Event()
        )
    assert instances[0].closed is True


def test_run_jellyfin_stops_when_cancel_event_is_set(manager, monkeypatch):
    import threading

    manager, session, engine = manager
    _add_job(session, job_id="job-1")
    monkeypatch.setattr(jobs_module, "JellyfinService", _FakeJellyfinRunService)
    cancel_event = threading.Event()
    cancel_event.set()

    manager._run_jellyfin(
        "job-1", "http://y", "k", None, False, "fix", [], cancel_event
    )

    with Session(engine) as check:
        job = check.get(Job, "job-1")
        assert job.processed == 0


def test_run_job_missing_source_marks_failed(manager):
    manager, session, engine = manager
    _add_job(session, job_id="job-1", source_name="ghost", status="pending")

    manager._run_job("job-1")

    with Session(engine) as check:
        job = check.get(Job, "job-1")
        assert job.status == "failed"
        assert job.message == "Source missing"


# ----- _run_jellyfin -----


class _FakeJellyfinRunService:
    def __init__(self, base_url, token):
        self.closed = False

    def iter_audio_items(self, library_id):
        return [{"Id": "1"}, {"Id": "2"}, {"Id": "3"}]

    def get_track_info(self, item):
        if item["Id"] == "2":
            raise RuntimeError("boom")
        from app.schemas.gain import LoudnessInfo, TrackInfo

        return TrackInfo(
            id=item["Id"],
            title="Song",
            path=f"/music/{item['Id']}.flac",
            loudness=LoudnessInfo(track_gain_db=-6.0),
        )

    def close(self):
        self.closed = True


def test_run_jellyfin_continues_past_bad_item_and_closes(manager, monkeypatch):
    import threading

    from app.schemas.gain import WriteResult

    manager, session, engine = manager
    _add_job(session, job_id="job-1", source_name="lib")
    instances = []

    def factory(base_url, token):
        svc = _FakeJellyfinRunService(base_url, token)
        instances.append(svc)
        return svc

    monkeypatch.setattr(jobs_module, "JellyfinService", factory)
    monkeypatch.setattr(
        manager._tagger,
        "write_replaygain",
        lambda *a, **kw: WriteResult(path="x", success=True, message="Tags written"),
    )

    manager._run_jellyfin(
        "job-1", "http://y", "k", None, False, "fix", [], threading.Event()
    )

    with Session(engine) as check:
        job = check.get(Job, "job-1")
        assert job.processed == 3
        assert job.written == 2
        assert job.errors == 1
    assert instances[0].closed is True
