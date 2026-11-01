from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, UploadFile
from fastapi.responses import FileResponse

from api.app.deps import AnyUser, AppSettings, DbSession
from api.app.enums import FilePurpose
from api.app.errors import error_responses
from api.app.schemas import MAX_UPLOAD_BYTES, FileOut
from api.app.services import files

router = APIRouter(tags=["files"])


@router.post(
    "/uploads",
    status_code=201,
    response_model=FileOut,
    responses=error_responses(401, 403, 413, 415),
)
def upload_file(
    file: UploadFile,
    purpose: Annotated[FilePurpose, Form()],
    user: AnyUser,
    db: DbSession,
    settings: AppSettings,
) -> FileOut:
    """Multipart upload to the local `uploads/` folder. Photos lose their metadata.

    Production swaps the folder for presigned object storage behind the same response.
    """
    # One byte over the limit is enough to know the file is too large.
    data = file.file.read(MAX_UPLOAD_BYTES.get(purpose, 0) + 1)
    stored = files.store_upload(db, settings, user, purpose, data, file.filename)
    return files.file_out(stored)


@router.get(
    "/files/{file_id}",
    response_class=FileResponse,
    responses={200: {"description": "The file bytes."}, **error_responses(401, 404)},
)
def get_file(file_id: UUID, user: AnyUser, db: DbSession, settings: AppSettings) -> FileResponse:
    """The owner, an admin, or a vendor viewing that request's terrace photo."""
    stored, path = files.readable_file(db, settings, user, file_id)
    return FileResponse(
        path,
        media_type=stored.mime_type,
        headers={
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=300",
        },
    )
