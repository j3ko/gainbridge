import logging
from logging.handlers import WatchedFileHandler

from app.core.config import settings


def setup_logging() -> None:
    """Configure the "app" logger to write to settings.LOG_FILE and stderr.

    Scoped to "app" (the parent of every app.* module logger) rather than
    the root logger, so Uvicorn's own request/reload logging - in particular
    watchfiles' extremely chatty "N changes detected" lines under
    `fastapi dev`'s --reload - never lands in the same file as job skip/error
    lines and drowns them out.

    Uses WatchedFileHandler (not RotatingFileHandler) because the app runs
    as multiple worker processes appending to the same file; rotation is
    left entirely to an external tool like logrotate, and WatchedFileHandler
    is the handler designed to cooperate with that (it reopens the file if
    logrotate renames/recreates it out from under us).
    """
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False
    app_logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    file_handler = WatchedFileHandler(settings.LOG_FILE)
    file_handler.setFormatter(formatter)
    app_logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    app_logger.addHandler(stream_handler)
