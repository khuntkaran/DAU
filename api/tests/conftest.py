"""A fresh SQLite database and API client per test, with known settings."""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from api.app import models
from api.app.config import Settings, get_settings
from api.app.db import Base, SessionFactory, get_session_factory, make_engine
from api.app.enums import Role
from api.app.llm.gateway import Gateway, get_gateway
from api.app.llm.providers.fake import FakeProvider
from api.app.llm.ratelimit import RateLimiter
from api.app.main import app
from api.app.services.auth import issue_token

# Explicit values win over .env, so tests never see real keys or call a real provider.
TEST_SETTINGS = Settings(
    database_url="sqlite://",
    jwt_secret="test-secret-that-is-long-enough-for-hs256",
    demo_otp="123456",
    ai_provider="fake",
    gemini_api_key=None,
    groq_api_key=None,
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
def factory(engine: Engine) -> SessionFactory:
    return sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def fake_ai() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def gateway(fake_ai: FakeProvider) -> Gateway:
    return Gateway([fake_ai], RateLimiter({}), sleep=lambda _: None)


@pytest.fixture
def client(factory: SessionFactory, settings: Settings, gateway: Gateway) -> Iterator[TestClient]:
    app.dependency_overrides[get_session_factory] = lambda: factory
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_gateway] = lambda: gateway
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
