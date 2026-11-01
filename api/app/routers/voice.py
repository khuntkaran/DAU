from fastapi import APIRouter

from api.app.deps import Household
from api.app.errors import error_responses, not_implemented
from api.app.schemas import JobAccepted, VoiceTranscribeRequest

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post(
    "/transcribe",
    status_code=202,
    response_model=JobAccepted,
    responses=error_responses(401, 403, 404, 422, 429),
)
async def transcribe(body: VoiceTranscribeRequest, user: Household) -> JobAccepted:
    """Queues `voice_extract`. The job output is a `VoiceResult` with fields to prefill."""
    raise not_implemented()
