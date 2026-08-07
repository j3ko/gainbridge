from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from app.schemas.gain import (
    JobCreate,
    JobInfo,
    JobStatus,
    SourceConfig,
    SourceType,
)
from app.services.plex import PlexService
from app.services.jellyfin import JellyfinService
from app.services.tagger import TaggerService


class JobManager:
    """In-memory job runner (good enough for v1)."""

    def __init__(self):
        self._jobs: dict[str, JobInfo] = {}
        self._sources: dict[str, SourceConfig] = {}
        self._executor = ThreadPoolExecutor(max_workers=1)  # sequential writes are safer
        self._tagger = TaggerService()

    # ----- sources -----
    def add_source(self, cfg: SourceConfig) -> SourceConfig:
        self._sources[cfg.name] = cfg
        return cfg

    def list_sources(self) -> list[SourceConfig]:
        return list(self._sources.values())

    def get_source(self, name: str) -> Optional[SourceConfig]:
        return self._sources.get(name)

    def test_source(self, name: str) -> dict:
        cfg = self._sources[name]
        if cfg.type == SourceType.plex:
            svc = PlexService(cfg.base_url, cfg.token)
            return svc.test_connection()
        else:
            svc = JellyfinService(cfg.base_url, cfg.token)
            try:
                return svc.test_connection()
            finally:
                svc.close()

    # ----- jobs -----
    def create_job(self, body: JobCreate) -> JobInfo:
        if body.source_name not in self._sources:
            raise ValueError(f"Unknown source: {body.source_name}")
        job = JobInfo(
            id=str(uuid.uuid4()),
            status=JobStatus.pending,
            source_name=body.source_name,
            dry_run=body.dry_run,
        )
        self._jobs[job.id] = job
        self._executor.submit(self._run_job, job.id, body)
        return job

    def get_job(self, job_id: str) -> Optional[JobInfo]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[JobInfo]:
        return list(self._jobs.values())

    def _run_job(self, job_id: str, body: JobCreate) -> None:
        job = self._jobs[job_id]
        job.status = JobStatus.running
        cfg = self._sources[body.source_name]

        try:
            if cfg.type == SourceType.plex:
                self._run_plex(job, cfg, body)
            else:
                self._run_jellyfin(job, cfg, body)
            job.status = JobStatus.completed
            job.message = "Done"
        except Exception as e:
            job.status = JobStatus.failed
            job.message = str(e)

    def _run_plex(self, job: JobInfo, cfg: SourceConfig, body: JobCreate) -> None:
        svc = PlexService(cfg.base_url, cfg.token)
        tracks = list(svc.iter_tracks(body.library_id))
        job.total = len(tracks)

        for track in tracks:
            info = svc.get_track_info(track)
            self._process_track(job, info, body.overwrite_existing)

    def _run_jellyfin(self, job: JobInfo, cfg: SourceConfig, body: JobCreate) -> None:
        svc = JellyfinService(cfg.base_url, cfg.token)
        try:
            items = list(svc.iter_audio_items(body.library_id))
            job.total = len(items)
            for item in items:
                info = svc.get_track_info(item)
                self._process_track(job, info, body.overwrite_existing)
        finally:
            svc.close()

    def _process_track(self, job: JobInfo, info, overwrite: bool) -> None:
        job.processed += 1
        if not info.path or not info.loudness:
            job.skipped += 1
            return
        result = self._tagger.write_replaygain(
            info.path,
            info.loudness,
            overwrite=overwrite,
            dry_run=job.dry_run,
        )
        if result.success:
            if "Skipped" in result.message:
                job.skipped += 1
            else:
                job.written += 1
        else:
            job.errors += 1


# Singleton used by API routes
job_manager = JobManager()