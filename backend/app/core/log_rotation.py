import fcntl
import logging
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def rotate_log_if_needed() -> None:
    """Rotate settings.LOG_FILE once it exceeds LOG_MAX_BYTES.

    The app runs as multiple worker processes appending to the same log
    file (see logging_config.py), so rotation can't just be a size check in
    each process's handler -- they'd race to rename the file. Instead this
    takes a non-blocking flock on a sibling lock file: whichever process
    (or scheduler tick) gets there first does the rotation, everyone else
    is a no-op. WatchedFileHandler already watches for the log file being
    replaced out from under it and reopens a fresh one on its next write,
    which is exactly what a rename here does.
    """
    log_path = Path(settings.LOG_FILE)
    try:
        if not log_path.is_file() or log_path.stat().st_size < settings.LOG_MAX_BYTES:
            return
    except OSError:
        return

    lock_path = log_path.with_name(log_path.name + ".lock")
    with open(lock_path, "w") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return  # another process is already rotating

        try:
            # Re-check: another process may have rotated while we waited.
            if (
                not log_path.is_file()
                or log_path.stat().st_size < settings.LOG_MAX_BYTES
            ):
                return
            for i in range(settings.LOG_BACKUP_COUNT - 1, 0, -1):
                src = log_path.with_name(f"{log_path.name}.{i}")
                dst = log_path.with_name(f"{log_path.name}.{i + 1}")
                if src.is_file():
                    src.replace(dst)
            log_path.replace(log_path.with_name(f"{log_path.name}.1"))
            logger.info(
                "rotated %s (exceeded %d bytes)", log_path, settings.LOG_MAX_BYTES
            )
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
