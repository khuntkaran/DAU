"""Background AI jobs (work plan 4.1): queueing, reuse, running, failure, and polling."""

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app import models
from api.app.config import Settings
from api.app.db import SessionFactory
from api.app.enums import JobPriority, JobStatus, JobType, Role
from api.app.jobs import runner
from api.app.llm.base import Text
from api.app.llm.gateway import AiUnavailable, Gateway
from api.app.llm.providers.fake import FakeProvider
from api.tests.conftest import MakeUser

Auth = Callable[[models.User], dict[str, str]]


class Shade(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = "photo_assess"
    risk: str


@pytest.fixture
def chat_handler(monkeypatch: pytest.MonkeyPatch) -> list[uuid.UUID]:
    """A stand-in job type that asks the fake provider one question."""
    seen: list[uuid.UUID] = []

    def handle(ctx: runner.JobContext) -> dict[str, Any]:
        seen.append(ctx.job.id)
        result = ctx.gateway.generate(
            task="shade", system="s", parts=[Text("x")], schema=Shade, priority=ctx.job.priority
        )
        runner.record(ctx.job, result)
        return result.output.model_dump()

    monkeypatch.setitem(runner.HANDLERS, JobType.CHAT, handle)
    return seen


def _enqueue(db: Session, entity: uuid.UUID, payload: dict[str, Any], user: models.User) -> Any:
    job, run = runner.enqueue(
        db,
        job_type=JobType.CHAT,
        entity_type="test",
        entity_id=entity,
        payload=payload,
        prompt_version="v1",
        priority=JobPriority.HIGH,
        requested_by=user.id,
    )
    db.commit()
    return job, run


def test_a_queued_job_runs_and_stores_its_answer(
    db: Session,
    factory: SessionFactory,
    settings: Settings,
    gateway: Gateway,
    fake_ai: FakeProvider,
    make_user: MakeUser,
    chat_handler: list[uuid.UUID],
) -> None:
    fake_ai.scripts = {"shade": lambda parts: {"risk": "low"}}
    job, run = _enqueue(db, uuid.uuid4(), {"photo": "abc"}, make_user())
    assert (job.status, run) == (JobStatus.QUEUED, True)

    runner.run_job(job.id, factory, gateway, settings)

    db.expire_all()
    done = db.get(models.AiJob, job.id)
    assert done is not None
    assert done.status == JobStatus.SUCCEEDED
    assert done.output == {"kind": "photo_assess", "risk": "low"}
    assert (done.provider, done.attempts) == ("fake", 1)
    assert done.tokens_out is not None
    assert done.finished_at is not None


def test_the_same_input_for_the_same_row_is_one_job(
    db: Session, make_user: MakeUser, chat_handler: list[uuid.UUID]
) -> None:
    entity, user = uuid.uuid4(), make_user()
    first, _ = _enqueue(db, entity, {"photo": "abc"}, user)
    again, run = _enqueue(db, entity, {"photo": "abc"}, user)

    assert (again.id, run) == (first.id, False)


def test_a_finished_answer_is_reused_for_identical_input(
    db: Session,
    factory: SessionFactory,
    settings: Settings,
    gateway: Gateway,
    fake_ai: FakeProvider,
    make_user: MakeUser,
    chat_handler: list[uuid.UUID],
) -> None:
    fake_ai.scripts = {"shade": lambda parts: {"risk": "high"}}
    user = make_user()
    first, _ = _enqueue(db, uuid.uuid4(), {"photo": "same"}, user)
    runner.run_job(first.id, factory, gateway, settings)

    copy, run = _enqueue(db, uuid.uuid4(), {"photo": "same"}, user)

    assert run is False
    assert (copy.status, copy.provider) == (JobStatus.SUCCEEDED, "cache")
    assert copy.output == {"kind": "photo_assess", "risk": "high"}
    assert fake_ai.calls == ["shade"]


def test_a_changed_input_is_a_new_job(
    db: Session, make_user: MakeUser, chat_handler: list[uuid.UUID]
) -> None:
    entity, user = uuid.uuid4(), make_user()
    first, _ = _enqueue(db, entity, {"photo": "abc"}, user)
    second, run = _enqueue(db, entity, {"photo": "xyz"}, user)

    assert second.id != first.id
    assert run is True


def test_ai_being_down_fails_the_job_without_raising(
    db: Session,
    factory: SessionFactory,
    settings: Settings,
    make_user: MakeUser,
    chat_handler: list[uuid.UUID],
) -> None:
    class Down:
        def generate(self, **_: Any) -> Any:
            raise AiUnavailable("all providers down")

    job, _ = _enqueue(db, uuid.uuid4(), {"photo": "abc"}, make_user())

    runner.run_job(job.id, factory, Down(), settings)  # type: ignore[arg-type]

    db.expire_all()
    failed = db.get(models.AiJob, job.id)
    assert failed is not None
    assert failed.status == JobStatus.FAILED
    assert failed.error is not None
    assert failed.error.startswith("AI unavailable")


def test_a_crashing_handler_fails_the_job_with_a_safe_message(
    db: Session,
    factory: SessionFactory,
    settings: Settings,
    gateway: Gateway,
    make_user: MakeUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(ctx: runner.JobContext) -> dict[str, Any]:
        raise RuntimeError("secret stack detail")

    monkeypatch.setitem(runner.HANDLERS, JobType.CHAT, broken)
    job, _ = _enqueue(db, uuid.uuid4(), {}, make_user())

    runner.run_job(job.id, factory, gateway, settings)

    db.expire_all()
    failed = db.get(models.AiJob, job.id)
    assert failed is not None
    assert failed.status == JobStatus.FAILED
    assert failed.error is not None
    assert "secret" not in failed.error


def test_a_job_runs_only_once(
    db: Session,
    factory: SessionFactory,
    settings: Settings,
    gateway: Gateway,
    fake_ai: FakeProvider,
    make_user: MakeUser,
    chat_handler: list[uuid.UUID],
) -> None:
    fake_ai.scripts = {"shade": lambda parts: {"risk": "low"}}
    job, _ = _enqueue(db, uuid.uuid4(), {}, make_user())

    runner.run_job(job.id, factory, gateway, settings)
    runner.run_job(job.id, factory, gateway, settings)

    assert chat_handler == [job.id]


def test_a_job_with_no_handler_fails_cleanly(
    db: Session, factory: SessionFactory, settings: Settings, gateway: Gateway, make_user: MakeUser
) -> None:
    job, _ = _enqueue(db, uuid.uuid4(), {}, make_user())
    runner.HANDLERS.pop(JobType.CHAT, None)

    runner.run_job(job.id, factory, gateway, settings)

    db.expire_all()
    assert db.scalars(select(models.AiJob.status)).one() == JobStatus.FAILED


# --- Polling --------------------------------------------------------------------------------


def test_the_requester_can_poll_their_job(
    client: TestClient,
    db: Session,
    factory: SessionFactory,
    settings: Settings,
    gateway: Gateway,
    fake_ai: FakeProvider,
    make_user: MakeUser,
    auth: Auth,
    chat_handler: list[uuid.UUID],
) -> None:
    fake_ai.scripts = {"shade": lambda parts: {"risk": "low"}}
    user = make_user()
    job, _ = _enqueue(db, uuid.uuid4(), {}, user)

    queued = client.get(f"/jobs/{job.id}", headers=auth(user)).json()
    assert (queued["status"], queued["output"]) == ("queued", None)

    runner.run_job(job.id, factory, gateway, settings)
    done = client.get(f"/jobs/{job.id}", headers=auth(user)).json()
    assert done["status"] == "succeeded"
    assert done["job_type"] == "chat"


def test_other_users_cannot_see_a_job(
    client: TestClient, db: Session, make_user: MakeUser, auth: Auth
) -> None:
    job, _ = _enqueue(db, uuid.uuid4(), {}, make_user())

    assert client.get(f"/jobs/{job.id}", headers=auth(make_user())).status_code == 404
    assert client.get(f"/jobs/{job.id}", headers=auth(make_user(Role.ADMIN))).status_code == 200
    assert client.get(f"/jobs/{uuid.uuid4()}", headers=auth(make_user())).status_code == 404
