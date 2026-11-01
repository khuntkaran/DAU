"""Storing uploads in the local uploads folder, and deciding who may read them back.

The file type comes from the bytes, never from the name or the browser's label. Photos are
re-encoded without metadata, because phone photos carry GPS that would reveal the address.
"""

import hashlib
import uuid
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from api.app import models
from api.app.config import Settings
from api.app.enums import AttachmentKind, FilePurpose, RequestStatus, Role
from api.app.errors import ApiError
from api.app.schemas import ALLOWED_CONTENT_TYPES, MAX_UPLOAD_BYTES, FileOut

UPLOAD_ROLES: dict[FilePurpose, frozenset[Role]] = {
    FilePurpose.TERRACE_PHOTO: frozenset({Role.HOUSEHOLD}),
    FilePurpose.ELECTRICITY_BILL: frozenset({Role.HOUSEHOLD}),
    FilePurpose.VOICE_AUDIO: frozenset({Role.HOUSEHOLD}),
    FilePurpose.QUOTE_DOCUMENT: frozenset({Role.HOUSEHOLD, Role.VENDOR}),
}

SIGNATURES: list[tuple[str, Callable[[bytes], bool]]] = [
    ("image/jpeg", lambda b: b.startswith(b"\xff\xd8\xff")),
    ("image/png", lambda b: b.startswith(b"\x89PNG\r\n\x1a\n")),
    ("image/webp", lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
    ("audio/wav", lambda b: b[:4] == b"RIFF" and b[8:12] == b"WAVE"),
    ("application/pdf", lambda b: b.startswith(b"%PDF-")),
    ("audio/webm", lambda b: b.startswith(b"\x1a\x45\xdf\xa3")),
    ("audio/ogg", lambda b: b.startswith(b"OggS")),
    ("audio/mp4", lambda b: b[4:8] == b"ftyp"),
    ("audio/mpeg", lambda b: b.startswith(b"ID3") or (b[:1] == b"\xff" and b[1:2] >= b"\xe0")),
]
EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "audio/wav": ".wav",
    "application/pdf": ".pdf",
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/mpeg": ".mp3",
}
PIL_FORMATS = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
MAX_PIXELS = 40_000_000

_NOT_FOUND = ApiError(404, "not_found", "File not found.")


def sniff(data: bytes) -> str | None:
    return next((mime for mime, matches in SIGNATURES if matches(data)), None)


def _clean_image(data: bytes, mime: str) -> tuple[bytes, int, int]:
    """Re-encodes the picture upright and without EXIF, GPS or text chunks."""
    try:
        with Image.open(BytesIO(data)) as probe:
            if probe.width * probe.height > MAX_PIXELS:
                raise ApiError(415, "unreadable_image", "This image is too large to process.")
            probe.verify()
        with Image.open(BytesIO(data)) as image:
            image.load()
            upright = ImageOps.exif_transpose(image)
    except ApiError:
        raise
    except Exception:
        raise ApiError(415, "unreadable_image", "This image could not be read.") from None

    if mime == "image/jpeg" and upright.mode not in ("RGB", "L"):
        upright = upright.convert("RGB")
    upright.info = {}
    out = BytesIO()
    upright.save(out, PIL_FORMATS[mime], exif=b"", quality=90)
    return out.getvalue(), upright.width, upright.height


def store_upload(
    db: Session,
    settings: Settings,
    user: models.User,
    purpose: FilePurpose,
    data: bytes,
    original_name: str | None,
) -> models.File:
    if purpose not in UPLOAD_ROLES:
        raise ApiError(422, "invalid_purpose", f"{purpose} files cannot be uploaded.")
    if user.role not in UPLOAD_ROLES[purpose]:
        raise ApiError(403, "forbidden", "Your account cannot upload this kind of file.")
    if not data:
        raise ApiError(422, "empty_file", "The file is empty.")
    if len(data) > MAX_UPLOAD_BYTES[purpose]:
        limit_mb = MAX_UPLOAD_BYTES[purpose] / 1024 / 1024
        raise ApiError(413, "file_too_large", f"Files of this kind must be under {limit_mb:g} MB.")

    mime = sniff(data)
    if mime is None or mime not in ALLOWED_CONTENT_TYPES[purpose]:
        raise ApiError(415, "unsupported_type", "This kind of file is not accepted here.")
    width = height = None
    if mime in PIL_FORMATS:
        data, width, height = _clean_image(data, mime)

    sha256 = hashlib.sha256(data).hexdigest()
    existing = db.scalars(
        select(models.File).where(
            models.File.owner_user_id == user.id,
            models.File.purpose == purpose,
            models.File.sha256 == sha256,
            models.File.deleted_at.is_(None),
        )
    ).first()
    if existing is not None:
        return existing

    key = f"files/{uuid.uuid4().hex}{EXTENSIONS[mime]}"
    path = settings.upload_dir / key
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    partial.write_bytes(data)
    partial.replace(path)

    file = models.File(
        owner_user_id=user.id,
        purpose=purpose,
        storage_backend="local",
        storage_key=key,
        # Kept for display only; the stored name never comes from the client.
        original_name=Path(original_name).name[:200] if original_name else None,
        mime_type=mime,
        size_bytes=len(data),
        sha256=sha256,
        width=width,
        height=height,
    )
    db.add(file)
    db.commit()
    return file


def _vendor_can_see(db: Session, user: models.User, file: models.File) -> bool:
    """Terrace photos of requests on the map, or of requests this vendor has quoted."""
    if file.purpose != FilePurpose.TERRACE_PHOTO or user.vendor is None:
        return False
    quoted = exists().where(
        models.Quote.request_id == models.SolarRequest.id,
        models.Quote.vendor_id == user.vendor.id,
    )
    visible = db.scalar(
        select(models.RequestAttachment.id)
        .join(models.SolarRequest, models.SolarRequest.id == models.RequestAttachment.request_id)
        .where(
            models.RequestAttachment.file_id == file.id,
            models.RequestAttachment.kind == AttachmentKind.TERRACE_PHOTO,
            (models.SolarRequest.status.in_([RequestStatus.OPEN, RequestStatus.QUOTED]) | quoted),
        )
        .limit(1)
    )
    return visible is not None


def readable_file(
    db: Session, settings: Settings, user: models.User, file_id: uuid.UUID
) -> tuple[models.File, Path]:
    """The file and its path, or 404 whether it is missing or not this user's to see."""
    file = db.get(models.File, file_id)
    if file is None or file.deleted_at is not None:
        raise _NOT_FOUND
    allowed = (
        file.owner_user_id == user.id
        or user.role == Role.ADMIN
        or (user.role == Role.VENDOR and _vendor_can_see(db, user, file))
    )
    path = settings.upload_dir / file.storage_key
    if not allowed or not path.is_file():
        raise _NOT_FOUND
    return file, path


def file_out(file: models.File) -> FileOut:
    return FileOut(
        id=file.id,
        purpose=file.purpose,
        mime_type=file.mime_type,
        size_bytes=file.size_bytes,
        sha256=file.sha256,
        width=file.width,
        height=file.height,
        url=f"/files/{file.id}",
    )
