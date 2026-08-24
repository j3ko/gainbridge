from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import SessionDep
from app.models import ScheduleUpdate, Source, SourceCreate, SourcePublic
from app.schemas.gain import LibraryInfo
from app.services.jellyfin import JellyfinService
from app.services.jobs import job_manager
from app.services.plex import PlexService

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/", response_model=list[SourcePublic])
def list_sources(session: SessionDep) -> list[Source]:
    return job_manager.list_sources(session)


@router.post("/", response_model=SourcePublic)
def add_source(session: SessionDep, body: SourceCreate) -> Source:
    return job_manager.add_source(session, body)


@router.delete("/{name}")
def delete_source(session: SessionDep, name: str) -> dict[str, bool]:
    if not job_manager.delete_source(session, name):
        raise HTTPException(404, "Source not found")
    return {"ok": True}


@router.put("/{name}/schedule", response_model=SourcePublic)
def set_schedule(session: SessionDep, name: str, body: ScheduleUpdate) -> Source:
    try:
        return job_manager.set_schedule(
            session, name, body.schedule_cron, body.schedule_enabled
        )
    except KeyError:
        raise HTTPException(404, "Source not found")
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.delete("/{name}/schedule", response_model=SourcePublic)
def clear_schedule(session: SessionDep, name: str) -> Source:
    try:
        return job_manager.clear_schedule(session, name)
    except KeyError:
        raise HTTPException(404, "Source not found")


@router.post("/{name}/test")
def test_source(session: SessionDep, name: str) -> dict[str, Any]:
    try:
        return job_manager.test_source(session, name)
    except KeyError:
        raise HTTPException(404, "Source not found")
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/{name}/libraries", response_model=list[LibraryInfo])
def list_libraries(session: SessionDep, name: str) -> list[LibraryInfo]:
    cfg = job_manager.get_source(session, name)
    if not cfg:
        raise HTTPException(404, "Source not found")
    if cfg.type == "plex":
        return PlexService(cfg.base_url, cfg.token).get_music_libraries()
    svc = JellyfinService(cfg.base_url, cfg.token, user_id=cfg.user_id)
    try:
        return svc.get_music_libraries()
    finally:
        svc.close()
