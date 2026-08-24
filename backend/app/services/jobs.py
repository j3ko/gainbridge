from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from croniter import croniter
from sqlmodel import Session, col, select

from app.core.db import engine
from app.models import Job, JobCreate, PathMapping, Source, SourceCreate
from app.schemas.gain import TrackInfo
from app.services.jellyfin import JellyfinService
from app.services.plex import PlexService
from app.services.tagger import TaggerService

logger = logging.getLogger(__name__)


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
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._tagger = TaggerService()

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
        if cfg.type == "plex":
            return PlexService(cfg.base_url, cfg.token).test_connection()
        svc = JellyfinService(cfg.base_url, cfg.token, user_id=cfg.user_id)
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
        job = Job(
            id=job_id,
            source_name=body.source_name,
            library_id=body.library_id,
            dry_run=body.dry_run,
            overwrite_existing=body.overwrite_existing,
            status="pending",
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        self._executor.submit(self._run_job, job_id)
        return job

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
                        overwrite_existing=False,
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

    def _run_job(self, job_id: str) -> None:
        self._update_job(job_id, status="running", message="Running")

        with Session(engine) as session:
            job = session.get(Job, job_id)
            if not job:
                return
            cfg = self.get_source(session, job.source_name)
            if not cfg:
                self._update_job(job_id, status="failed", message="Source missing")
                return

            # snapshot values for the worker thread
            source_type = cfg.type
            base_url = cfg.base_url
            token = cfg.token
            user_id = cfg.user_id
            path_mappings = [(m.remote_path, m.local_path) for m in cfg.path_mappings]
            library_id = job.library_id
            dry_run = job.dry_run
            overwrite = job.overwrite_existing

        try:
            if source_type == "plex":
                self._run_plex(
                    job_id,
                    base_url,
                    token,
                    library_id,
                    dry_run,
                    overwrite,
                    path_mappings,
                )
            else:
                self._run_jellyfin(
                    job_id,
                    base_url,
                    token,
                    user_id,
                    library_id,
                    dry_run,
                    overwrite,
                    path_mappings,
                )
            self._update_job(job_id, status="completed", message="Done")
        except Exception as e:
            self._update_job(job_id, status="failed", message=str(e))

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
        overwrite: bool,
        path_mappings: list[tuple[str, str]],
    ) -> None:
        svc = PlexService(base_url, token)
        tracks = list(svc.iter_tracks(library_id))
        self._update_job(job_id, total=len(tracks))

        for track in tracks:
            info = svc.get_track_info(track)
            self._process_track(job_id, info, dry_run, overwrite, path_mappings)

    def _run_jellyfin(
        self,
        job_id: str,
        base_url: str,
        token: str,
        user_id: str | None,
        library_id: str | None,
        dry_run: bool,
        overwrite: bool,
        path_mappings: list[tuple[str, str]],
    ) -> None:
        svc = JellyfinService(base_url, token, user_id=user_id)
        try:
            items = list(svc.iter_audio_items(library_id))
            self._update_job(job_id, total=len(items))
            for item in items:
                info = svc.get_track_info(item)
                self._process_track(job_id, info, dry_run, overwrite, path_mappings)
        finally:
            svc.close()

    def _process_track(
        self,
        job_id: str,
        info: TrackInfo,
        dry_run: bool,
        overwrite: bool,
        path_mappings: list[tuple[str, str]],
    ) -> None:
        self._bump(job_id, processed=1)
        if not info.path or not info.loudness:
            self._bump(job_id, skipped=1)
            return
        mapped_path = _remap_path(info.path, path_mappings)
        result = self._tagger.write_replaygain(
            mapped_path,
            info.loudness,
            overwrite=overwrite,
            dry_run=dry_run,
        )
        if result.success:
            if "Skipped" in result.message:
                self._bump(job_id, skipped=1)
            else:
                self._bump(job_id, written=1)
        else:
            self._bump(job_id, errors=1)


job_manager = JobManager()
