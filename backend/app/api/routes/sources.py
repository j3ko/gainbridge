from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import SessionDep
from app.models import (
    PlexPinCreate,
    PlexPinStatus,
    PlexServerOption,
    ScheduleUpdate,
    Source,
    SourceCreate,
    SourcePublic,
    SourceTestRequest,
)
from app.schemas.gain import LibraryInfo
from app.services import plex_oauth
from app.services.jobs import job_manager

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/", response_model=list[SourcePublic])
def list_sources(session: SessionDep) -> list[Source]:
    return job_manager.list_sources(session)


@router.post("/", response_model=SourcePublic)
def add_source(session: SessionDep, body: SourceCreate) -> Source:
    try:
        return job_manager.add_source(session, body)
    except ValueError as e:
        raise HTTPException(422, str(e))


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


@router.post("/test")
def test_connection(body: SourceTestRequest) -> dict[str, Any]:
    try:
        return job_manager.test_connection(
            body.type, body.base_url, body.token, body.user_id
        )
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/libraries", response_model=list[LibraryInfo])
def list_libraries_for_connection(body: SourceTestRequest) -> list[LibraryInfo]:
    try:
        return job_manager.get_libraries(
            body.type, body.base_url, body.token, body.user_id
        )
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/plex/oauth/pin", response_model=PlexPinCreate)
def create_plex_pin() -> dict[str, Any]:
    return plex_oauth.create_pin()


@router.get("/plex/oauth/pin/{pin_id}", response_model=PlexPinStatus)
def check_plex_pin(pin_id: str) -> dict[str, Any]:
    try:
        return plex_oauth.check_pin(pin_id)
    except KeyError:
        raise HTTPException(404, "Pin not found or expired")


@router.get("/plex/oauth/servers", response_model=list[PlexServerOption])
def list_plex_servers(token: str) -> list[dict[str, Any]]:
    try:
        return plex_oauth.list_servers(token)
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/{name}/libraries", response_model=list[LibraryInfo])
def list_libraries(session: SessionDep, name: str) -> list[LibraryInfo]:
    cfg = job_manager.get_source(session, name)
    if not cfg:
        raise HTTPException(404, "Source not found")
    return job_manager.get_libraries(cfg.type, cfg.base_url, cfg.token, cfg.user_id)
