import fcntl
from pathlib import Path

from app.core.log_rotation import rotate_log_if_needed


def _configure(monkeypatch, log_file, max_bytes=10, backup_count=3):
    monkeypatch.setattr("app.core.log_rotation.settings.LOG_FILE", str(log_file))
    monkeypatch.setattr("app.core.log_rotation.settings.LOG_MAX_BYTES", max_bytes)
    monkeypatch.setattr("app.core.log_rotation.settings.LOG_BACKUP_COUNT", backup_count)


def test_missing_file_is_a_no_op(tmp_path, monkeypatch):
    _configure(monkeypatch, tmp_path / "app.log")
    rotate_log_if_needed()  # should not raise


def test_small_file_is_not_rotated(tmp_path, monkeypatch):
    log_file = tmp_path / "app.log"
    log_file.write_text("x")
    _configure(monkeypatch, log_file, max_bytes=1000)

    rotate_log_if_needed()

    assert log_file.exists()
    assert not (tmp_path / "app.log.1").exists()


def test_stat_oserror_is_a_no_op(tmp_path, monkeypatch):
    log_file = tmp_path / "app.log"
    log_file.write_text("x" * 100)
    _configure(monkeypatch, log_file, max_bytes=1)

    def raise_oserror(_self):
        raise OSError("boom")

    monkeypatch.setattr(Path, "stat", raise_oserror)

    rotate_log_if_needed()  # should not raise


def test_rotates_and_shifts_existing_backups(tmp_path, monkeypatch):
    log_file = tmp_path / "app.log"
    log_file.write_text("x" * 100)
    (tmp_path / "app.log.1").write_text("oldest kept")
    (tmp_path / "app.log.2").write_text("newest backup")
    _configure(monkeypatch, log_file, max_bytes=10, backup_count=3)

    rotate_log_if_needed()

    assert not log_file.exists()
    assert (tmp_path / "app.log.1").read_text() == "x" * 100
    assert (tmp_path / "app.log.2").read_text() == "oldest kept"
    assert (tmp_path / "app.log.3").read_text() == "newest backup"


def test_lock_contention_skips_rotation(tmp_path, monkeypatch):
    log_file = tmp_path / "app.log"
    log_file.write_text("x" * 100)
    _configure(monkeypatch, log_file, max_bytes=10)

    lock_path = tmp_path / "app.log.lock"
    with open(lock_path, "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)

        rotate_log_if_needed()

        assert log_file.exists()
        assert not (tmp_path / "app.log.1").exists()
