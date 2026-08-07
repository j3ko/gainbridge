from fastapi import APIRouter, HTTPException
from app.schemas.gain import SourceConfig, LibraryInfo
from app.services.jobs import job_manager
from app.services.plex import PlexService
from app.services.jellyfin import JellyfinService
from app.schemas.gain import SourceType

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/", response_model=list[SourceConfig])
def list_sources():
    return job_manager.list_sources()


@router.post("/", response_model=SourceConfig)
def add_source(cfg: SourceConfig):
    return job_manager.add_source(cfg)


@router.post("/{name}/test")
def test_source(name: str):
    try:
        return job_manager.test_source(name)
    except KeyError:
        raise HTTPException(404, "Source not found")
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/{name}/libraries", response_model=list[LibraryInfo])
def list_libraries(name: str):
    cfg = job_manager.get_source(name)
    if not cfg:
        raise HTTPException(404, "Source not found")
    if cfg.type == SourceType.plex:
        return PlexService(cfg.base_url, cfg.token).get_music_libraries()
    svc = JellyfinService(cfg.base_url, cfg.token)
    try:
        return svc.get_music_libraries()
    finally:
        svc.close()