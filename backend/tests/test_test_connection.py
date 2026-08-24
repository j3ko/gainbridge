import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import Source
from app.services import jobs as jobs_module
from app.services.jobs import JobManager


@pytest.fixture
def manager(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(jobs_module, "engine", engine)
    manager = JobManager()
    monkeypatch.setattr(manager._executor, "submit", lambda *a, **kw: None)
    with Session(engine) as session:
        yield manager, session


class _FakePlexService:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token

    def test_connection(self):
        return {"ok": True, "server_name": "My Plex", "version": "1.0"}


class _FakeJellyfinService:
    def __init__(self, base_url, token, user_id=None):
        self.base_url = base_url
        self.token = token
        self.user_id = user_id
        self.closed = False

    def test_connection(self):
        return {"ok": True, "server_name": "My Jellyfin", "version": "2.0"}

    def close(self):
        self.closed = True


def test_test_connection_dispatches_to_plex(monkeypatch):
    monkeypatch.setattr(jobs_module, "PlexService", _FakePlexService)
    manager = JobManager()
    result = manager.test_connection("plex", "http://x", "t")
    assert result == {"ok": True, "server_name": "My Plex", "version": "1.0"}


def test_test_connection_dispatches_to_jellyfin_and_closes(monkeypatch):
    services = []

    def factory(base_url, token, user_id=None):
        svc = _FakeJellyfinService(base_url, token, user_id)
        services.append(svc)
        return svc

    monkeypatch.setattr(jobs_module, "JellyfinService", factory)
    manager = JobManager()
    result = manager.test_connection("jellyfin", "http://y", "k", "uid")
    assert result == {"ok": True, "server_name": "My Jellyfin", "version": "2.0"}
    assert services[0].closed is True


def test_test_source_looks_up_by_name_then_delegates(manager, monkeypatch):
    manager, session = manager
    monkeypatch.setattr(jobs_module, "PlexService", _FakePlexService)
    session.add(Source(name="lib", type="plex", base_url="http://x", token="t"))
    session.commit()

    result = manager.test_source(session, "lib")
    assert result == {"ok": True, "server_name": "My Plex", "version": "1.0"}


def test_test_source_raises_for_unknown_name(manager):
    manager, session = manager
    with pytest.raises(KeyError):
        manager.test_source(session, "missing")
