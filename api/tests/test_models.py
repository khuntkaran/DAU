"""The P0 tables from docs/previous/db-schema.html, created on a real SQLite database."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app import models
from api.app.db import Base, enable_sqlite_foreign_keys
from api.app.enums import QuoteStatus, RequestStatus, Role

P0_TABLES = {
    "users",
    "auth_otps",
    "vendors",
    "discoms",
    "discom_tariff_slabs",
    "rule_sets",
    "rule_items",
    "files",
    "solar_requests",
    "request_attachments",
    "voice_inputs",
    "roof_assessments",
    "roof_obstructions",
    "calculations",
    "request_status_history",
    "quotes",
    "quote_line_items",
    "quote_reviews",
    "quote_scores",
    "recommendations",
    "ai_jobs",
}


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = create_engine("sqlite://")
    event.listen(engine, "connect", enable_sqlite_foreign_keys)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def _now() -> datetime:
    return datetime.now(UTC)


def _request_with_two_quotes(db: Session) -> tuple[models.SolarRequest, list[models.Quote]]:
    household = models.User(role=Role.HOUSEHOLD, full_name="Asha", phone="+919800000001")
    rule_set = models.RuleSet(
        scheme="pm_surya_ghar",
        version="pm_surya_ghar_v2024_03",
        effective_from=_now().date(),
        is_active=True,
        source_checked_on=_now().date(),
    )
    request = models.SolarRequest(
        request_code="SR-2026-000001",
        household=household,
        lat=23.0225,
        lng=72.5714,
        location_source="map_pin",
        state_category="general",
        monthly_units=330,
        budget_inr=200000,
        input_method="form",
        status=RequestStatus.QUOTED,
        rule_set=rule_set,
    )
    quotes = []
    for n in (1, 2):
        user = models.User(role=Role.VENDOR, full_name=f"V{n}", phone=f"+91980000001{n}")
        vendor = models.Vendor(user=user, company_name=f"Surya {n}", service_radius_km=50)
        quotes.append(
            models.Quote(
                quote_code=f"Q-2026-00000{n}",
                request=request,
                vendor=vendor,
                status=QuoteStatus.SUBMITTED,
                system_kw=Decimal(3),
                price_total_inr=185000,
                gst_included=True,
                panel_brand="Waaree",
                dcr_compliant=True,
                inverter_brand="Growatt",
                timeline_days=21,
                source="form",
            )
        )
    db.add_all([request, *quotes])
    db.commit()
    return request, quotes


def test_every_p0_table_is_created(engine: Engine) -> None:
    assert set(inspect(engine).get_table_names()) == P0_TABLES


def test_ids_are_uuids_and_timestamps_are_set(db: Session) -> None:
    request, _ = _request_with_two_quotes(db)

    assert isinstance(request.id, uuid.UUID)
    assert request.created_at is not None
    assert request.quotes_count == 0


def test_a_vendor_quotes_a_request_only_once(db: Session) -> None:
    request, quotes = _request_with_two_quotes(db)
    duplicate = models.Quote(
        quote_code="Q-2026-000009",
        request=request,
        vendor=quotes[0].vendor,
        status=QuoteStatus.SUBMITTED,
        system_kw=Decimal(3),
        price_total_inr=180000,
        gst_included=True,
        panel_brand="Waaree",
        dcr_compliant=True,
        inverter_brand="Growatt",
        timeline_days=20,
        source="form",
    )
    db.add(duplicate)

    with pytest.raises(IntegrityError):
        db.commit()


def test_a_request_cannot_have_two_accepted_quotes(db: Session) -> None:
    _, quotes = _request_with_two_quotes(db)
    quotes[0].status = QuoteStatus.ACCEPTED
    db.commit()

    quotes[1].status = QuoteStatus.ACCEPTED
    with pytest.raises(IntegrityError):
        db.commit()


def test_foreign_keys_are_enforced(db: Session) -> None:
    db.add(models.RequestStatusHistory(request_id=uuid.uuid4(), to_status=RequestStatus.OPEN))

    with pytest.raises(IntegrityError):
        db.commit()


def test_status_columns_store_the_lowercase_values(db: Session, engine: Engine) -> None:
    _request_with_two_quotes(db)

    with engine.connect() as conn:
        status = conn.exec_driver_sql("SELECT status FROM solar_requests").scalar_one()

    assert status == "quoted"


def test_money_is_whole_rupees_and_capacity_is_decimal(db: Session) -> None:
    _, quotes = _request_with_two_quotes(db)
    db.expire_all()

    quote = db.get(models.Quote, quotes[0].id)
    assert quote is not None
    assert quote.price_total_inr == 185000
    assert quote.system_kw == Decimal("3.00")
