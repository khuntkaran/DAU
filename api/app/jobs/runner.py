"""Background AI jobs. Every LLM call runs here, never inside a request.

A job is recorded in `ai_jobs` before it runs. The same input for the same row returns the
existing job, and the same input for another row reuses a finished answer, so a retry or a
duplicate click never spends a second call.
"""

import hashlib
import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app import models
from api.app.config import Settings
from api.app.db import SessionFactory, utcnow
from api.app.enums import JobPriority, JobStatus, JobType
from api.app.llm.gateway import AiUnavailable, Gateway, Result, Transcription

logger = logging.getLogger("suryasetu.jobs")


@dataclass(frozen=True)
class JobContext:
    db: Session
    job: models.AiJob
    gateway: Gateway
    settings: Settings


Handler = Callable[[JobContext], dict[str, Any]]
HANDLERS: dict[JobType, Handler] = {}
# Runs after a job fails, so the row it was filling in can say so instead of staying pending.
FailureHook = Callable[[Session, models.AiJob], None]
ON_FAILURE: dict[JobType, FailureHook] = {}

_LIVE = (JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.SUCCEEDED)


def handler(job_type: JobType) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        HANDLERS[job_type] = fn
        return fn

    return register


def on_failure(job_type: JobType) -> Callable[[FailureHook], FailureHook]:
    def register(fn: FailureHook) -> FailureHook:
        ON_FAILURE[job_type] = fn
        return fn

    return register


def input_hash(payload: dict[str, Any], prompt_version: str) -> str:
    text = json.dumps(payload, sort_keys=True, default=str) + prompt_version
    return hashlib.sha256(text.encode()).hexdigest()


def enqueue(
    db: Session,
    *,
    job_type: JobType,
    entity_type: str,
    entity_id: uuid.UUID,
    payload: dict[str, Any],
    prompt_version: str,
    priority: JobPriority,
    requested_by: uuid.UUID | None,
) -> tuple[models.AiJob, bool]:
    """Returns the job and whether it still needs to run. The caller commits."""
    digest = input_hash(payload, prompt_version)
    same = db.scalars(
        select(models.AiJob).where(
            models.AiJob.entity_id == entity_id,
            models.AiJob.job_type == job_type,
            models.AiJob.input_hash == digest,
            models.AiJob.status.in_(_LIVE),
        )
    ).first()
    if same is not None:
        return same, False

    now = utcnow()
    job = models.AiJob(
        job_type=job_type,
        entity_type=entity_type,
        entity_id=entity_id,
        priority=priority,
        prompt_version=prompt_version,
        input_hash=digest,
        requested_by=requested_by,
        queued_at=now,
        status=JobStatus.QUEUED,
    )
    cached = db.scalars(
        select(models.AiJob)
        .where(
            models.AiJob.job_type == job_type,
            models.AiJob.input_hash == digest,
            models.AiJob.status == JobStatus.SUCCEEDED,
        )
        .order_by(models.AiJob.finished_at.desc())
        .limit(1)
    ).first()
    if cached is not None:
        job.status = JobStatus.SUCCEEDED
        job.output = cached.output
        job.provider, job.model = "cache", cached.model
        job.started_at = job.finished_at = now
    db.add(job)
    db.flush()
    return job, cached is None


def record(job: models.AiJob, result: Result[Any] | Transcription) -> None:
    """Notes which provider answered and what it cost, for the free-tier budget."""
    job.provider, job.model, job.latency_ms = result.provider, result.model, result.latency_ms
    if isinstance(result, Result):
        job.tokens_in, job.tokens_out = result.tokens_in, result.tokens_out


def run_job(
    job_id: uuid.UUID, factory: SessionFactory, gateway: Gateway, settings: Settings
) -> None:
    """Runs one queued job. Failures are stored on the job; nothing is raised to the caller."""
    with factory() as db:
        job = db.get(models.AiJob, job_id)
        if job is None or job.status != JobStatus.QUEUED:
            return
        fn = HANDLERS.get(job.job_type)
        job.status, job.started_at = JobStatus.RUNNING, utcnow()
        job.attempts += 1
        db.commit()

        try:
            if fn is None:
                raise LookupError(f"no handler for {job.job_type}")
            output = fn(JobContext(db, job, gateway, settings))
        except AiUnavailable as exc:
            db.rollback()
            _finish(db, job_id, JobStatus.FAILED, error=f"AI unavailable: {exc}")
            return
        except Exception:
            logger.exception("job failed id=%s type=%s", job_id, job.job_type)
            db.rollback()
            _finish(db, job_id, JobStatus.FAILED, error="The job failed. It can be retried.")
            return
        job.status, job.output, job.finished_at = JobStatus.SUCCEEDED, output, utcnow()
        db.commit()


def _finish(db: Session, job_id: uuid.UUID, status: JobStatus, *, error: str) -> None:
    job = db.get(models.AiJob, job_id)
    if job is not None:
        job.status, job.error, job.finished_at = status, error, utcnow()
        hook = ON_FAILURE.get(job.job_type)
        if hook is not None:
            hook(db, job)
        db.commit()
