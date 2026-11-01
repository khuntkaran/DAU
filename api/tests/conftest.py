"""A fresh SQLite database and API client per test, with known settings."""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from api.app import models
from api.app.config import Settings, get_settings
from api.app.db import Base, get_db, make_engine
from api.app.enums import Role
from api.app.main import app
from api.app.services.auth import issue_token

TEST_SETTINGS = Settings(
    database_url="sqlite://",
    jwt_secret="test-secret-that-is-long-enough-for-hs256",
    demo_otp="123456",
)


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    with Session(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def settings() -> Settings:
    return TEST_SETTINGS.model_copy()


@pytest.fixture
def client(engine: Engine, settings: Settings) -> Iterator[TestClient]:
    factory = sessionmaker(engine, expire_on_commit=False)

    def _db() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


MakeUser = Callable[..., models.User]


@pytest.fixture
def make_user(db: Session) -> MakeUser:
    count = 0

    def _make(role: Role = Role.HOUSEHOLD, *, is_active: bool = True) -> models.User:
        nonlocal count
        count += 1
        user = models.User(
            role=role,
            full_name=f"{role} {count}",
            phone=f"+9190000099{count:02d}",
            is_active=is_active,
        )
        db.add(user)
        if role == Role.VENDOR:
            # Signing up as a vendor always creates the profile, so test vendors have one too.
            db.add(models.Vendor(user=user, company_name=f"Vendor {count}", service_radius_km=50))
        db.commit()
        return user

    return _make


@pytest.fixture
def auth(settings: Settings) -> Callable[[models.User], dict[str, str]]:
    def _headers(user: models.User) -> dict[str, str]:
        return {"Authorization": f"Bearer {issue_token(user, settings)}"}

    return _headers
