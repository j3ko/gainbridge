import logging

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect

from app.core.db import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def stamp_if_legacy(db_engine: Engine) -> None:
    """Mark pre-Alembic databases as already up to date.

    Before Alembic was wired into container startup, the schema was created
    by SQLModel.metadata.create_all(), which always matches the current
    models. Such a database has its tables but no alembic_version - running
    `alembic upgrade head` against it would try to recreate tables that
    already exist. Stamp it as head instead so upgrade becomes a no-op.
    """
    tables = inspect(db_engine).get_table_names()
    if "source" in tables and "alembic_version" not in tables:
        logger.info("Pre-Alembic database detected, stamping as up to date")
        command.stamp(Config("alembic.ini"), "head")


def main() -> None:
    stamp_if_legacy(engine)


if __name__ == "__main__":  # pragma: no cover
    main()
