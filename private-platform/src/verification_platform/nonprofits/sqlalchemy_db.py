from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def build_nonprofit_engine(
    database_url: str,
    *,
    echo: bool = False,
    future: bool = True,
) -> Engine:
    return create_engine(database_url, echo=echo, future=future)


def build_nonprofit_session_factory(
    bind: Engine | str,
    *,
    echo: bool = False,
) -> sessionmaker[Session]:
    engine = bind if isinstance(bind, Engine) else build_nonprofit_engine(bind, echo=echo)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


@contextmanager
def nonprofit_session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
