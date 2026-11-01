from uuid import UUID

from fastapi import APIRouter

from api.app.deps import AnyUser, DbSession
from api.app.errors import error_responses
from api.app.schemas import JobOut
from api.app.services import jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut, responses=error_responses(401, 404))
def get_job(job_id: UUID, user: AnyUser, db: DbSession) -> JobOut:
    """Polling fallback for clients without SSE. Only the user who started a job can read it."""
    return jobs.get_job(db, user, job_id)
