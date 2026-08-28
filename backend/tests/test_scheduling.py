from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from croniter import croniter
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import settings
from app.models import Job, Source
from app.services import jobs as jobs_module
from app.services.jobs import JobManager


def _naive(dt: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip; normalize before comparing."""
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


@pytest.fixture
def manager(monkeypatch):
    # Schedule tests assert exact next-run times, so pin the zone cron
    # expressions are evaluated in regardless of the deployer's .env.
    monkeypatch.setattr(settings, "TIMEZONE", "UTC")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(jobs_module, "engine", engine)
    manager = JobManager()
    # don't actually execute jobs against a real Plex/Jellyfin server in tests -
    # we only care about Job rows and status transitions the scheduler itself makes
    monkeypatch.setattr(manager._executor, "submit", lambda *a, **kw: None)
    with Session(engine) as session:
        yield manager, session, engine


def _add_source(session, name="lib", **overrides):
    source = Source(name=name, type="plex", base_url="http://x", token="t", **overrides)
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def test_set_schedule_rejects_invalid_cron(manager):
    manager, session, _ = manager
    _add_source(session)
    with pytest.raises(ValueError):
        manager.set_schedule(session, "lib", "not a cron")


@pytest.mark.parametrize("cron_expr", ["* * * * *", "0 0 * * *"])
def test_set_schedule_computes_next_run(manager, cron_expr):
    manager, session, _ = manager
    _add_source(session)
    before = datetime.now(timezone.utc)
    source = manager.set_schedule(session, "lib", cron_expr)
    expected = croniter(cron_expr, before).get_next(datetime)
    assert source.schedule_cron == cron_expr
    assert source.next_run_at is not None
    assert abs((_naive(source.next_run_at) - _naive(expected)).total_seconds()) < 2


def test_set_schedule_evaluates_cron_in_configured_timezone(manager, monkeypatch):
    manager, session, _ = manager
    monkeypatch.setattr(settings, "TIMEZONE", "America/Toronto")
    _add_source(session)

    source = manager.set_schedule(session, "lib", "0 23 * * *")

    assert source.next_run_at is not None
    next_run_local = source.next_run_at.replace(tzinfo=timezone.utc).astimezone(
        ZoneInfo("America/Toronto")
    )
    assert next_run_local.hour == 23
    assert next_run_local.minute == 0


def test_clear_schedule(manager):
    manager, session, _ = manager
    _add_source(session)
    manager.set_schedule(session, "lib", "* * * * *")
    source = manager.clear_schedule(session, "lib")
    assert source.schedule_cron is None
    assert source.next_run_at is None


def test_run_due_schedules_creates_one_job_and_guards_overlap(manager):
    manager, session, engine = manager
    due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    _add_source(
        session,
        name="due",
        schedule_cron="* * * * *",
        next_run_at=due_at,
    )

    manager.run_due_schedules()

    with Session(engine) as check_session:
        jobs = check_session.exec(select(Job).where(Job.source_name == "due")).all()
        assert len(jobs) == 1
        assert jobs[0].status == "pending"  # execution is stubbed out, see fixture

        source = check_session.exec(select(Source).where(Source.name == "due")).first()
        assert source is not None
        assert source.last_run_at is not None
        assert source.next_run_at is not None
        assert _naive(source.next_run_at) > _naive(due_at)

    # make the schedule due again; the still-pending job from above should block a second run
    with Session(engine) as session2:
        source = session2.exec(select(Source).where(Source.name == "due")).first()
        source.next_run_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session2.add(source)
        session2.commit()

    manager.run_due_schedules()

    with Session(engine) as check_session:
        jobs = check_session.exec(select(Job).where(Job.source_name == "due")).all()
        assert len(jobs) == 1


def test_run_due_schedules_skips_disabled_source(manager):
    manager, session, engine = manager
    due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    _add_source(
        session,
        name="disabled",
        enabled=False,
        schedule_cron="* * * * *",
        next_run_at=due_at,
    )

    manager.run_due_schedules()

    with Session(engine) as check_session:
        jobs = check_session.exec(
            select(Job).where(Job.source_name == "disabled")
        ).all()
        assert len(jobs) == 0
