"""The P0 tables from docs/previous/db-schema.html.

Money is whole rupees in `int`. Capacity, areas and ratios are `Numeric`, read back as `Decimal`.
Locations are `lat`/`lng` columns; production adds a PostGIS `geography` column beside them.
P1 to P3 tables are added when their features are built.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.app.db import Base, JsonDoc, UtcDateTime, str_enum, utcnow
from api.app.enums import (
    AssessmentStatus,
    AttachmentKind,
    BuildingType,
    CalculationScope,
    FilePurpose,
    InputMethod,
    InverterType,
    JobPriority,
    JobStatus,
    JobType,
    Lang,
    Level,
    LineItemType,
    LocationSource,
    ObstructionType,
    OtpPurpose,
    PanelTechnology,
    QuoteSource,
    QuoteStatus,
    RequestStatus,
    Role,
    RoofType,
    StateCategory,
    SttProvider,
    VerificationStatus,
    VoiceLanguage,
)

Json = dict[str, Any] | list[Any]


def _id() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def _fk(target: str, *, nullable: bool = False, index: bool = False) -> Mapped[Any]:
    return mapped_column(Uuid, ForeignKey(target), nullable=nullable, index=index)


def _created() -> Mapped[datetime]:
    return mapped_column(UtcDateTime(), default=utcnow)


def _updated() -> Mapped[datetime]:
    return mapped_column(UtcDateTime(), default=utcnow, onupdate=utcnow)


def _kw() -> Mapped[Any]:
    return mapped_column(Numeric(5, 2), nullable=True)


# --- Identity -------------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _id()
    role: Mapped[Role] = mapped_column(str_enum(Role), index=True)
    full_name: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str] = mapped_column(String(16), unique=True)
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    preferred_lang: Mapped[Lang] = mapped_column(str_enum(Lang), default=Lang.EN)
    avatar_file_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("files.id", use_alter=True)
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()

    vendor: Mapped["Vendor | None"] = relationship(
        back_populates="user", foreign_keys="Vendor.user_id"
    )


class AuthOtp(Base):
    __tablename__ = "auth_otps"

    id: Mapped[uuid.UUID] = _id()
    phone: Mapped[str] = mapped_column(String(16), index=True)
    code_hash: Mapped[str] = mapped_column(Text)
    purpose: Mapped[OtpPurpose] = mapped_column(str_enum(OtpPurpose))
    attempts: Mapped[int] = mapped_column(default=0)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime())
    consumed_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    created_at: Mapped[datetime] = _created()


# --- Vendors --------------------------------------------------------------------------------


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[uuid.UUID] = _id()
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), unique=True)
    company_name: Mapped[str] = mapped_column(Text)
    gstin: Mapped[str | None] = mapped_column(String(15), unique=True)
    mnre_registration_no: Mapped[str | None] = mapped_column(Text, unique=True)
    years_in_business: Mapped[int | None]
    installations_completed: Mapped[int | None]
    contact_person: Mapped[str | None] = mapped_column(Text)
    contact_phone: Mapped[str | None] = mapped_column(String(16))
    contact_email: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    base_lat: Mapped[float | None] = mapped_column(Float)
    base_lng: Mapped[float | None] = mapped_column(Float)
    service_radius_km: Mapped[int] = mapped_column(default=50)
    logo_file_id: Mapped[uuid.UUID | None] = _fk("files.id", nullable=True)
    about: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        str_enum(VerificationStatus), default=VerificationStatus.PENDING, index=True
    )
    verified_by: Mapped[uuid.UUID | None] = _fk("users.id", nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    avg_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    rating_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()

    user: Mapped[User] = relationship(back_populates="vendor", foreign_keys=[user_id])


# --- Reference and rules --------------------------------------------------------------------


class Discom(Base):
    __tablename__ = "discoms"

    id: Mapped[uuid.UUID] = _id()
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text)
    state_category: Mapped[StateCategory] = mapped_column(str_enum(StateCategory))
    net_metering_fee_inr: Mapped[int | None]
    portal_url: Mapped[str | None] = mapped_column(Text)


class DiscomTariffSlab(Base):
    __tablename__ = "discom_tariff_slabs"

    id: Mapped[uuid.UUID] = _id()
    discom_id: Mapped[uuid.UUID] = _fk("discoms.id", index=True)
    from_units: Mapped[int]
    to_units: Mapped[int | None] = mapped_column(comment="Null means no upper limit.")
    rate_per_unit_inr: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    fixed_charge_inr: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    effective_from: Mapped[date] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(Text)
    is_sample: Mapped[bool] = mapped_column(comment="Demo values; the UI labels them.")


class RuleSet(Base):
    __tablename__ = "rule_sets"

    id: Mapped[uuid.UUID] = _id()
    scheme: Mapped[str] = mapped_column(String(32))
    version: Mapped[str] = mapped_column(String(64), unique=True)
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool]
    source_checked_on: Mapped[date] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()

    __table_args__ = (
        Index(
            "uq_rule_sets_one_active",
            "scheme",
            unique=True,
            sqlite_where=text("is_active"),
            postgresql_where=text("is_active"),
        ),
    )


class RuleItem(Base):
    __tablename__ = "rule_items"

    id: Mapped[uuid.UUID] = _id()
    rule_set_id: Mapped[uuid.UUID] = _fk("rule_sets.id")
    rule_key: Mapped[str] = mapped_column(String(64))
    rule_type: Mapped[str] = mapped_column(String(32))
    applies_to: Mapped[str] = mapped_column(String(16), comment="general, special or all")
    params: Mapped[Json] = mapped_column(JsonDoc)
    description: Mapped[str] = mapped_column(Text)
    source_title: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(
        Text, comment="Null for assumptions, which the UI labels."
    )
    source_clause: Mapped[str | None] = mapped_column(Text)
    # Not in db-schema.html; the UI labels `verify` and `assumption` figures as estimates.
    status: Mapped[str] = mapped_column(String(16), comment="confirmed, verify or assumption")

    __table_args__ = (UniqueConstraint("rule_set_id", "rule_key", "applies_to"),)


# --- Platform -------------------------------------------------------------------------------


class File(Base):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = _id()
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", use_alter=True), index=True
    )
    purpose: Mapped[FilePurpose] = mapped_column(str_enum(FilePurpose))
    storage_backend: Mapped[str] = mapped_column(String(8), default="local")
    storage_key: Mapped[str] = mapped_column(Text, unique=True)
    original_name: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    width: Mapped[int | None]
    height: Mapped[int | None]
    thumbnail_key: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime())


class AiJob(Base):
    __tablename__ = "ai_jobs"

    id: Mapped[uuid.UUID] = _id()
    job_type: Mapped[JobType] = mapped_column(str_enum(JobType))
    entity_type: Mapped[str | None] = mapped_column(String(32))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    status: Mapped[JobStatus] = mapped_column(str_enum(JobStatus), default=JobStatus.QUEUED)
    priority: Mapped[JobPriority] = mapped_column(str_enum(JobPriority))
    provider: Mapped[str | None] = mapped_column(String(16))
    model: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(String(32))
    input_hash: Mapped[str] = mapped_column(String(64))
    output: Mapped[Json | None] = mapped_column(JsonDoc)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(default=0)
    tokens_in: Mapped[int | None]
    tokens_out: Mapped[int | None]
    latency_ms: Mapped[int | None]
    requested_by: Mapped[uuid.UUID | None] = _fk("users.id", nullable=True)
    queued_at: Mapped[datetime] = _created()
    started_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime())

    __table_args__ = (
        Index("ix_ai_jobs_input_hash_job_type", "input_hash", "job_type"),
        Index("ix_ai_jobs_status_priority_queued_at", "status", "priority", "queued_at"),
    )


# --- Requests and roof AI -------------------------------------------------------------------


class SolarRequest(Base):
    __tablename__ = "solar_requests"

    id: Mapped[uuid.UUID] = _id()
    request_code: Mapped[str] = mapped_column(String(20), unique=True)
    household_id: Mapped[uuid.UUID] = _fk("users.id")
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    location_source: Mapped[LocationSource] = mapped_column(str_enum(LocationSource))
    address_text: Mapped[str | None] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(Text, index=True)
    pincode: Mapped[str | None] = mapped_column(String(6))
    discom_id: Mapped[uuid.UUID | None] = _fk("discoms.id", nullable=True)
    state_category: Mapped[StateCategory] = mapped_column(str_enum(StateCategory))
    monthly_units: Mapped[int]
    monthly_bill_inr: Mapped[int | None]
    budget_inr: Mapped[int]
    roof_type: Mapped[RoofType | None] = mapped_column(str_enum(RoofType))
    roof_area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    floors: Mapped[int | None]
    building_type: Mapped[BuildingType | None] = mapped_column(str_enum(BuildingType))
    input_method: Mapped[InputMethod] = mapped_column(str_enum(InputMethod))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RequestStatus] = mapped_column(str_enum(RequestStatus))
    rule_set_id: Mapped[uuid.UUID] = _fk("rule_sets.id")
    latest_estimate_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("calculations.id", use_alter=True)
    )
    quotes_count: Mapped[int] = mapped_column(default=0)
    accepted_quote_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("quotes.id", use_alter=True)
    )
    submitted_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    closed_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()

    household: Mapped[User] = relationship(foreign_keys=[household_id])
    rule_set: Mapped[RuleSet] = relationship()
    quotes: Mapped[list["Quote"]] = relationship(
        back_populates="request", foreign_keys="Quote.request_id"
    )

    __table_args__ = (
        CheckConstraint("monthly_units > 0 AND budget_inr > 0", name="positive_inputs"),
        # Production replaces this with a partial GiST index on a PostGIS location column.
        Index("ix_solar_requests_status_lat_lng", "status", "lat", "lng"),
        Index("ix_solar_requests_household_created", "household_id", "created_at"),
    )


class RequestAttachment(Base):
    __tablename__ = "request_attachments"

    id: Mapped[uuid.UUID] = _id()
    request_id: Mapped[uuid.UUID] = _fk("solar_requests.id", index=True)
    file_id: Mapped[uuid.UUID] = _fk("files.id")
    kind: Mapped[AttachmentKind] = mapped_column(str_enum(AttachmentKind))
    is_primary: Mapped[bool] = mapped_column(default=False)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = _created()

    __table_args__ = (UniqueConstraint("request_id", "file_id"),)


class VoiceInput(Base):
    __tablename__ = "voice_inputs"

    id: Mapped[uuid.UUID] = _id()
    user_id: Mapped[uuid.UUID] = _fk("users.id")
    request_id: Mapped[uuid.UUID | None] = _fk("solar_requests.id", nullable=True)
    audio_file_id: Mapped[uuid.UUID | None] = _fk("files.id", nullable=True)
    language: Mapped[VoiceLanguage] = mapped_column(str_enum(VoiceLanguage))
    stt_provider: Mapped[SttProvider] = mapped_column(str_enum(SttProvider))
    transcript: Mapped[str | None] = mapped_column(Text)
    extracted_fields: Mapped[Json | None] = mapped_column(JsonDoc)
    ai_job_id: Mapped[uuid.UUID | None] = _fk("ai_jobs.id", nullable=True)
    applied_to_request: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = _created()


class RoofAssessment(Base):
    __tablename__ = "roof_assessments"

    id: Mapped[uuid.UUID] = _id()
    request_id: Mapped[uuid.UUID] = _fk("solar_requests.id", index=True)
    photo_file_id: Mapped[uuid.UUID] = _fk("files.id")
    ai_job_id: Mapped[uuid.UUID | None] = _fk("ai_jobs.id", nullable=True)
    status: Mapped[AssessmentStatus] = mapped_column(str_enum(AssessmentStatus))
    model: Mapped[str | None] = mapped_column(Text)
    roof_area_input_sqm: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    usable_fraction: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), comment="From LLM.")
    usable_area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), comment="From code.")
    max_kw_by_area: Mapped[Decimal | None] = _kw()
    shade_risk: Mapped[Level | None] = mapped_column(str_enum(Level))
    summary: Mapped[str | None] = mapped_column(Text)
    raw_output: Mapped[Json | None] = mapped_column(JsonDoc)
    created_at: Mapped[datetime] = _created()


class RoofObstruction(Base):
    __tablename__ = "roof_obstructions"

    id: Mapped[uuid.UUID] = _id()
    assessment_id: Mapped[uuid.UUID] = _fk("roof_assessments.id", index=True)
    obstruction_type: Mapped[ObstructionType] = mapped_column(str_enum(ObstructionType))
    # Box position and size as fractions of the image, 0 to 1.
    bbox_x: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    bbox_y: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    bbox_w: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    bbox_h: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    severity: Mapped[Level | None] = mapped_column(str_enum(Level))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    note: Mapped[str | None] = mapped_column(Text)


class Calculation(Base):
    """Every number the rules engine produces, with its steps and the rule set it used."""

    __tablename__ = "calculations"

    id: Mapped[uuid.UUID] = _id()
    scope: Mapped[CalculationScope] = mapped_column(str_enum(CalculationScope))
    request_id: Mapped[uuid.UUID] = _fk("solar_requests.id", index=True)
    quote_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("quotes.id", use_alter=True), unique=True
    )
    rule_set_id: Mapped[uuid.UUID] = _fk("rule_sets.id")
    recommended_kw: Mapped[Decimal | None] = _kw()
    kw_band_min: Mapped[Decimal | None] = _kw()
    kw_band_max: Mapped[Decimal | None] = _kw()
    roof_cap_kw: Mapped[Decimal | None] = _kw()
    system_kw: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    gross_cost_inr: Mapped[int | None]
    subsidy_inr: Mapped[int]
    net_cost_inr: Mapped[int | None]
    annual_generation_kwh: Mapped[int | None]
    monthly_savings_inr: Mapped[int | None]
    annual_savings_inr: Mapped[int | None]
    bill_reduction_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    payback_years: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    savings_25y_inr: Mapped[int | None]
    inputs_snapshot: Mapped[Json] = mapped_column(JsonDoc)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JsonDoc)
    # Not in db-schema.html: some rules back a result without appearing in one step.
    citation_keys: Mapped[list[str]] = mapped_column(JsonDoc)
    engine_version: Mapped[str] = mapped_column(String(32))
    computed_at: Mapped[datetime] = _created()

    __table_args__ = (
        CheckConstraint(
            "scope <> 'quote_financials' OR quote_id IS NOT NULL", name="quote_has_quote_id"
        ),
    )


class RequestStatusHistory(Base):
    __tablename__ = "request_status_history"

    id: Mapped[uuid.UUID] = _id()
    request_id: Mapped[uuid.UUID] = _fk("solar_requests.id", index=True)
    from_status: Mapped[RequestStatus | None] = mapped_column(str_enum(RequestStatus))
    to_status: Mapped[RequestStatus] = mapped_column(str_enum(RequestStatus))
    changed_by: Mapped[uuid.UUID | None] = _fk("users.id", nullable=True)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()


# --- Quotes and decision --------------------------------------------------------------------


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[uuid.UUID] = _id()
    quote_code: Mapped[str] = mapped_column(String(20), unique=True)
    request_id: Mapped[uuid.UUID] = _fk("solar_requests.id")
    vendor_id: Mapped[uuid.UUID] = _fk("vendors.id")
    status: Mapped[QuoteStatus] = mapped_column(str_enum(QuoteStatus))
    system_kw: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    price_total_inr: Mapped[int]
    gst_included: Mapped[bool]
    gst_amount_inr: Mapped[int | None]
    panel_component_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, comment="Links to components once that P2 table exists."
    )
    panel_brand: Mapped[str] = mapped_column(Text)
    panel_model: Mapped[str | None] = mapped_column(Text)
    panel_technology: Mapped[PanelTechnology | None] = mapped_column(str_enum(PanelTechnology))
    panel_wattage: Mapped[int | None]
    panel_count: Mapped[int | None]
    panel_efficiency_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    dcr_compliant: Mapped[bool]
    panel_product_warranty_yrs: Mapped[int | None]
    panel_performance_warranty_yrs: Mapped[int | None]
    inverter_component_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    inverter_brand: Mapped[str] = mapped_column(Text)
    inverter_model: Mapped[str | None] = mapped_column(Text)
    inverter_type: Mapped[InverterType | None] = mapped_column(str_enum(InverterType))
    inverter_capacity_kw: Mapped[Decimal | None] = _kw()
    inverter_warranty_yrs: Mapped[int | None]
    workmanship_warranty_yrs: Mapped[int | None]
    amc_years: Mapped[int | None]
    timeline_days: Mapped[int]
    valid_until: Mapped[date | None] = mapped_column(Date)
    payment_terms: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text, comment="Untrusted; never sent to ranking.")
    source: Mapped[QuoteSource] = mapped_column(str_enum(QuoteSource))
    source_file_id: Mapped[uuid.UUID | None] = _fk("files.id", nullable=True)
    generated_pdf_file_id: Mapped[uuid.UUID | None] = _fk("files.id", nullable=True)
    injection_flag: Mapped[bool] = mapped_column(default=False)
    injection_reason: Mapped[str | None] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(default=1)
    submitted_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    decided_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _updated()

    request: Mapped[SolarRequest] = relationship(back_populates="quotes", foreign_keys=[request_id])
    vendor: Mapped[Vendor] = relationship()
    line_items: Mapped[list["QuoteLineItem"]] = relationship(
        order_by="QuoteLineItem.sort_order", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("request_id", "vendor_id"),
        # The database itself refuses a second accepted quote, even if two accepts race.
        Index(
            "uq_quotes_one_accepted",
            "request_id",
            unique=True,
            sqlite_where=text("status = 'accepted'"),
            postgresql_where=text("status = 'accepted'"),
        ),
        Index("ix_quotes_request_status", "request_id", "status"),
        Index("ix_quotes_vendor_status", "vendor_id", "status"),
    )


class QuoteLineItem(Base):
    __tablename__ = "quote_line_items"

    id: Mapped[uuid.UUID] = _id()
    quote_id: Mapped[uuid.UUID] = _fk("quotes.id", index=True)
    item_type: Mapped[LineItemType] = mapped_column(str_enum(LineItemType))
    description: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    unit: Mapped[str | None] = mapped_column(String(8))
    unit_price_inr: Mapped[int | None]
    amount_inr: Mapped[int | None]
    included: Mapped[bool] = mapped_column(comment="False means listed as excluded.")
    sort_order: Mapped[int] = mapped_column(default=0)


class QuoteReview(Base):
    __tablename__ = "quote_reviews"

    id: Mapped[uuid.UUID] = _id()
    quote_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("quotes.id"), unique=True)
    rule_set_id: Mapped[uuid.UUID] = _fk("rule_sets.id")
    checklist_version: Mapped[str] = mapped_column(String(32))
    missing_items: Mapped[Json] = mapped_column(JsonDoc, comment="From code.")
    warnings: Mapped[Json | None] = mapped_column(JsonDoc)
    injection_detected: Mapped[bool]
    injection_excerpt: Mapped[str | None] = mapped_column(Text)
    llm_notes: Mapped[str | None] = mapped_column(Text, comment="Explanations only, no numbers.")
    ai_job_id: Mapped[uuid.UUID | None] = _fk("ai_jobs.id", nullable=True)
    reviewed_at: Mapped[datetime] = _created()


class QuoteScore(Base):
    __tablename__ = "quote_scores"

    id: Mapped[uuid.UUID] = _id()
    quote_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("quotes.id"), unique=True)
    scoring_version: Mapped[str] = mapped_column(String(32))
    total_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    price_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    panel_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    inverter_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    warranty_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    timeline_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    completeness_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    vendor_rating_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    weights: Mapped[Json] = mapped_column(JsonDoc)
    explanation: Mapped[Json] = mapped_column(JsonDoc)
    computed_at: Mapped[datetime] = _created()


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = _id()
    request_id: Mapped[uuid.UUID] = _fk("solar_requests.id", index=True)
    recommended_quote_id: Mapped[uuid.UUID] = _fk("quotes.id")
    quotes_fingerprint: Mapped[str] = mapped_column(String(64))
    ranking: Mapped[Json] = mapped_column(JsonDoc, comment="From code.")
    reasons: Mapped[Json] = mapped_column(JsonDoc, comment="LLM text from the score table only.")
    caveats: Mapped[str | None] = mapped_column(Text)
    ai_job_id: Mapped[uuid.UUID | None] = _fk("ai_jobs.id", nullable=True)
    model: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()
