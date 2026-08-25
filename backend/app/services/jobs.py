from __future__ import annotations

import logging
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import wait as wait_futures
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from croniter import croniter
from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.db import engine
from app.models import Job, JobCreate, PathMapping, Source, SourceCreate
from app.schemas.gain import TrackInfo
from app.services.jellyfin import JellyfinService
from app.services.plex import PlexService
from app.services.tagger import TaggerService, WriteMode

logger = logging.getLogger(__name__)

MAX_LOG_LINES = 1000


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _compute_next_run(cron_expr: str, base: datetime | None = None) -> datetime:
    return croniter(cron_expr, base or _utcnow()).get_next(datetime)


def _validate_path_mapping(remote_path: str, local_path: str) -> None:
    if not remote_path.strip():
        raise ValueError("remote_path must not be empty")
    if not Path(local_path).is_dir():
        raise ValueError(
            f"local_path does not exist or is not a directory: {local_path}"
        )


def _remap_path(path: str, mappings: list[tuple[str, str]]) -> str:
    """Rewrite a track path using the first matching remote->local mapping.

    A single Plex/Jellyfin library can span multiple folders on disk, so a
    source may have several mappings; the first configured one whose
    remote_path is a prefix of `path` wins.
    """
    for remote_path, local_path in mappings:
        remote = remote_path.rstrip("/")
        local = local_path.rstrip("/")
        if path == remote:
            return local
        if path.startswith(remote + "/"):
            return local + path[len(remote) :]
    return path


class JobManager:
    # How long shutdown() waits for active jobs to notice cancellation and
    # stop before giving up on a clean exit.
    _SHUTDOWN_TIMEOUT = 30.0

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._tagger = TaggerService()
        self._cancel_events: dict[str, threading.Event] = {}
        self._futures: dict[str, Future[None]] = {}

    # ----- sources -----
    def add_source(self, session: Session, data: SourceCreate) -> Source:
        for m in data.path_mappings:
            _validate_path_mapping(m.remote_path, m.local_path)

        payload = data.model_dump(exclude={"path_mappings"})
        mappings = [
            PathMapping(remote_path=m.remote_path, local_path=m.local_path)
            for m in data.path_mappings
        ]

        existing = session.exec(select(Source).where(Source.name == data.name)).first()
        if existing:
            for k, v in payload.items():
                setattr(existing, k, v)
            existing.updated_at = _utcnow()
            existing.path_mappings = mappings
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing
        source = Source(**payload)
        source.path_mappings = mappings
        session.add(source)
        session.commit()
        session.refresh(source)
        return source

    def list_sources(self, session: Session) -> list[Source]:
        return list(session.exec(select(Source).order_by(Source.name)).all())

    def get_source(self, session: Session, name: str) -> Source | None:
        return session.exec(select(Source).where(Source.name == name)).first()

    def delete_source(self, session: Session, name: str) -> bool:
        source = self.get_source(session, name)
        if not source:
            return False
        session.delete(source)
        session.commit()
        return True

    def set_schedule(
        self, session: Session, name: str, cron_expr: str, enabled: bool
    ) -> Source:
        source = self.get_source(session, name)
        if not source:
            raise KeyError(name)
        if not croniter.is_valid(cron_expr):
            raise ValueError(f"Invalid cron expression: {cron_expr}")
        source.schedule_cron = cron_expr
        source.schedule_enabled = enabled
        source.next_run_at = _compute_next_run(cron_expr) if enabled else None
        source.updated_at = _utcnow()
        session.add(source)
        session.commit()
        session.refresh(source)
        return source

    def clear_schedule(self, session: Session, name: str) -> Source:
        source = self.get_source(session, name)
        if not source:
            raise KeyError(name)
        source.schedule_cron = None
        source.schedule_enabled = False
        source.next_run_at = None
        source.updated_at = _utcnow()
        session.add(source)
        session.commit()
        session.refresh(source)
        return source

    def test_source(self, session: Session, name: str) -> dict[str, Any]:
        cfg = self.get_source(session, name)
        if not cfg:
            raise KeyError(name)
        return self.test_connection(cfg.type, cfg.base_url, cfg.token, cfg.user_id)

    def test_connection(
        self, type: str, base_url: str, token: str, user_id: str | None = None
    ) -> dict[str, Any]:
        if type == "plex":
            return PlexService(base_url, token).test_connection()
        svc = JellyfinService(base_url, token, user_id=user_id)
        try:
            return svc.test_connection()
        finally:
            svc.close()

    # ----- jobs -----
    def create_job(
        self, session: Session, body: JobCreate, skip_if_running: bool = False
    ) -> Job | None:
        if not self.get_source(session, body.source_name):
            raise ValueError(f"Unknown source: {body.source_name}")

        if skip_if_running:
            existing = session.exec(
                select(Job).where(
                    Job.source_name == body.source_name,
                    col(Job.status).in_(["pending", "running"]),
                )
            ).first()
            if existing:
                return None

        job_id = str(uuid.uuid4())
        self._cancel_events[job_id] = threading.Event()
        job = Job(
            id=job_id,
            source_name=body.source_name,
            library_id=body.library_id,
            dry_run=body.dry_run,
            write_mode=body.write_mode,
            status="pending",
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        self._futures[job_id] = self._executor.submit(self._run_job, job_id)
        return job

    def cancel_job(self, session: Session, job_id: str) -> Job | None:
        job = session.get(Job, job_id)
        if not job:
            return None
        if job.status not in ("pending", "running"):
            raise ValueError(f"Job is not running (status={job.status})")

        event = self._cancel_events.get(job_id)
        if event:
            event.set()

        if job.status == "pending":
            # Not yet picked up by the worker thread, so nothing else is
            # mutating this row -- safe to mark it cancelled directly here.
            # A running job's own worker thread finalizes its status once
            # it notices the event, so only one side ever writes it.
            job.status = "cancelled"
            job.message = "Cancelled"
            job.updated_at = _utcnow()
            session.add(job)
            session.commit()
            session.refresh(job)
        return job

    def cancel_all_active(self) -> None:
        with Session(engine) as session:
            active = session.exec(
                select(Job).where(col(Job.status).in_(["pending", "running"]))
            ).all()
            for job in active:
                assert job.id is not None
                try:
                    self.cancel_job(session, job.id)
                except ValueError:
                    pass

    def shutdown(self) -> None:
        """Cancel any active jobs and wait briefly for them to stop, so a
        SIGTERM (or similar) doesn't kill the process mid-write."""
        self.cancel_all_active()
        futures = list(self._futures.values())
        if futures:
            _, not_done = wait_futures(futures, timeout=self._SHUTDOWN_TIMEOUT)
            if not_done:
                logger.warning(
                    "shutdown: %d job(s) did not stop within %.0fs",
                    len(not_done),
                    self._SHUTDOWN_TIMEOUT,
                )
        self._executor.shutdown(wait=False, cancel_futures=True)

    def run_due_schedules(self) -> None:
        now = _utcnow()
        with Session(engine) as session:
            due = session.exec(
                select(Source).where(
                    Source.schedule_enabled == True,  # noqa: E712
                    col(Source.next_run_at) <= now,
                )
            ).all()
            for source in due:
                assert source.schedule_cron is not None
                job = self.create_job(
                    session,
                    JobCreate(
                        source_name=source.name,
                        dry_run=False,
                        write_mode="fix",
                    ),
                    skip_if_running=True,
                )
                if job is not None:
                    source.last_run_at = now
                else:
                    logger.info(
                        "skipping scheduled sync for %s: a job is already running",
                        source.name,
                    )
                source.next_run_at = _compute_next_run(source.schedule_cron, base=now)
                source.updated_at = now
                session.add(source)
                session.commit()

    def get_job(self, session: Session, job_id: str) -> Job | None:
        return session.get(Job, job_id)

    def list_jobs(self, session: Session) -> list[Job]:
        statement = select(Job).order_by(col(Job.created_at).desc())
        return list(session.exec(statement).all())

    def read_log(self, job_id: str | None = None) -> str:
        log_path = Path(settings.LOG_FILE)
        if not log_path.is_file():
            return ""
        lines = log_path.read_text().splitlines()
        if job_id is not None:
            marker = f"[job {job_id}]"
            lines = [line for line in lines if marker in line]
        else:
            lines = lines[-MAX_LOG_LINES:]
        return "\n".join(lines)

    def _update_job(self, job_id: str, **fields: Any) -> None:
        with Session(engine) as session:
            job = session.get(Job, job_id)
            if not job:
                return
            for k, v in fields.items():
                setattr(job, k, v)
            job.updated_at = _utcnow()
            session.add(job)
            session.commit()

    def _cleanup_job(self, job_id: str) -> None:
        self._cancel_events.pop(job_id, None)
        self._futures.pop(job_id, None)

    def _run_job(self, job_id: str) -> None:
        # Falls back to a fresh (never-set) Event if this job's entry was
        # somehow already cleaned up, so the checks below are always safe.
        cancel_event = self._cancel_events.get(job_id, threading.Event())
        if cancel_event.is_set():
            # Cancelled while still queued behind another job; the worker
            # never got a chance to touch it.
            self._update_job(job_id, status="cancelled", message="Cancelled")
            self._cleanup_job(job_id)
            return

        self._update_job(job_id, status="running", message="Running")
        try:
            with Session(engine) as session:
                job = session.get(Job, job_id)
                if not job:
                    return
                logger.info("[job %s] started: source=%s", job_id, job.source_name)
                cfg = self.get_source(session, job.source_name)
                if not cfg:
                    self._update_job(job_id, status="failed", message="Source missing")
                    return

                # snapshot values for the worker thread
                source_type = cfg.type
                base_url = cfg.base_url
                token = cfg.token
                user_id = cfg.user_id
                path_mappings = [
                    (m.remote_path, m.local_path) for m in cfg.path_mappings
                ]
                library_id = job.library_id
                dry_run = job.dry_run
                # write_mode is validated to one of WriteMode's values by
                # JobCreate at job-creation time; the DB column is a plain str.
                write_mode = cast(WriteMode, job.write_mode)

            if source_type == "plex":
                self._run_plex(
                    job_id,
                    base_url,
                    token,
                    library_id,
                    dry_run,
                    write_mode,
                    path_mappings,
                    cancel_event,
                )
            else:
                self._run_jellyfin(
                    job_id,
                    base_url,
                    token,
                    user_id,
                    library_id,
                    dry_run,
                    write_mode,
                    path_mappings,
                    cancel_event,
                )
            self._update_job(
                job_id,
                status="cancelled" if cancel_event.is_set() else "completed",
                message="Cancelled" if cancel_event.is_set() else "Done",
            )
        except Exception as e:
            self._update_job(job_id, status="failed", message=str(e))
        finally:
            self._cleanup_job(job_id)
            with Session(engine) as session:
                job = session.get(Job, job_id)
                if job:
                    logger.info(
                        "[job %s] finished: status=%s written=%d skipped=%d errors=%d",
                        job_id,
                        job.status,
                        job.written,
                        job.skipped,
                        job.errors,
                    )

    def _bump(self, job_id: str, **deltas: int) -> None:
        """Increment counters safely in a short transaction."""
        with Session(engine) as session:
            job = session.get(Job, job_id)
            if not job:
                return
            for k, v in deltas.items():
                setattr(job, k, getattr(job, k) + v)
            job.updated_at = _utcnow()
            session.add(job)
            session.commit()

    def _run_plex(
        self,
        job_id: str,
        base_url: str,
        token: str,
        library_id: str | None,
        dry_run: bool,
        write_mode: WriteMode,
        path_mappings: list[tuple[str, str]],
        cancel_event: threading.Event,
    ) -> None:
        svc = PlexService(base_url, token)
        tracks = list(svc.iter_tracks(library_id))
        self._update_job(job_id, total=len(tracks))

        for track in tracks:
            if cancel_event.is_set():
                break
            try:
                info = svc.get_track_info(track)
                self._process_track(job_id, info, dry_run, write_mode, path_mappings)
            except Exception as e:
                self._bump(job_id, processed=1, errors=1)
                logger.warning("[job %s] error (track fetch failed): %s", job_id, e)

    def _run_jellyfin(
        self,
        job_id: str,
        base_url: str,
        token: str,
        user_id: str | None,
        library_id: str | None,
        dry_run: bool,
        write_mode: WriteMode,
        path_mappings: list[tuple[str, str]],
        cancel_event: threading.Event,
    ) -> None:
        svc = JellyfinService(base_url, token, user_id=user_id)
        try:
            items = list(svc.iter_audio_items(library_id))
            self._update_job(job_id, total=len(items))
            for item in items:
                if cancel_event.is_set():
                    break
                try:
                    info = svc.get_track_info(item)
                    self._process_track(job_id, info, dry_run, write_mode, path_mappings)
                except Exception as e:
                    self._bump(job_id, processed=1, errors=1)
                    logger.warning("[job %s] error (track fetch failed): %s", job_id, e)
        finally:
            svc.close()

    def _process_track(
        self,
        job_id: str,
        info: TrackInfo,
        dry_run: bool,
        write_mode: WriteMode,
        path_mappings: list[tuple[str, str]],
    ) -> None:
        self._bump(job_id, processed=1)
        if not info.path or not info.loudness:
            self._bump(job_id, skipped=1)
            logger.info(
                "[job %s] skipped %s: missing path or loudness data",
                job_id,
                info.path or info.title,
            )
            return
        mapped_path = _remap_path(info.path, path_mappings)
        result = self._tagger.write_replaygain(
            mapped_path,
            info.loudness,
            mode=write_mode,
            dry_run=dry_run,
        )
        if result.success:
            if "Skipped" in result.message:
                self._bump(job_id, skipped=1)
                logger.info(
                    "[job %s] skipped %s: %s", job_id, mapped_path, result.message
                )
            else:
                self._bump(job_id, written=1)
        else:
            self._bump(job_id, errors=1)
            logger.warning("[job %s] error %s: %s", job_id, mapped_path, result.message)


job_manager = JobManager()
