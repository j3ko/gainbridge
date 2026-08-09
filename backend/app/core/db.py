from sqlmodel import Session, create_engine, SQLModel
from app.core.config import settings

connect_args = {"check_same_thread": False}  # required for SQLite + FastAPI
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    connect_args=connect_args,
)


def init_db() -> None:
    # Import models so metadata is registered
    from app.models import Source, Job  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session