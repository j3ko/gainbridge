import logging
from logging.handlers import WatchedFileHandler

import pytest

from app.core.logging_config import setup_logging


@pytest.fixture(autouse=True)
def _restore_app_logger_propagation():
    # setup_logging() sets propagate=False in production so Uvicorn's own
    # reload logging doesn't share this file; other tests' caplog-based
    # assertions rely on propagation reaching the root logger, so undo it
    # once this file is done exercising the real function.
    yield
    logging.getLogger("app").propagate = True


def test_setup_logging_attaches_file_and_stream_handlers(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.core.logging_config.settings.LOG_FILE", str(tmp_path / "app.log")
    )

    setup_logging()

    logger = logging.getLogger("app")
    assert logger.level == logging.INFO
    assert logger.propagate is False
    assert len(logger.handlers) == 2
    assert isinstance(logger.handlers[0], WatchedFileHandler)
    assert isinstance(logger.handlers[1], logging.StreamHandler)


def test_setup_logging_clears_previous_handlers(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.core.logging_config.settings.LOG_FILE", str(tmp_path / "app.log")
    )

    setup_logging()
    setup_logging()

    logger = logging.getLogger("app")
    assert len(logger.handlers) == 2
