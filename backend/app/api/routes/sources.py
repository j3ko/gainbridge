from fastapi import APIRouter, HTTPException
from app.api.deps import SessionDep
from app.models import SourceCreate, SourcePublic
from app.services.jobs import job_manager
from app.services.plex import PlexService
from app.services.jellyfin import JellyfinService
from app.schemas.gain import LibraryInfo

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/", response_model=list[SourcePublic])
def list_sources(session: SessionDep):
    return job_manager.list_sources(session)


@router.post("/", response_model=SourcePublic)
def add_source(session: SessionDep, body: SourceCreate):
    return job_manager.add_source(session, body)


@router.delete("/{name}")
def delete_source(session: SessionDep, name: str):
    if not job_manager.delete_source(session, name):
        raise HTTPException(404, "Source not found")
    return {"ok": True}


@router.post("/{name}/test")
def test_source(session: SessionDep, name: str):
    try:
        return job_manager.test_source(session, name)
    except KeyError:
        raise HTTPException(404, "Source not found")
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/{name}/libraries", response_model=list[LibraryInfo])
def list_libraries(session: SessionDep, name: str):
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