"""Creating solar requests and showing them to their owner or to vendors."""

import math
import uuid
from datetime import timedelta
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy import or_, select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app import models
from api.app.db import utcnow
from api.app.enums import (
    AttachmentKind,
    FilePurpose,
    QuoteStatus,
    RequestStatus,
    Role,
    StateCategory,
)
from api.app.errors import ApiError
from api.app.schemas import (
    AttachmentOut,
    BBox,
    CalculationOut,
    HouseholdContact,
    ObstructionOut,
    OpenRequestPin,
    Page,
    RequestCreate,
    RequestOut,
    RequestSummary,
    RoofAssessmentOut,
    VendorRequestView,
)
from api.app.services.calculations import request_estimate
from api.app.services.codes import CODE_RETRIES, next_code
from api.app.services.geo import GRID_DEG, approx_point, haversine_km, km
from api.app.services.pagination import decode_cursor, encode_cursor
from api.app.services.rules import citations_for, ensure_rule_set

# From the request lifecycle in the architecture: open requests expire after 30 days.
REQUEST_LIFETIME = timedelta(days=30)
VISIBLE_TO_VENDORS = (RequestStatus.OPEN, RequestStatus.QUOTED)

_NOT_FOUND = ApiError(404, "not_found", "Request not found.")

Row = TypeVar("Row")


def _invalid(message: str) -> ApiError:
    return ApiError(422, "invalid_attachment", message)


def _owned_files(
    db: Session, user: models.User, ids: list[uuid.UUID], purpose: FilePurpose
) -> list[models.File]:
    if len(set(ids)) != len(ids):
        raise _invalid("The same file is listed twice.")
    if not ids:
        return []
    found = {
        f.id: f
        for f in db.scalars(
            select(models.File).where(
                models.File.id.in_(ids),
                models.File.owner_user_id == user.id,
                models.File.purpose == purpose,
                models.File.deleted_at.is_(None),
            )
        )
    }
    if len(found) != len(ids):
        raise _invalid(f"Each file must be your own {purpose.replace('_', ' ')} upload.")
    return [found[i] for i in ids]


def create_request(db: Session, user: models.User, body: RequestCreate) -> models.SolarRequest:
    discom = None
    if body.discom_id is not None:
        discom = db.get(models.Discom, body.discom_id)
        if discom is None:
            raise ApiError(422, "unknown_discom", "That electricity company is not listed.")
    photos = _owned_files(db, user, body.photo_file_ids, FilePurpose.TERRACE_PHOTO)
    bills = _owned_files(
        db, user, [body.bill_file_id] if body.bill_file_id else [], FilePurpose.ELECTRICITY_BILL
    )
    voice = None
    if body.voice_input_id is not None:
        voice = db.get(models.VoiceInput, body.voice_input_id)
        if voice is None or voice.user_id != user.id or voice.request_id is not None:
            raise ApiError(422, "invalid_voice_input", "That voice note cannot be used here.")

    fields = body.model_dump(exclude={"photo_file_ids", "bill_file_id", "voice_input_id"})
    for attempt in range(CODE_RETRIES):
        try:
            return _insert(db, user, fields, discom, photos, bills, voice)
        except IntegrityError:
            # Two requests took the same code at once; the loser takes the next one.
            db.rollback()
            if attempt == CODE_RETRIES - 1:
                raise
    raise AssertionError("unreachable")


def _insert(
    db: Session,
    user: models.User,
    fields: dict[str, Any],
    discom: models.Discom | None,
    photos: list[models.File],
    bills: list[models.File],
    voice: models.VoiceInput | None,
) -> models.SolarRequest:
    rule_set = ensure_rule_set(db)
    now = utcnow()
    request = models.SolarRequest(
        **fields,
        request_code=next_code(db, models.SolarRequest.request_code, "SR"),
        household_id=user.id,
        state_category=discom.state_category if discom else StateCategory.GENERAL,
        status=RequestStatus.OPEN,
        rule_set_id=rule_set.id,
        submitted_at=now,
        expires_at=now + REQUEST_LIFETIME,
        created_at=now,
    )
    db.add(request)
    db.flush()

    estimate = request_estimate(request)
    db.add(estimate)
    db.flush()
    request.latest_estimate_id = estimate.id
    db.add(
        models.RequestStatusHistory(
            request_id=request.id, to_status=RequestStatus.OPEN, changed_by=user.id
        )
    )
    attachments = [(f, AttachmentKind.TERRACE_PHOTO) for f in photos] + [
        (f, AttachmentKind.ELECTRICITY_BILL) for f in bills
    ]
    for order, (file, kind) in enumerate(attachments):
        db.add(
            models.RequestAttachment(
                request_id=request.id,
                file_id=file.id,
                kind=kind,
                is_primary=order == 0 and kind == AttachmentKind.TERRACE_PHOTO,
                sort_order=order,
            )
        )
    if voice is not None:
        voice.request_id = request.id
        voice.applied_to_request = True
    db.commit()
    return request


# --- Reading --------------------------------------------------------------------------------


def required(row: Row | None, what: str) -> Row:
    # Foreign keys guarantee these rows; a miss means the database is damaged.
    if row is None:
        raise RuntimeError(f"missing {what}")
    return row


def fields_of(row: object, model: type[BaseModel]) -> dict[str, Any]:
    return {name: getattr(row, name) for name in model.model_fields if hasattr(row, name)}


def calculation_out(db: Session, calc: models.Calculation) -> CalculationOut:
    rule_set = required(db.get(models.RuleSet, calc.rule_set_id), "rule set")
    citations = citations_for(db, calc.rule_set_id)
    return CalculationOut.model_validate(
        {
            **fields_of(calc, CalculationOut),
            "rule_version": rule_set.version,
            "citations": [citations[k] for k in calc.citation_keys if k in citations],
        }
    )


def _attachments(
    db: Session, request: models.SolarRequest, kinds: tuple[AttachmentKind, ...]
) -> list[AttachmentOut]:
    rows = db.scalars(
        select(models.RequestAttachment)
        .where(
            models.RequestAttachment.request_id == request.id,
            models.RequestAttachment.kind.in_(kinds),
        )
        .order_by(models.RequestAttachment.sort_order)
    )
    return [
        AttachmentOut(
            id=a.id,
            file_id=a.file_id,
            kind=a.kind,
            is_primary=a.is_primary,
            url=f"/files/{a.file_id}",
        )
        for a in rows
    ]


def _roof_assessment(db: Session, request: models.SolarRequest) -> RoofAssessmentOut | None:
    assessment = db.scalars(
        select(models.RoofAssessment)
        .where(models.RoofAssessment.request_id == request.id)
        .order_by(models.RoofAssessment.created_at.desc())
        .limit(1)
    ).first()
    if assessment is None:
        return None
    obstructions = db.scalars(
        select(models.RoofObstruction).where(models.RoofObstruction.assessment_id == assessment.id)
    )
    return RoofAssessmentOut.model_validate(
        {
            **fields_of(assessment, RoofAssessmentOut),
            "obstructions": [ObstructionOut.model_validate(o) for o in obstructions],
        }
    )


def _common(
    db: Session, request: models.SolarRequest, kinds: tuple[AttachmentKind, ...]
) -> dict[str, Any]:
    estimate = required(db.get(models.Calculation, request.latest_estimate_id), "estimate")
    return {
        "estimate": calculation_out(db, estimate),
        "roof_assessment": _roof_assessment(db, request),
        "attachments": _attachments(db, request, kinds),
    }


def owner_view(db: Session, request: models.SolarRequest) -> RequestOut:
    every_kind = tuple(AttachmentKind)
    return RequestOut.model_validate(
        {**fields_of(request, RequestOut), **_common(db, request, every_kind)}
    )


def household_contact(db: Session, request: models.SolarRequest) -> HouseholdContact:
    """Only for the vendor whose quote was accepted."""
    household = required(db.get(models.User, request.household_id), "household")
    return HouseholdContact(
        full_name=household.full_name,
        phone=household.phone,
        lat=request.lat,
        lng=request.lng,
        address_text=request.address_text,
    )


def vendor_view(
    db: Session, request: models.SolarRequest, vendor: models.Vendor
) -> VendorRequestView:
    my_quote = db.scalars(
        select(models.Quote).where(
            models.Quote.request_id == request.id, models.Quote.vendor_id == vendor.id
        )
    ).first()
    approx_lat, approx_lng = approx_point(request.lat, request.lng)
    distance = None
    if vendor.base_lat is not None and vendor.base_lng is not None:
        distance = km(haversine_km(vendor.base_lat, vendor.base_lng, approx_lat, approx_lng))

    contact = None
    if my_quote is not None and my_quote.status == QuoteStatus.ACCEPTED:
        contact = household_contact(db, request)
    return VendorRequestView.model_validate(
        {
            **fields_of(request, VendorRequestView),
            # Bills and voice notes are private; vendors see terrace photos only.
            **_common(db, request, (AttachmentKind.TERRACE_PHOTO,)),
            "approx_lat": approx_lat,
            "approx_lng": approx_lng,
            "distance_km": distance,
            "my_quote_id": my_quote.id if my_quote else None,
            "contact": contact,
        }
    )


def get_request(
    db: Session, user: models.User, request_id: uuid.UUID
) -> RequestOut | VendorRequestView:
    request = db.get(models.SolarRequest, request_id)
    if request is None:
        raise _NOT_FOUND
    if user.role == Role.HOUSEHOLD:
        if request.household_id != user.id:
            raise _NOT_FOUND
        return owner_view(db, request)

    vendor = user.vendor
    if vendor is None:
        raise _NOT_FOUND
    quoted = db.scalar(
        select(models.Quote.id).where(
            models.Quote.request_id == request.id, models.Quote.vendor_id == vendor.id
        )
    )
    if request.status not in VISIBLE_TO_VENDORS and quoted is None:
        raise _NOT_FOUND
    return vendor_view(db, request, vendor)


def my_requests(
    db: Session, user: models.User, limit: int, cursor: str | None
) -> Page[RequestSummary]:
    query = (
        select(models.SolarRequest, models.Calculation.system_kw)
        .join(models.Calculation, models.Calculation.id == models.SolarRequest.latest_estimate_id)
        .where(models.SolarRequest.household_id == user.id)
        .order_by(models.SolarRequest.created_at.desc(), models.SolarRequest.id.desc())
        .limit(limit + 1)
    )
    if cursor is not None:
        created_at, row_id = decode_cursor(cursor)
        query = query.where(
            tuple_(models.SolarRequest.created_at, models.SolarRequest.id)
            < tuple_(created_at, row_id)
        )
    rows = db.execute(query).all()
    items = [
        RequestSummary.model_validate({**fields_of(r, RequestSummary), "system_kw": kw})
        for r, kw in rows[:limit]
    ]
    last = rows[limit - 1][0] if len(rows) > limit else None
    return Page[RequestSummary](
        items=items, next_cursor=encode_cursor(last.created_at, last.id) if last else None
    )


# --- Vendor map -----------------------------------------------------------------------------

# Rows are read in batches because the radius check runs on the rounded point in Python.
_MAP_BATCH = 200


def open_requests(
    db: Session, user: models.User, bbox: BBox, limit: int, cursor: str | None
) -> Page[OpenRequestPin]:
    """Open and quoted requests whose rounded pin lies in the view and the service radius.

    A vendor with no base location yet sees the whole view, without distances.
    """
    vendor = user.vendor
    base = (
        (vendor.base_lat, vendor.base_lng, vendor.service_radius_km)
        if vendor and vendor.base_lat is not None and vendor.base_lng is not None
        else None
    )
    # Pins move by up to half a grid cell, so the database filter is widened by that much.
    pad = GRID_DEG / 2
    south, north, west, east = bbox.south - pad, bbox.north + pad, bbox.west - pad, bbox.east + pad
    if base is not None:
        lat, lng, radius = base
        lat_span = radius / 111.0 + pad
        lng_span = radius / (111.0 * max(math.cos(math.radians(lat)), 0.01)) + pad
        south, north = max(south, lat - lat_span), min(north, lat + lat_span)
        west, east = max(west, lng - lng_span), min(east, lng + lng_span)

    query = (
        select(models.SolarRequest, models.Calculation.system_kw)
        .join(models.Calculation, models.Calculation.id == models.SolarRequest.latest_estimate_id)
        .where(
            models.SolarRequest.status.in_(VISIBLE_TO_VENDORS),
            or_(
                models.SolarRequest.expires_at.is_(None), models.SolarRequest.expires_at > utcnow()
            ),
            models.SolarRequest.lat.between(south, north),
            models.SolarRequest.lng.between(west, east),
        )
        .order_by(models.SolarRequest.created_at.desc(), models.SolarRequest.id.desc())
        .limit(_MAP_BATCH)
    )
    position = decode_cursor(cursor) if cursor is not None else None

    pins: list[OpenRequestPin] = []
    last: models.SolarRequest | None = None
    more = False
    while True:
        batch = query
        if position is not None:
            batch = batch.where(
                tuple_(models.SolarRequest.created_at, models.SolarRequest.id) < tuple_(*position)
            )
        rows = db.execute(batch).all()
        for request, system_kw in rows:
            approx_lat, approx_lng = approx_point(request.lat, request.lng)
            if not (
                bbox.south <= approx_lat <= bbox.north and bbox.west <= approx_lng <= bbox.east
            ):
                continue
            distance = None
            if base is not None:
                away = haversine_km(base[0], base[1], approx_lat, approx_lng)
                if away > base[2]:
                    continue
                distance = km(away)
            if len(pins) == limit:
                more = True
                break
            pins.append(
                OpenRequestPin.model_validate(
                    {
                        **fields_of(request, OpenRequestPin),
                        "approx_lat": approx_lat,
                        "approx_lng": approx_lng,
                        "distance_km": distance,
                        "recommended_kw": system_kw,
                    }
                )
            )
            last = request
        if more or len(rows) < _MAP_BATCH:
            break
        position = (rows[-1][0].created_at, rows[-1][0].id)

    next_cursor = encode_cursor(last.created_at, last.id) if more and last else None
    return Page[OpenRequestPin](items=pins, next_cursor=next_cursor)
