"""Builds the local database from files in Git, so every laptop holds the same data.

Usage: npm run db:seed -- --reset

Rule values come only from the rule file. Seed files hold households, vendors, requests and
quotes; every figure on them is calculated by `services.calculations`.
"""

import argparse
import hashlib
import json
import shutil
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from api.app import models
from api.app.config import get_settings
from api.app.db import Base, get_engine, utcnow
from api.app.enums import (
    AttachmentKind,
    BuildingType,
    FilePurpose,
    InputMethod,
    Lang,
    LocationSource,
    QuoteSource,
    QuoteStatus,
    RequestStatus,
    Role,
    RoofType,
    StateCategory,
    VerificationStatus,
)
from api.app.schemas import Input, Lat, Lng, Phone, QuoteCreate, Rupees, check_upload
from api.app.services.calculations import quote_financials, request_estimate
from api.app.services.requests import REQUEST_LIFETIME
from api.app.services.rules import ensure_rule_set
from rules.loader import load_rules

ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = ROOT / "seed" / "data"
PHOTOS_DIR = ROOT / "seed" / "photos"
# Seed photos live in their own folder, so a reset never touches files uploaded while testing.
SEED_UPLOADS = "seed"
PHOTO_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class SeedError(Exception):
    pass


# --- Seed file formats ----------------------------------------------------------------------


class SlabSeed(Input):
    from_units: int = Field(ge=0)
    to_units: int | None = Field(None, gt=0)
    rate_per_unit_inr: Decimal = Field(gt=0)
    fixed_charge_inr: Decimal | None = Field(None, ge=0)
    effective_from: date
    source_url: str | None = None
    is_sample: bool = True


class DiscomSeed(Input):
    code: str = Field(min_length=2, max_length=32)
    name: str
    state: str
    state_category: StateCategory
    net_metering_fee_inr: int | None = Field(None, ge=0)
    portal_url: str | None = None
    tariff_slabs: list[SlabSeed] = Field(default_factory=list)


class UserSeed(Input):
    phone: Phone
    role: Role = Role.HOUSEHOLD
    full_name: str
    preferred_lang: Lang = Lang.EN


class VendorSeed(Input):
    phone: Phone
    full_name: str
    company_name: str
    mnre_registration_no: str | None = None
    gstin: str | None = Field(None, min_length=15, max_length=15)
    years_in_business: int | None = Field(None, ge=0)
    installations_completed: int | None = Field(None, ge=0)
    contact_phone: Phone | None = None
    contact_email: str | None = None
    address: str | None = None
    base_lat: Lat
    base_lng: Lng
    service_radius_km: int = Field(50, gt=0, le=500)
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    avg_rating: Decimal | None = Field(None, ge=0, le=5)
    rating_count: int = Field(0, ge=0)
    about: str | None = None


class RequestSeed(Input):
    code: str = Field(pattern=r"^SR-\d{4}-\d{6}$")
    household_phone: Phone
    lat: Lat
    lng: Lng
    location_source: LocationSource = LocationSource.MAP_PIN
    address_text: str | None = None
    district: str | None = None
    pincode: str | None = Field(None, pattern=r"^\d{6}$")
    discom_code: str | None = None
    monthly_units: int = Field(gt=0)
    monthly_bill_inr: int | None = Field(None, gt=0)
    budget_inr: Rupees
    roof_type: RoofType | None = None
    roof_area_sqm: Decimal = Field(gt=0)
    floors: int | None = Field(None, ge=0)
    building_type: BuildingType | None = None
    notes: str | None = None
    photos: list[str] = Field(default_factory=list, max_length=3)


class QuoteSeed(QuoteCreate):
    """The vendor's quote form, plus which request and vendor it belongs to."""

    code: str = Field(pattern=r"^Q-\d{4}-\d{6}$")
    request_code: str
    vendor_phone: Phone


Row = TypeVar("Row", bound=BaseModel)


def _load(data_dir: Path, name: str, row: type[Row]) -> list[Row]:
    path = data_dir / name
    if not path.exists():
        return []
    try:
        items = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SeedError(f"{name}: not valid JSON: {exc}") from None
    if not isinstance(items, list):
        raise SeedError(f"{name}: expected a list of rows")
    rows = []
    for i, item in enumerate(items):
        try:
            rows.append(row.model_validate(item))
        except ValidationError as exc:
            raise SeedError(f"{name}, row {i + 1}: {exc}") from None
    return rows


def _lookup(table: dict[str, Any], key: str, file: str, what: str) -> Any:
    if key not in table:
        raise SeedError(f"{file}: unknown {what} {key!r}")
    return table[key]


# --- Everything else ------------------------------------------------------------------------


def _copy_photo(db: Session, src: Path, upload_dir: Path, owner: models.User) -> models.File:
    mime = PHOTO_TYPES.get(src.suffix.lower())
    if mime is None or not src.exists():
        raise SeedError(f"requests.json: photo {src.name!r} is missing or not an image")
    data = src.read_bytes()
    try:
        check_upload(FilePurpose.TERRACE_PHOTO, mime, len(data))
    except ValueError as exc:
        raise SeedError(f"requests.json: photo {src.name!r}: {exc}") from None
    key = f"{SEED_UPLOADS}/{uuid.uuid4().hex}{src.suffix.lower()}"
    (upload_dir / key).write_bytes(data)
    file = models.File(
        owner_user_id=owner.id,
        purpose=FilePurpose.TERRACE_PHOTO,
        storage_key=key,
        original_name=src.name,
        mime_type=mime,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )
    db.add(file)
    return file


def _drop_all(engine: Engine) -> None:
    # Requests, quotes and calculations reference each other. PostgreSQL drops those
    # constraints first; SQLite cannot, so its foreign key checks pause for the drop.
    with engine.connect() as conn:
        sqlite = conn.dialect.name == "sqlite"
        if sqlite:
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(conn)
        conn.commit()
        if sqlite:
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")


def seed(
    engine: Engine,
    data_dir: Path,
    upload_dir: Path,
    *,
    reset: bool,
    photos_dir: Path = PHOTOS_DIR,
) -> dict[str, int]:
    """Loads every seed file. Returns how many rows of each kind were created."""
    discoms = _load(data_dir, "discoms.json", DiscomSeed)
    users = _load(data_dir, "users.json", UserSeed)
    vendors = _load(data_dir, "vendors.json", VendorSeed)
    requests = _load(data_dir, "requests.json", RequestSeed)
    quotes = _load(data_dir, "quotes.json", QuoteSeed)

    if reset:
        _drop_all(engine)
        shutil.rmtree(upload_dir / SEED_UPLOADS, ignore_errors=True)
    Base.metadata.create_all(engine)
    (upload_dir / SEED_UPLOADS).mkdir(parents=True, exist_ok=True)

    with Session(engine) as db:
        if db.scalar(select(models.RuleSet.id).limit(1)) is not None:
            raise SeedError("The database already has data. Run again with --reset to rebuild it.")
        rule_set = ensure_rule_set(db)

        discom_by_code: dict[str, models.Discom] = {}
        for d in discoms:
            discom = models.Discom(**d.model_dump(exclude={"tariff_slabs"}))
            discom_by_code[d.code] = discom
            db.add(discom)
            db.flush()
            for slab in d.tariff_slabs:
                db.add(models.DiscomTariffSlab(discom_id=discom.id, **slab.model_dump()))

        user_by_phone: dict[str, models.User] = {}
        for u in users:
            user_by_phone[u.phone] = models.User(**u.model_dump())
        vendor_by_phone: dict[str, models.Vendor] = {}
        for v in vendors:
            user = models.User(role=Role.VENDOR, full_name=v.full_name, phone=v.phone)
            vendor_by_phone[v.phone] = models.Vendor(
                user=user,
                contact_person=v.full_name,
                **v.model_dump(exclude={"phone", "full_name"}),
            )
        db.add_all([*user_by_phone.values(), *vendor_by_phone.values()])
        db.flush()

        now = utcnow()
        request_by_code: dict[str, models.SolarRequest] = {}
        for r in requests:
            household = _lookup(user_by_phone, r.household_phone, "requests.json", "household")
            supplier: models.Discom | None = (
                _lookup(discom_by_code, r.discom_code, "requests.json", "discom")
                if r.discom_code
                else None
            )
            request = models.SolarRequest(
                request_code=r.code,
                household_id=household.id,
                discom_id=supplier.id if supplier else None,
                state_category=supplier.state_category if supplier else StateCategory.GENERAL,
                input_method=InputMethod.FORM,
                status=RequestStatus.OPEN,
                rule_set_id=rule_set.id,
                submitted_at=now,
                expires_at=now + REQUEST_LIFETIME,
                **r.model_dump(exclude={"code", "household_phone", "discom_code", "photos"}),
            )
            db.add(request)
            db.flush()
            estimate = request_estimate(request)
            db.add(estimate)
            db.flush()
            request.latest_estimate_id = estimate.id
            db.add(
                models.RequestStatusHistory(
                    request_id=request.id, to_status=RequestStatus.OPEN, created_at=now
                )
            )
            for order, name in enumerate(r.photos):
                file = _copy_photo(db, photos_dir / name, upload_dir, household)
                db.flush()
                db.add(
                    models.RequestAttachment(
                        request_id=request.id,
                        file_id=file.id,
                        kind=AttachmentKind.TERRACE_PHOTO,
                        is_primary=order == 0,
                        sort_order=order,
                    )
                )
            request_by_code[r.code] = request

        for n, q in enumerate(quotes, start=1):
            request = _lookup(request_by_code, q.request_code, "quotes.json", "request")
            vendor = _lookup(vendor_by_phone, q.vendor_phone, "quotes.json", "vendor")
            # Quotes arrive one minute apart, so the demo shows a believable order.
            submitted = now + timedelta(minutes=n)
            quote = models.Quote(
                quote_code=q.code,
                request_id=request.id,
                vendor_id=vendor.id,
                status=QuoteStatus.SUBMITTED,
                source=QuoteSource.FORM,
                submitted_at=submitted,
                **q.model_dump(exclude={"code", "request_code", "vendor_phone", "line_items"}),
            )
            quote.line_items = [
                models.QuoteLineItem(sort_order=i, **item.model_dump())
                for i, item in enumerate(q.line_items)
            ]
            db.add(quote)
            db.flush()
            db.add(quote_financials(quote, request))
            if request.status == RequestStatus.OPEN:
                request.status = RequestStatus.QUOTED
                db.add(
                    models.RequestStatusHistory(
                        request_id=request.id,
                        from_status=RequestStatus.OPEN,
                        to_status=RequestStatus.QUOTED,
                        created_at=submitted,
                    )
                )
            request.quotes_count += 1

        db.commit()

    return {
        "rule_items": len(load_rules().citations),
        "discoms": len(discoms),
        "users": len(users),
        "vendors": len(vendors),
        "requests": len(requests),
        "quotes": len(quotes),
        "photos": sum(len(r.photos) for r in requests),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build the local database from seed files.")
    parser.add_argument("--reset", action="store_true", help="drop and rebuild every table")
    args = parser.parse_args(argv)
    settings = get_settings()
    try:
        counts = seed(get_engine(), SEED_DIR, settings.upload_dir, reset=args.reset)
    except SeedError as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    print("Seeded " + json.dumps(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
