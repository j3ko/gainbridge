from unittest.mock import MagicMock, patch

from app.core.migrations import run_migrations


def test_run_migrations_stamps_and_upgrades(tmp_path):
    fake_settings = MagicMock(SQLITE_DB_FILE=str(tmp_path / "gainbridge.db"))

    with (
        patch("app.core.migrations.settings", fake_settings),
        patch("app.core.migrations.stamp_if_legacy") as stamp_mock,
        patch("app.core.migrations.command") as command_mock,
    ):
        run_migrations()

        stamp_mock.assert_called_once()
        command_mock.upgrade.assert_called_once()

    assert (tmp_path / ".migrations.lock").exists()
