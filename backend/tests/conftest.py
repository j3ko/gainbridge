import logging

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from starlette.testclient import TestClient

from app.core.db import get_session
from app.main import app
from app.services import jobs as jobs_module

# Importing app.main runs setup_logging(), which sets propagate=False on the
# "app" logger (so Uvicorn's own noisy reload logging doesn't share its file
# in production). That would silently break every existing caplog-based test
# here, since caplog listens on the root logger and relies on propagation to
# reach it.
logging.getLogger("app").propagate = True


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(test_engine, monkeypatch):
    """A TestClient wired to an isolated in-memory database.

    Not entered as `with TestClient(app) as client`, so FastAPI's lifespan
    (real migrations, the infinite scheduler loop) never runs -- routes
    don't need it, they get everything through dependency injection or
    module-level globals already set up at import time.
    """

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    # create_job() hands work to a background thread that opens its own
    # Session(engine) against the *global* engine, not the request-scoped
    # one above -- point it at the same in-memory db and stub the executor
    # so no real background thread ever touches it during a route test.
    monkeypatch.setattr(jobs_module, "engine", test_engine)
    monkeypatch.setattr(
        jobs_module.job_manager._executor, "submit", lambda *a, **kw: None
    )

    app.dependency_overrides[get_session] = override_get_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_session, None)
