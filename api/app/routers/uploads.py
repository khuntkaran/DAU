from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, UploadFile
from fastapi.responses import FileResponse

from api.app.deps import AnyUser
from api.app.enums import FilePurpose
from api.app.errors import error_responses, not_implemented
from api.app.schemas import FileOut

router = APIRouter(tags=["files"])


@router.post(
    "/uploads", status_code=201, response_model=FileOut, responses=error_responses(401, 413, 415)
)
async def upload_file(
    file: UploadFile, purpose: Annotated[FilePurpose, Form()], user: AnyUser
) -> FileOut:
    """Multipart upload to the local `uploads/` folder, with a `files` row and its sha256.

    Stands in for presigned object storage in production. Type and size limits are in
    `schemas.check_upload`.
    """
    raise not_implemented()


@router.get(
    "/files/{file_id}",
    response_class=FileResponse,
    responses={200: {"description": "The file bytes."}, **error_responses(401, 403, 404)},
)
async def get_file(file_id: UUID, user: AnyUser) -> FileResponse:
    """Only the owner, or a party to the file's request, can read it."""
    raise not_implemented()
