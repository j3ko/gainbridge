from unittest.mock import MagicMock, patch

from app.stamp_legacy_db import logger, stamp_if_legacy


def test_stamps_pre_alembic_database() -> None:
    engine_mock = MagicMock()

    with (
        patch(
            "app.stamp_legacy_db.inspect",
            return_value=MagicMock(get_table_names=lambda: ["source", "job"]),
        ),
        patch("app.stamp_legacy_db.command") as command_mock,
        patch.object(logger, "info"),
    ):
        stamp_if_legacy(engine_mock)

        command_mock.stamp.assert_called_once()


def test_skips_fresh_database() -> None:
    engine_mock = MagicMock()

    with (
        patch(
            "app.stamp_legacy_db.inspect",
            return_value=MagicMock(get_table_names=lambda: []),
        ),
        patch("app.stamp_legacy_db.command") as command_mock,
    ):
        stamp_if_legacy(engine_mock)

        command_mock.stamp.assert_not_called()


def test_skips_database_already_tracked_by_alembic() -> None:
    engine_mock = MagicMock()

    with (
        patch(
            "app.stamp_legacy_db.inspect",
            return_value=MagicMock(
                get_table_names=lambda: ["source", "job", "alembic_version"]
            ),
        ),
        patch("app.stamp_legacy_db.command") as command_mock,
    ):
        stamp_if_legacy(engine_mock)

        command_mock.stamp.assert_not_called()
