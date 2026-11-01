"""Reading a job's state for the polling fallback."""

import uuid

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from api.app import models
from api.app.enums import Role
from api.app.errors import ApiError
from api.app.schemas import JobOut, JobOutput

_OUTPUT: TypeAdapter[JobOutput] = TypeAdapter(JobOutput)


def get_job(db: Session, user: models.User, job_id: uuid.UUID) -> JobOut:
    job = db.get(models.AiJob, job_id)
    if job is None or (job.requested_by != user.id and user.role != Role.ADMIN):
        raise ApiError(404, "not_found", "Job not found.")
    output = None
    if job.output is not None:
        try:
            output = _OUTPUT.validate_python(job.output)
        except ValidationError:
            # Output written by an older prompt version; the job page still shows its status.
            output = None
    return JobOut(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        entity_type=job.entity_type,
        entity_id=job.entity_id,
        attempts=job.attempts,
        output=output,
        error=job.error,
        queued_at=job.queued_at,
        finished_at=job.finished_at,
    )
