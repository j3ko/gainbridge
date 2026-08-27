import fcntl
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import settings
from app.core.db import engine
from app.stamp_legacy_db import stamp_if_legacy

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """Apply Alembic migrations, safe to call from every worker process.

    The app runs single-process by default, but `fastapi run --workers N`
    would start N separate processes that each run the app lifespan
    independently. Without a lock, all of them would race to apply
    migrations against the same SQLite file on first start. The file lock
    serializes them: one worker migrates while the rest block, then proceed
    once it's done (upgrading an already-current DB is a no-op) - kept as a
    safety net in case this ever runs with more than one worker again.
    """
    lock_path = Path(settings.SQLITE_DB_FILE).parent / ".migrations.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            stamp_if_legacy(engine)
            command.upgrade(Config("alembic.ini"), "head")
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
