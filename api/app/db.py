"""Engine, sessions and the declarative base.

The same models run on SQLite for the demo and on PostgreSQL in production; only
`DATABASE_URL` changes. Column types are chosen to be portable for that reason.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import JSON, DateTime, Dialect, Engine, MetaData, create_engine, event
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from api.app.config import get_settings

# Stable constraint names, so Alembic can diff them once production moves to PostgreSQL.
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

JsonDoc = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


def str_enum(enum: type[StrEnum]) -> SAEnum:
    """Stores the lowercase value as text, so no database-specific enum type is needed."""
    return SAEnum(
        enum,
        native_enum=False,
        create_constraint=False,
        length=32,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )


def utcnow() -> datetime:
    return datetime.now(UTC)


class UtcDateTime(TypeDecorator[datetime]):
    """Always hands back an aware UTC datetime. SQLite drops the zone; PostgreSQL keeps it."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamps must carry a time zone")
        return value.astimezone(UTC) if value is not None else None

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def enable_sqlite_foreign_keys(dbapi_connection: Any, _: Any) -> None:
    # SQLite ignores foreign keys unless each connection asks for them.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False})
        event.listen(engine, "connect", enable_sqlite_foreign_keys)
        return engine
    return create_engine(url, pool_pre_ping=True)


@lru_cache
def get_engine() -> Engine:
    return make_engine(get_settings().database_url)


SessionFactory = sessionmaker[Session]


@lru_cache
def get_session_factory() -> SessionFactory:
    """Also handed to background jobs, which outlive the request's own session."""
    return sessionmaker(get_engine(), expire_on_commit=False)


def get_db(
    factory: Annotated[SessionFactory, Depends(get_session_factory)],
) -> Iterator[Session]:
    with factory() as session:
        yield session
