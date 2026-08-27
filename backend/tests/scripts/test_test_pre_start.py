from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select
from tenacity import RetryError, stop_after_attempt

from app.tests_pre_start import init, logger, main


def test_init_successful_connection() -> None:
    engine_mock = MagicMock()

    session_mock = MagicMock()
    session_mock.__enter__.return_value = session_mock

    select1 = select(1)

    with (
        patch("app.tests_pre_start.Session", return_value=session_mock),
        patch("app.tests_pre_start.select", return_value=select1),
        patch.object(logger, "info"),
        patch.object(logger, "error"),
        patch.object(logger, "warn"),
    ):
        try:
            init(engine_mock)
            connection_successful = True
        except Exception:
            connection_successful = False

        assert connection_successful, (
            "The database connection should be successful and not raise an exception."
        )

        session_mock.exec.assert_called_once_with(select1)


def test_init_raises_and_logs_after_retries_exhausted() -> None:
    engine_mock = MagicMock()
    session_mock = MagicMock()
    session_mock.__enter__.return_value = session_mock
    session_mock.exec.side_effect = RuntimeError("db unreachable")

    original_stop = init.retry.stop
    init.retry.stop = stop_after_attempt(1)
    try:
        with (
            patch("app.tests_pre_start.Session", return_value=session_mock),
            patch.object(logger, "error") as error_mock,
        ):
            # tenacity's default (no reraise=True) wraps the exhausted
            # exception in a RetryError rather than propagating it as-is.
            with pytest.raises(RetryError):
                init(engine_mock)
            error_mock.assert_called_once()
    finally:
        init.retry.stop = original_stop


def test_main_initializes_using_the_module_engine() -> None:
    with (
        patch("app.tests_pre_start.init") as init_mock,
        patch.object(logger, "info"),
    ):
        main()
        init_mock.assert_called_once()
