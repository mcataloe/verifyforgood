from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class CustomerAccountsBase(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def build_customer_accounts_engine(
    database_url: str,
    *,
    echo: bool = False,
    future: bool = True,
) -> Engine:
    return create_engine(database_url, echo=echo, future=future)


def build_customer_accounts_session_factory(
    bind: Engine | str,
    *,
    echo: bool = False,
) -> sessionmaker[Session]:
    engine = bind if isinstance(bind, Engine) else build_customer_accounts_engine(bind, echo=echo)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


@contextmanager
def customer_accounts_session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
