"""HTTP contract. Field names follow docs/previous/db-schema.html; web types are generated from it.

Money is whole rupees in `int`. Capacity is `Decimal` kW, which JSON carries as a string.
Every number in a response comes from `rules/`. The LLM only fills text fields.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Generic, Literal, Self, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from api.app.enums import (
    AssessmentStatus,
    AttachmentKind,
    BuildingType,
    CalculationScope,
    FilePurpose,
    InputMethod,
    InverterType,
    JobStatus,
    JobType,
    Lang,
    Level,
    LineItemType,
    LocationSource,
    ObstructionType,
    PanelTechnology,
    QuoteStatus,
    RequestStatus,
    Role,
    RoofType,
    StateCategory,
    VerificationStatus,
    VoiceLanguage,
)
from rules.loader import PaybackRules, ScoringRules, SizingRules, SubsidyRules

# --- Shared -------------------------------------------------------------------------------


class Input(BaseModel):
    """Request bodies. Unknown keys are rejected, so a client cannot slip in a score or status."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


Rupees = Annotated[int, Field(strict=True, gt=0)]
Kw = Annotated[Decimal, Field(gt=0, le=100, max_digits=5, decimal_places=2)]
Years = Annotated[int, Field(ge=0, le=40)]
Lat = Annotated[float, Field(ge=-90, le=90)]
Lng = Annotated[float, Field(ge=-180, le=180)]


class ErrorBody(Output):
    code: str
    message: str
    details: list[dict[str, object]] | dict[str, object] | None = None


class ErrorResponse(Output):
    error: ErrorBody


T = TypeVar("T")


# Generic[T] rather than PEP 695 syntax, because the code must also run on Python 3.11.
class Page(Output, Generic[T]):
    items: list[T]
    next_cursor: str | None = Field(None, description="Pass back as `cursor` for the next page.")


class CitationOut(Output):
    key: str
    title: str
    source: str
    url: str | None
    status: Literal["confirmed", "verify", "assumption"]


class Cited(Output):
    """Every calculated result names the rule version that produced it and each rule's source."""

    rule_version: str
    citations: list[CitationOut]


class BBox(BaseModel):
    """Map viewport as `west,south,east,north` in degrees, the order Leaflet's toBBoxString uses."""

    west: float = Field(ge=-180, le=180)
    south: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)

    @classmethod
    def parse(cls, raw: str) -> Self:
        parts = raw.split(",")
        if len(parts) != 4:
            raise ValueError("bbox needs four numbers: west,south,east,north")
        try:
            west, south, east, north = (float(p) for p in parts)
        except ValueError:
            raise ValueError("bbox values must be numbers") from None
        if west >= east or south >= north:
            raise ValueError("bbox must have west < east and south < north")
        try:
            return cls(west=west, south=south, east=east, north=north)
        except ValueError:
            raise ValueError("bbox values are out of range") from None


class JobAccepted(Output):
    """Returned with 202. Follow progress on `GET /jobs/{id}` or the SSE stream."""

    job_id: UUID
    job_type: JobType
    status: JobStatus
    entity_id: UUID | None = Field(None, description="The row the job will fill in.")


# --- Auth -----------------------------------------------------------------------------------

Phone = Annotated[str, Field(pattern=r"^\+[1-9]\d{7,14}$", description="E.164, e.g. +919812345678")]


class OtpRequest(Input):
    phone: Phone


class OtpSent(Output):
    expires_in_s: int


class VerifyRequest(Input):
    phone: Phone
    code: str = Field(pattern=r"^\d{6}$")
    role: Literal[Role.HOUSEHOLD, Role.VENDOR] | None = Field(
        None, description="Required the first time a phone signs in; ignored afterwards."
    )
    full_name: str | None = Field(None, min_length=1, max_length=100)
    preferred_lang: Lang = Lang.EN


class UserOut(Output):
    id: UUID
    role: Role
    full_name: str | None
    phone: str
    preferred_lang: Lang


class TokenResponse(Output):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_in_s: int
    user: UserOut


# --- Files ----------------------------------------------------------------------------------

_IMAGES = frozenset({"image/jpeg", "image/png", "image/webp"})
ALLOWED_CONTENT_TYPES: dict[FilePurpose, frozenset[str]] = {
    FilePurpose.TERRACE_PHOTO: _IMAGES,
    FilePurpose.ELECTRICITY_BILL: _IMAGES | {"application/pdf"},
    FilePurpose.VOICE_AUDIO: frozenset(
        {"audio/webm", "audio/ogg", "audio/mpeg", "audio/wav", "audio/mp4"}
    ),
    FilePurpose.QUOTE_DOCUMENT: _IMAGES | {"application/pdf"},
}
MAX_UPLOAD_BYTES: dict[FilePurpose, int] = {
    FilePurpose.TERRACE_PHOTO: 8 * 1024 * 1024,
    FilePurpose.ELECTRICITY_BILL: 8 * 1024 * 1024,
    FilePurpose.VOICE_AUDIO: 10 * 1024 * 1024,
    FilePurpose.QUOTE_DOCUMENT: 10 * 1024 * 1024,
}


def check_upload(purpose: FilePurpose, content_type: str, size_bytes: int) -> None:
    """Raises ValueError when a file does not fit its purpose. The upload route calls this."""
    if purpose not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"{purpose} files cannot be uploaded here")
    if content_type not in ALLOWED_CONTENT_TYPES[purpose]:
        raise ValueError(f"{content_type} is not allowed for {purpose}")
    if not 0 < size_bytes <= MAX_UPLOAD_BYTES[purpose]:
        raise ValueError(f"{purpose} files must be 1 to {MAX_UPLOAD_BYTES[purpose]} bytes")


class FileOut(Output):
    id: UUID
    purpose: FilePurpose
    mime_type: str
    size_bytes: int
    sha256: str
    width: int | None = None
    height: int | None = None
    url: str = Field(description="`GET /files/{id}` with the bearer token.")


# --- Voice ----------------------------------------------------------------------------------


class VoiceTranscribeRequest(Input):
    audio_file_id: UUID
    language: VoiceLanguage


class PrefillFields(Output):
    """What the LLM heard. The household confirms each value; nothing is posted automatically."""

    monthly_units: int | None = Field(None, gt=0)
    monthly_bill_inr: int | None = Field(None, gt=0)
    budget_inr: int | None = Field(None, gt=0)
    roof_type: RoofType | None = None
    roof_area_sqm: Decimal | None = Field(None, gt=0)
    floors: int | None = Field(None, ge=0, le=100)
    address_hint: str | None = None


class VoiceResult(Output):
    kind: Literal["voice_extract"] = "voice_extract"
    voice_input_id: UUID
    language: VoiceLanguage
    transcript: str
    extracted_fields: PrefillFields


# --- Calculations ---------------------------------------------------------------------------


class CalcStep(Output):
    """One line of working, rendered in the UI with an ⓘ link to its rule."""

    label: str
    formula: str
    value: str
    rule_key: str | None = Field(None, description="Key into `citations`; empty for arithmetic.")


class CalculationOut(Cited):
    """A row of `calculations`: the request estimate, or one quote's financials."""

    id: UUID
    scope: CalculationScope
    system_kw: Decimal
    recommended_kw: Decimal | None
    kw_band_min: Decimal | None
    kw_band_max: Decimal | None
    roof_cap_kw: Decimal | None
    gross_cost_inr: int | None
    subsidy_inr: int
    net_cost_inr: int | None
    annual_generation_kwh: int | None
    monthly_savings_inr: int | None
    annual_savings_inr: int | None
    bill_reduction_pct: Decimal | None
    payback_years: Decimal | None = Field(description="Empty when the system saves nothing.")
    savings_25y_inr: int | None
    steps: list[CalcStep]
    engine_version: str
    computed_at: datetime


# --- Requests -------------------------------------------------------------------------------


class RequestCreate(Input):
    lat: Lat
    lng: Lng
    location_source: LocationSource
    address_text: str | None = Field(None, max_length=300)
    district: str | None = Field(None, max_length=80)
    pincode: str | None = Field(None, pattern=r"^\d{6}$")
    discom_id: UUID | None = Field(
        None, description="Sets the subsidy category. Without it, the general rates apply."
    )
    monthly_units: int = Field(gt=0, le=100_000)
    monthly_bill_inr: int | None = Field(None, gt=0)
    budget_inr: Rupees
    roof_type: RoofType | None = None
    roof_area_sqm: Decimal = Field(gt=0, le=10_000, max_digits=7, decimal_places=2)
    floors: int | None = Field(None, ge=0, le=100)
    building_type: BuildingType | None = None
    input_method: InputMethod = InputMethod.FORM
    notes: str | None = Field(None, max_length=1000)
    photo_file_ids: list[UUID] = Field(default_factory=list, max_length=3)
    bill_file_id: UUID | None = None
    voice_input_id: UUID | None = None


class ObstructionOut(Output):
    obstruction_type: ObstructionType
    bbox_x: Decimal | None = Field(description="Box position and size as fractions of the image.")
    bbox_y: Decimal | None
    bbox_w: Decimal | None
    bbox_h: Decimal | None
    severity: Level | None
    confidence: Decimal | None
    note: str | None


class RoofAssessmentOut(Output):
    """`usable_fraction` and obstructions come from the LLM; areas and the kW cap from code."""

    kind: Literal["photo_assess"] = "photo_assess"
    id: UUID
    status: AssessmentStatus
    usable_fraction: Decimal | None
    usable_area_sqm: Decimal | None
    max_kw_by_area: Decimal | None
    shade_risk: Level | None
    summary: str | None
    obstructions: list[ObstructionOut]


class AttachmentOut(Output):
    id: UUID
    file_id: UUID
    kind: AttachmentKind
    is_primary: bool
    url: str


class RequestBase(Output):
    id: UUID
    request_code: str
    status: RequestStatus
    district: str | None
    state_category: StateCategory
    monthly_units: int
    budget_inr: int
    roof_type: RoofType | None
    roof_area_sqm: Decimal | None
    floors: int | None
    building_type: BuildingType | None
    estimate: CalculationOut
    roof_assessment: RoofAssessmentOut | None
    attachments: list[AttachmentOut]
    quotes_count: int
    submitted_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


class RequestOut(RequestBase):
    """The household's own view."""

    view: Literal["owner"] = "owner"
    lat: float
    lng: float
    location_source: LocationSource
    address_text: str | None
    pincode: str | None
    discom_id: UUID | None
    monthly_bill_inr: int | None
    input_method: InputMethod
    notes: str | None
    accepted_quote_id: UUID | None
    closed_at: datetime | None


class RequestSummary(Output):
    id: UUID
    request_code: str
    status: RequestStatus
    monthly_units: int
    system_kw: Decimal
    quotes_count: int
    created_at: datetime


class HouseholdContact(Output):
    """Shared with a vendor only after that vendor's quote is accepted."""

    full_name: str | None
    phone: str
    lat: float
    lng: float
    address_text: str | None


class VendorRequestView(RequestBase):
    """A vendor's view. The location is rounded to about 500 m and there is no phone number."""

    view: Literal["vendor"] = "vendor"
    approx_lat: float
    approx_lng: float
    distance_km: Decimal
    my_quote_id: UUID | None
    contact: HouseholdContact | None = Field(
        None, description="Set once this vendor's quote is accepted."
    )


class OpenRequestPin(Output):
    id: UUID
    request_code: str
    approx_lat: float
    approx_lng: float
    distance_km: Decimal
    district: str | None
    monthly_units: int
    budget_inr: int
    recommended_kw: Decimal
    roof_area_sqm: Decimal | None
    quotes_count: int
    submitted_at: datetime | None


# --- Quotes ---------------------------------------------------------------------------------


class LineItemIn(Input):
    item_type: LineItemType
    description: str | None = Field(None, max_length=200)
    quantity: Decimal | None = Field(None, gt=0, max_digits=8, decimal_places=2)
    unit: Literal["nos", "m", "set", "lot"] | None = None
    unit_price_inr: int | None = Field(None, ge=0)
    amount_inr: int | None = Field(None, ge=0)
    included: bool = Field(True, description="False lists the item as excluded.")


class LineItemOut(Output):
    id: UUID
    item_type: LineItemType
    description: str | None
    quantity: Decimal | None
    unit: str | None
    unit_price_inr: int | None
    amount_inr: int | None
    included: bool


class QuoteCreate(Input):
    system_kw: Kw
    price_total_inr: Rupees
    gst_included: bool
    gst_amount_inr: int | None = Field(None, ge=0)
    panel_brand: str = Field(min_length=1, max_length=80)
    panel_model: str | None = Field(None, max_length=80)
    panel_technology: PanelTechnology | None = None
    panel_wattage: int | None = Field(None, ge=100, le=1000)
    panel_count: int | None = Field(None, ge=1, le=1000)
    panel_efficiency_pct: Decimal | None = Field(None, gt=0, le=40)
    dcr_compliant: bool = Field(description="Domestic content panels, required for the subsidy.")
    panel_product_warranty_yrs: Years | None = None
    panel_performance_warranty_yrs: Years | None = None
    inverter_brand: str = Field(min_length=1, max_length=80)
    inverter_model: str | None = Field(None, max_length=80)
    inverter_type: InverterType | None = None
    inverter_capacity_kw: Kw | None = None
    inverter_warranty_yrs: Years | None = None
    workmanship_warranty_yrs: Years | None = None
    amc_years: Years | None = None
    timeline_days: int = Field(ge=1, le=365)
    valid_until: date | None = None
    payment_terms: str | None = Field(None, max_length=500)
    line_items: list[LineItemIn] = Field(default_factory=list, max_length=40)
    notes: str | None = Field(
        None, max_length=2000, description="Untrusted. Shown to the household, never used to rank."
    )


class VendorSummary(Output):
    id: UUID
    company_name: str
    mnre_registration_no: str | None
    avg_rating: Decimal | None
    rating_count: int
    verification_status: VerificationStatus


class VendorContact(Output):
    company_name: str
    contact_person: str | None
    contact_phone: str | None
    contact_email: str | None


class MissingItem(Output):
    item: str
    severity: Level
    why: str


class QuoteReviewOut(Output):
    """`missing_items`, `warnings` and the injection check come from code; `llm_notes` is text."""

    kind: Literal["quote_review"] = "quote_review"
    llm_status: JobStatus
    missing_items: list[MissingItem]
    warnings: list[str]
    injection_detected: bool
    injection_excerpt: str | None
    llm_notes: str | None
    reviewed_at: datetime


class ScoreLine(Output):
    criterion: str
    input: str
    formula: str
    points: Decimal


class QuoteScoreOut(Output):
    total_score: Decimal = Field(description="0 to 100, from `rules.scoring`.")
    weights: dict[str, int]
    explanation: list[ScoreLine]


class QuoteOut(Output):
    id: UUID
    quote_code: str
    request_id: UUID
    vendor: VendorSummary
    status: QuoteStatus
    system_kw: Decimal
    price_total_inr: int
    gst_included: bool
    gst_amount_inr: int | None
    panel_brand: str
    panel_model: str | None
    panel_technology: PanelTechnology | None
    panel_wattage: int | None
    panel_count: int | None
    panel_efficiency_pct: Decimal | None
    dcr_compliant: bool
    panel_product_warranty_yrs: int | None
    panel_performance_warranty_yrs: int | None
    inverter_brand: str
    inverter_model: str | None
    inverter_type: InverterType | None
    inverter_capacity_kw: Decimal | None
    inverter_warranty_yrs: int | None
    workmanship_warranty_yrs: int | None
    amc_years: int | None
    timeline_days: int
    valid_until: date | None
    payment_terms: str | None
    line_items: list[LineItemOut]
    notes: str | None
    injection_flag: bool
    revision: int
    financials: CalculationOut
    review: QuoteReviewOut | None
    score: QuoteScoreOut | None
    submitted_at: datetime | None


class QuoteCreated(Output):
    quote: QuoteOut
    review_job_id: UUID


class QuoteComparison(Cited):
    """All quotes on one request, ranked by `rules.scoring`. Capped at 50 quotes per request."""

    request_id: UUID
    quotes: list[QuoteOut]
    top_quote_id: UUID | None


class VendorQuoteSummary(Output):
    id: UUID
    quote_code: str
    request_id: UUID
    request_code: str
    status: QuoteStatus
    price_total_inr: int
    system_kw: Decimal
    submitted_at: datetime | None
    contact: HouseholdContact | None = Field(None, description="Set once this quote is accepted.")


class RankedQuote(Output):
    quote_id: UUID
    rank: int
    score: Decimal


class RecommendationOut(Cited):
    """Ranking from `rules.scoring`. The LLM writes the reasons from the score table only."""

    kind: Literal["recommend"] = "recommend"
    id: UUID
    request_id: UUID
    recommended_quote_id: UUID
    ranking: list[RankedQuote]
    reasons: list[str]
    caveats: str | None
    stale: bool = Field(description="True when quotes changed since this was written.")
    created_at: datetime


class AcceptResult(Output):
    request_id: UUID
    request_status: RequestStatus
    accepted_quote_id: UUID
    rejected_quote_ids: list[UUID]
    vendor_contact: VendorContact


# --- Jobs, events, rules --------------------------------------------------------------------

JobOutput = Annotated[
    VoiceResult | RoofAssessmentOut | QuoteReviewOut | RecommendationOut,
    Field(discriminator="kind"),
]


class JobOut(Output):
    id: UUID
    job_type: JobType
    status: JobStatus
    entity_type: str | None
    entity_id: UUID | None
    attempts: int
    output: JobOutput | None = None
    error: str | None = None
    queued_at: datetime
    finished_at: datetime | None = None


class Event(Output):
    """One SSE message. The `event:` line carries `type`; the `data:` line carries this JSON."""

    type: Literal[
        "quote.submitted",
        "quote.reviewed",
        "quote.accepted",
        "quote.rejected",
        "request.updated",
        "recommendation.ready",
        "job.finished",
    ]
    request_id: UUID | None = None
    quote_id: UUID | None = None
    job_id: UUID | None = None


class RulesOut(Output):
    version: str
    effective_from: date
    checked_on: date
    subsidy: SubsidyRules
    sizing: SizingRules
    payback: PaybackRules
    scoring: ScoringRules
    citations: list[CitationOut]
