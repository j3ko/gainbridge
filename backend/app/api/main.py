from fastapi import APIRouter
from app.api.routes import utils, sources, jobs

api_router = APIRouter()
api_router.include_router(utils.router)
api_router.include_router(sources.router)
api_router.include_router(jobs.router)