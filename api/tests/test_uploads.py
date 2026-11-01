"""Multipart uploads to the local uploads folder (work plan 3.2), and reading files back."""

import hashlib
import uuid
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app import models, schemas
from api.app.config import Settings
from api.app.enums import (
    AttachmentKind,
    FilePurpose,
    InputMethod,
    LocationSource,
    QuoteSource,
    QuoteStatus,
    RequestStatus,
    Role,
    StateCategory,
)
from api.tests.conftest import MakeUser

Auth = Callable[[models.User], dict[str, str]]
GPS_TAG = 0x8825
DAY = date(2026, 11, 1)
WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 64
PDF = b"%PDF-1.7\n" + b"0" * 64


def _image(fmt: str = "JPEG", size: tuple[int, int] = (64, 48), gps: bool = False) -> bytes:
    image = Image.new("RGB", size, (200, 120, 40))
    exif = Image.Exif()
    if gps:
        exif[GPS_TAG] = {1: "N", 2: (23.0, 1.0, 21.0), 3: "E", 4: (72.0, 34.0, 17.0)}
    out = BytesIO()
    image.save(out, fmt, exif=exif.tobytes())
    return out.getvalue()


def _upload(
    client: TestClient,
    headers: dict[str, str],
    data: bytes,
    purpose: str = "terrace_photo",
    content_type: str = "image/jpeg",
    name: str = "roof.jpg",
) -> dict[str, object]:
    response = client.post(
        "/uploads",
        data={"purpose": purpose},
        files={"file": (name, data, content_type)},
        headers=headers,
    )
    return {"status": response.status_code, **response.json()}


def _code(result: dict[str, object]) -> object:
    error = result["error"]
    assert isinstance(error, dict)
    return error["code"]


def _stored(settings: Settings, db: Session, file_id: object) -> Path:
    file = db.get(models.File, uuid.UUID(str(file_id)))
    assert file is not None
    return settings.upload_dir / file.storage_key


@pytest.fixture(autouse=True)
def _uploads_in_tmp(settings: Settings, tmp_path: Path) -> None:
    settings.upload_dir = tmp_path / "uploads"


# --- Uploading ------------------------------------------------------------------------------


def test_a_household_uploads_a_terrace_photo(
    client: TestClient, db: Session, settings: Settings, make_user: MakeUser, auth: Auth
) -> None:
    user = make_user(Role.HOUSEHOLD)
    result = _upload(client, auth(user), _image(size=(64, 48)))

    assert result["status"] == 201
    assert (result["purpose"], result["mime_type"]) == ("terrace_photo", "image/jpeg")
    assert (result["width"], result["height"]) == (64, 48)
    assert result["url"] == f"/files/{result['id']}"
    stored = _stored(settings, db, result["id"])
    assert stored.read_bytes()[:3] == b"\xff\xd8\xff"
    assert hashlib.sha256(stored.read_bytes()).hexdigest() == result["sha256"]
    row = db.scalars(select(models.File)).one()
    assert (row.owner_user_id, row.original_name) == (user.id, "roof.jpg")


def test_location_metadata_is_removed_from_photos(
    client: TestClient, db: Session, settings: Settings, make_user: MakeUser, auth: Auth
) -> None:
    original = _image(gps=True)
    assert Image.open(BytesIO(original)).getexif().get(GPS_TAG)

    result = _upload(client, auth(make_user()), original)

    assert result["status"] == 201
    with Image.open(_stored(settings, db, result["id"])) as kept:
        assert not kept.getexif().get(GPS_TAG)


def test_png_photos_are_accepted(client: TestClient, make_user: MakeUser, auth: Auth) -> None:
    result = _upload(client, auth(make_user()), _image("PNG"), content_type="image/png")
    assert (result["status"], result["mime_type"]) == (201, "image/png")


def test_the_type_comes_from_the_bytes_not_the_label(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    result = _upload(client, auth(make_user()), _image("PNG"), content_type="image/jpeg")
    assert (result["status"], result["mime_type"]) == (201, "image/png")


def test_a_text_file_named_jpg_is_rejected(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    result = _upload(client, auth(make_user()), b"<script>alert(1)</script>")
    assert (result["status"], _code(result)) == (415, "unsupported_type")


def test_a_corrupt_image_is_rejected(client: TestClient, make_user: MakeUser, auth: Auth) -> None:
    result = _upload(client, auth(make_user()), b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    assert (result["status"], _code(result)) == (415, "unreadable_image")


def test_a_file_that_does_not_fit_its_purpose_is_rejected(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    result = _upload(client, auth(make_user()), _image(), purpose="voice_audio")
    assert (result["status"], _code(result)) == (415, "unsupported_type")


def test_voice_audio_and_pdf_bills_are_accepted(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    headers = auth(make_user())
    audio = _upload(client, headers, WEBM, "voice_audio", "audio/webm", "voice.webm")
    bill = _upload(client, headers, PDF, "electricity_bill", "application/pdf", "bill.pdf")

    assert (audio["status"], audio["mime_type"], audio["width"]) == (201, "audio/webm", None)
    assert (bill["status"], bill["mime_type"]) == (201, "application/pdf")


def test_an_oversized_file_is_rejected(
    client: TestClient, make_user: MakeUser, auth: Auth, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(schemas.MAX_UPLOAD_BYTES, FilePurpose.VOICE_AUDIO, 32)

    result = _upload(client, auth(make_user()), WEBM, "voice_audio", "audio/webm")
    assert (result["status"], _code(result)) == (413, "file_too_large")


def test_an_empty_file_is_rejected(client: TestClient, make_user: MakeUser, auth: Auth) -> None:
    result = _upload(client, auth(make_user()), b"")
    assert (result["status"], _code(result)) == (422, "empty_file")


def test_purposes_that_cannot_be_uploaded_are_rejected(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    result = _upload(client, auth(make_user()), _image(), purpose="logo")
    assert (result["status"], _code(result)) == (422, "invalid_purpose")


def test_a_vendor_cannot_upload_a_terrace_photo(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    result = _upload(client, auth(make_user(Role.VENDOR)), _image())
    assert (result["status"], _code(result)) == (403, "forbidden")


def test_a_vendor_can_upload_a_quote_document(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    result = _upload(
        client, auth(make_user(Role.VENDOR)), PDF, "quote_document", "application/pdf", "q.pdf"
    )
    assert result["status"] == 201


def test_the_same_file_twice_is_stored_once(
    client: TestClient, db: Session, make_user: MakeUser, auth: Auth
) -> None:
    headers = auth(make_user())
    photo = _image()

    first = _upload(client, headers, photo)
    second = _upload(client, headers, photo)

    assert first["id"] == second["id"]
    assert len(db.scalars(select(models.File)).all()) == 1


def test_uploading_needs_a_sign_in(client: TestClient) -> None:
    response = client.post(
        "/uploads", data={"purpose": "terrace_photo"}, files={"file": ("a.jpg", _image())}
    )
    assert response.status_code == 401


# --- Reading back ---------------------------------------------------------------------------


def _attach(
    db: Session, owner: models.User, file_id: object, kind: AttachmentKind, status: RequestStatus
) -> models.SolarRequest:
    rule_set = db.scalars(select(models.RuleSet)).first()
    if rule_set is None:
        rule_set = models.RuleSet(
            scheme="pm_surya_ghar",
            version="v",
            effective_from=DAY,
            is_active=True,
            source_checked_on=DAY,
        )
        db.add(rule_set)
        db.flush()
    count = len(db.scalars(select(models.SolarRequest)).all())
    request = models.SolarRequest(
        request_code=f"SR-2026-{count + 1:06d}",
        household_id=owner.id,
        lat=23.0,
        lng=72.5,
        location_source=LocationSource.MAP_PIN,
        state_category=StateCategory.GENERAL,
        monthly_units=300,
        budget_inr=150000,
        input_method=InputMethod.FORM,
        status=status,
        rule_set_id=rule_set.id,
    )
    db.add(request)
    db.flush()
    db.add(
        models.RequestAttachment(
            request_id=request.id, file_id=uuid.UUID(str(file_id)), kind=kind, is_primary=True
        )
    )
    db.commit()
    return request


def test_the_owner_can_read_their_file(
    client: TestClient, db: Session, settings: Settings, make_user: MakeUser, auth: Auth
) -> None:
    headers = auth(make_user())
    uploaded = _upload(client, headers, _image())

    response = client.get(f"/files/{uploaded['id']}", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.content == _stored(settings, db, uploaded["id"]).read_bytes()


def test_another_household_cannot_read_it(
    client: TestClient, make_user: MakeUser, auth: Auth
) -> None:
    uploaded = _upload(client, auth(make_user()), _image())

    response = client.get(f"/files/{uploaded['id']}", headers=auth(make_user()))
    assert response.status_code == 404


def test_a_vendor_sees_photos_of_open_requests_only(
    client: TestClient, db: Session, make_user: MakeUser, auth: Auth
) -> None:
    household = make_user()
    vendor = make_user(Role.VENDOR)
    loose = _upload(client, auth(household), _image(size=(10, 10)))
    attached = _upload(client, auth(household), _image(size=(20, 20)))
    _attach(db, household, attached["id"], AttachmentKind.TERRACE_PHOTO, RequestStatus.OPEN)

    assert client.get(f"/files/{loose['id']}", headers=auth(vendor)).status_code == 404
    assert client.get(f"/files/{attached['id']}", headers=auth(vendor)).status_code == 200


def test_a_vendor_who_quoted_keeps_access_after_the_request_closes(
    client: TestClient, db: Session, make_user: MakeUser, auth: Auth
) -> None:
    household = make_user()
    quoting, other = make_user(Role.VENDOR), make_user(Role.VENDOR)
    uploaded = _upload(client, auth(household), _image())
    request = _attach(
        db, household, uploaded["id"], AttachmentKind.TERRACE_PHOTO, RequestStatus.ACCEPTED
    )
    vendor = quoting.vendor
    assert vendor is not None
    db.add(
        models.Quote(
            quote_code="Q-2026-000001",
            request_id=request.id,
            vendor_id=vendor.id,
            status=QuoteStatus.ACCEPTED,
            system_kw=Decimal(3),
            price_total_inr=180000,
            gst_included=True,
            panel_brand="P",
            dcr_compliant=True,
            inverter_brand="I",
            timeline_days=20,
            source=QuoteSource.FORM,
        )
    )
    db.commit()

    assert client.get(f"/files/{uploaded['id']}", headers=auth(quoting)).status_code == 200
    assert client.get(f"/files/{uploaded['id']}", headers=auth(other)).status_code == 404


def test_vendors_never_see_electricity_bills(
    client: TestClient, db: Session, make_user: MakeUser, auth: Auth
) -> None:
    household = make_user()
    bill = _upload(client, auth(household), PDF, "electricity_bill", "application/pdf")
    _attach(db, household, bill["id"], AttachmentKind.ELECTRICITY_BILL, RequestStatus.OPEN)

    response = client.get(f"/files/{bill['id']}", headers=auth(make_user(Role.VENDOR)))
    assert response.status_code == 404


def test_an_admin_can_read_any_file(client: TestClient, make_user: MakeUser, auth: Auth) -> None:
    uploaded = _upload(client, auth(make_user()), _image())

    response = client.get(f"/files/{uploaded['id']}", headers=auth(make_user(Role.ADMIN)))
    assert response.status_code == 200


def test_an_unknown_file_is_not_found(client: TestClient, make_user: MakeUser, auth: Auth) -> None:
    response = client.get("/files/00000000-0000-4000-8000-000000000000", headers=auth(make_user()))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
