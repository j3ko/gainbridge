from sqlmodel import Session

from app.core.db import get_session


def test_get_session_yields_a_session():
    gen = get_session()
    session = next(gen)
    try:
        assert isinstance(session, Session)
    finally:
        gen.close()
