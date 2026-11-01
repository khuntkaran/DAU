from uuid import UUID

from fastapi import APIRouter

from api.app.deps import AnyUser
from api.app.errors import error_responses, not_implemented
from api.app.schemas import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut, responses=error_responses(401, 404))
async def get_job(job_id: UUID, user: AnyUser) -> JobOut:
    """Polling fallback for clients without SSE. Only the job's owner can read it."""
    raise not_implemented()
