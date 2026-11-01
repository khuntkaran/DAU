from fastapi import APIRouter, BackgroundTasks

from api.app.deps import Ai, AppSettings, DbSession, Household, Sessions
from api.app.errors import error_responses
from api.app.jobs import voice_extract
from api.app.jobs.runner import run_job
from api.app.schemas import JobAccepted, VoiceTranscribeRequest

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post(
    "/transcribe",
    status_code=202,
    response_model=JobAccepted,
    responses=error_responses(401, 403, 422, 429),
)
def transcribe(
    body: VoiceTranscribeRequest,
    user: Household,
    db: DbSession,
    background: BackgroundTasks,
    sessions: Sessions,
    ai: Ai,
    settings: AppSettings,
) -> JobAccepted:
    """Queues `voice_extract` for an uploaded voice note. Poll the job for a `VoiceResult`.

    The fields prefill the form for the household to check. Pass `entity_id` as
    `voice_input_id` when submitting the request. Limited to 10 voice notes an hour.
    """
    job, voice, needs_run = voice_extract.start(db, user, body.audio_file_id, body.language)
    if needs_run:
        background.add_task(run_job, job.id, sessions, ai, settings)
    return JobAccepted(job_id=job.id, job_type=job.job_type, status=job.status, entity_id=voice.id)
