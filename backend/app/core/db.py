from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import settings

connect_args = {"check_same_thread": False}  # required for SQLite + FastAPI
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    connect_args=connect_args,
)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
