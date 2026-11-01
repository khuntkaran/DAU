from fastapi import APIRouter

from api.app.deps import AnyUser
from api.app.errors import error_responses, not_implemented
from api.app.schemas import PresignRequest, PresignResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/presign", response_model=PresignResponse, responses=error_responses(401, 422))
async def presign_upload(body: PresignRequest, user: AnyUser) -> PresignResponse:
    """Returns a presigned PUT URL. The browser uploads straight to storage, never via the API."""
    raise not_implemented()
