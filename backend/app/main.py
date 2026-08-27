import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.log_rotation import rotate_log_if_needed
from app.core.logging_config import setup_logging
from app.core.migrations import run_migrations
from app.services.jobs import job_manager

setup_logging()
logger = logging.getLogger(__name__)


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)


async def _scheduler_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(job_manager.run_due_schedules)
            await asyncio.to_thread(job_manager.prune_old_jobs)
            await asyncio.to_thread(rotate_log_if_needed)
        except Exception:
            logger.exception("scheduler tick failed")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    run_migrations()
    task = asyncio.create_task(_scheduler_loop())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    await asyncio.to_thread(job_manager.shutdown)


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

# Serves the built frontend when bundled alongside the backend in the
# published single-image release; absent (and a no-op) in local dev, where
# the frontend runs as its own container/dev server.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", tags=["spa"], include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:  # noqa: ARG001
        return FileResponse(STATIC_DIR / "index.html")
