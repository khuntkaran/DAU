"""HTTP contract from section 08 of the architecture. The web types are generated from this.

Money is whole rupees in `int`. Capacity is `Decimal` kW, which JSON carries as a string.
Every number in a response comes from `rules/`. The LLM only fills text fields.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Generic, Literal, Self, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from rules.loader import PaybackRules, ScoringRules, SizingRules, StateCategory, SubsidyRules

# --- Shared -------------------------------------------------------------------------------


class Input(BaseModel):
    """Request bodies. Unknown keys are rejected, so a client cannot slip in a score or status."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


Role = Literal["household", "vendor", "admin"]
Lang = Literal["en", "hi", "gu"]
RoofType = Literal["rcc_flat", "sloped", "tin_sheet", "other"]
Inclusion = Literal[
    "net_metering_fee",
    "mounting_structure",
    "earthing_and_lightning_arrester",
    "amc",
    "insurance",
    "cabling",
    "acdb_dcdb",
    "transport",
]
Rupees = Annotated[int, Field(strict=True, gt=0)]
Kw = Annotated[Decimal, Field(gt=0, le=100, max_digits=6, decimal_places=2)]
Years = Annotated[int, Field(ge=0, le=40)]


class RequestStatus(StrEnum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    QUOTED = "QUOTED"
    ACCEPTED = "ACCEPTED"
    INSTALLED = "INSTALLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class QuoteStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobType(StrEnum):
    PHOTO_ASSESS = "photo_assess"
    VOICE_EXTRACT = "voice_extract"
    QUOTE_REVIEW = "quote_review"
    RECOMMEND = "recommend"


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


class GeoPoint(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


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
    type: JobType
    status: JobStatus


# --- Auth -----------------------------------------------------------------------------------

Phone = Annotated[str, Field(pattern=r"^\+[1-9]\d{7,14}$", description="E.164, e.g. +919812345678")]


class OtpRequest(Input):
    phone: Phone


class OtpSent(Output):
    expires_in_s: int


class VerifyRequest(Input):
    phone: Phone
    code: str = Field(pattern=r"^\d{6}$")
    role: Literal["household", "vendor"] | None = Field(
        None, description="Required the first time a phone signs in; ignored afterwards."
    )
    name: str | None = Field(None, min_length=1, max_length=100)
    lang: Lang = "en"


class UserOut(Output):
    id: UUID
    role: Role
    name: str | None
    phone: str
    lang: Lang


class TokenResponse(Output):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_in_s: int
    user: UserOut


# --- Uploads --------------------------------------------------------------------------------

UploadKind = Literal["photo", "audio", "quote_doc"]
ALLOWED_CONTENT_TYPES: dict[str, frozenset[str]] = {
    "photo": frozenset({"image/jpeg", "image/png", "image/webp"}),
    "audio": frozenset({"audio/webm", "audio/ogg", "audio/mpeg", "audio/wav", "audio/mp4"}),
    "quote_doc": frozenset({"application/pdf", "image/jpeg", "image/png"}),
}
MAX_UPLOAD_BYTES: dict[str, int] = {
    "photo": 8 * 1024 * 1024,
    "audio": 10 * 1024 * 1024,
    "quote_doc": 10 * 1024 * 1024,
}


class PresignRequest(Input):
    kind: UploadKind
    content_type: str
    size_bytes: int = Field(gt=0)

    @model_validator(mode="after")
    def _type_and_size_fit_the_kind(self) -> Self:
        if self.content_type not in ALLOWED_CONTENT_TYPES[self.kind]:
            raise ValueError(f"{self.content_type} is not allowed for {self.kind}")
        if self.size_bytes > MAX_UPLOAD_BYTES[self.kind]:
            raise ValueError(
                f"{self.kind} uploads are limited to {MAX_UPLOAD_BYTES[self.kind]} bytes"
            )
        return self


class PresignResponse(Output):
    object_key: str
    upload_url: str
    method: Literal["PUT"] = "PUT"
    headers: dict[str, str] = Field(description="Send these headers with the PUT unchanged.")
    expires_in_s: int


class MediaOut(Output):
    id: UUID
    kind: Literal["photo", "audio"]
    url: str = Field(description="Short-lived signed GET URL.")


# --- Voice ----------------------------------------------------------------------------------


class VoiceTranscribeRequest(Input):
    object_key: str = Field(min_length=1, max_length=300)
    lang: Lang


class PrefillFields(Output):
    """What the LLM heard. The household confirms each value; nothing is posted automatically."""

    monthly_units: int | None = Field(None, gt=0)
    monthly_bill_inr: int | None = Field(None, gt=0)
    budget_inr: int | None = Field(None, gt=0)
    roof_type: RoofType | None = None
    floors: int | None = Field(None, ge=0, le=100)
    address_hint: str | None = None


class VoiceResult(Output):
    kind: Literal["voice_extract"] = "voice_extract"
    lang: Lang
    transcript: str
    fields: PrefillFields


# --- Requests -------------------------------------------------------------------------------


class RequestCreate(Input):
    location: GeoPoint
    address_text: str | None = Field(None, max_length=300)
    discom: str | None = Field(None, max_length=50)
    state_category: StateCategory
    monthly_units: int = Field(gt=0, le=100_000)
    monthly_bill_inr: int | None = Field(None, gt=0)
    budget_inr: Rupees
    roof_area_m2: Decimal = Field(gt=0, le=10_000, max_digits=7, decimal_places=2)
    roof_type: RoofType
    floors: int | None = Field(None, ge=0, le=100)
    photo_keys: list[str] = Field(default_factory=list, max_length=3)
    audio_key: str | None = None
    notes: str | None = Field(None, max_length=1000)


class Estimate(Cited):
    """Calculated by `rules.sizing` and `rules.subsidy` when the request is created."""

    raw_kw: Decimal
    size_kw: Decimal
    max_kw: Decimal
    capped_by_roof: bool
    subsidy_inr: int


class Obstruction(Output):
    type: Literal[
        "water_tank",
        "staircase_room",
        "parapet",
        "tree_shade",
        "dish_antenna",
        "solar_heater",
        "other",
    ]
    x: float = Field(ge=0, le=1, description="Box position and size as fractions of the image.")
    y: float = Field(ge=0, le=1)
    w: float = Field(ge=0, le=1)
    h: float = Field(ge=0, le=1)
    severity: Literal["low", "medium", "high"]


class PhotoAssessment(Output):
    """`usable_fraction` and the obstructions come from the LLM; the areas and kW cap from code."""

    kind: Literal["photo_assess"] = "photo_assess"
    status: JobStatus
    usable_fraction: Decimal | None = None
    usable_area_m2: Decimal | None = None
    max_kw: Decimal | None = None
    shade_risk: Literal["low", "medium", "high"] | None = None
    obstructions: list[Obstruction] = Field(default_factory=list)
    summary: str | None = None


class RequestBase(Output):
    id: UUID
    status: RequestStatus
    state_category: StateCategory
    monthly_units: int
    budget_inr: int
    roof_area_m2: Decimal
    roof_type: RoofType
    floors: int | None
    estimate: Estimate
    photo_assessment: PhotoAssessment | None
    photos: list[MediaOut]
    quotes_count: int
    created_at: datetime
    expires_at: datetime | None


class RequestOut(RequestBase):
    """The household's own view."""

    view: Literal["owner"] = "owner"
    location: GeoPoint
    address_text: str | None
    discom: str | None
    monthly_bill_inr: int | None
    notes: str | None
    accepted_quote_id: UUID | None


class RequestSummary(Output):
    id: UUID
    status: RequestStatus
    monthly_units: int
    size_kw: Decimal
    quotes_count: int
    created_at: datetime


class HouseholdContact(Output):
    """Shared with a vendor only after that vendor's quote is accepted."""

    name: str | None
    phone: str
    location: GeoPoint
    address_text: str | None


class VendorRequestView(RequestBase):
    """A vendor's view. The location is rounded to about 500 m and there is no phone number."""

    view: Literal["vendor"] = "vendor"
    approx_location: GeoPoint
    distance_km: Decimal
    my_quote_id: UUID | None
    contact: HouseholdContact | None = Field(
        None, description="Set once this vendor's quote is accepted."
    )


class OpenRequestPin(Output):
    id: UUID
    approx_location: GeoPoint
    distance_km: Decimal
    monthly_units: int
    budget_inr: int
    size_kw: Decimal
    roof_area_m2: Decimal
    quotes_count: int
    created_at: datetime


# --- Quotes ---------------------------------------------------------------------------------


class QuoteCreate(Input):
    system_kw: Kw
    price_inr: Rupees
    panel_brand: str = Field(min_length=1, max_length=80)
    panel_watt: int = Field(ge=100, le=1000)
    dcr: bool | None = Field(None, description="Domestic content panels. Leave empty if unknown.")
    inverter_brand: str = Field(min_length=1, max_length=80)
    inverter_kw: Kw
    warranty_panel_yrs: Years
    warranty_inverter_yrs: Years
    warranty_work_yrs: Years
    timeline_days: int = Field(ge=1, le=365)
    inclusions: set[Inclusion] = Field(default_factory=set)
    notes: str | None = Field(
        None, max_length=2000, description="Untrusted. Shown to the household, never used to rank."
    )


class VendorSummary(Output):
    id: UUID
    company: str
    mnre_reg_no: str | None
    rating: Decimal | None
    verified: bool


class VendorContact(Output):
    company: str
    contact_name: str | None
    phone: str


class QuoteFinancials(Cited):
    """Calculated by `rules.subsidy` and `rules.payback` when the quote is submitted."""

    subsidy_inr: int
    net_cost_inr: int
    annual_generation_kwh: Decimal
    annual_saving_inr: int
    payback_years: Decimal | None = Field(description="Empty when the system saves nothing.")


class QuoteReview(Output):
    """`missing_items` and the injection flag come from code. `llm_notes` is explanation only."""

    kind: Literal["quote_review"] = "quote_review"
    status: JobStatus
    missing_items: list[str]
    injection_flag: bool
    injection_excerpt: str | None = None
    llm_notes: str | None = None


class QuoteScore(Output):
    score: Decimal
    breakdown: dict[str, Decimal]


class QuoteOut(Output):
    id: UUID
    request_id: UUID
    vendor: VendorSummary
    status: QuoteStatus
    system_kw: Decimal
    price_inr: int
    panel_brand: str
    panel_watt: int
    dcr: bool | None
    inverter_brand: str
    inverter_kw: Decimal
    warranty_panel_yrs: int
    warranty_inverter_yrs: int
    warranty_work_yrs: int
    timeline_days: int
    inclusions: list[Inclusion]
    notes: str | None
    financials: QuoteFinancials
    review: QuoteReview
    score: QuoteScore | None
    submitted_at: datetime


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
    request_id: UUID
    status: QuoteStatus
    price_inr: int
    system_kw: Decimal
    submitted_at: datetime
    contact: HouseholdContact | None = Field(None, description="Set once this quote is accepted.")


class RankedQuote(Output):
    quote_id: UUID
    rank: int
    score: Decimal


class Recommendation(Cited):
    """Ranking from `rules.scoring`. The LLM writes the reasons and notes from the score table."""

    kind: Literal["recommend"] = "recommend"
    request_id: UUID
    recommended_quote_id: UUID | None
    ranking: list[RankedQuote]
    reasons: list[str]
    other_notes: dict[str, str] = Field(description="One line per other quote, keyed by quote id.")
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
    VoiceResult | PhotoAssessment | QuoteReview | Recommendation, Field(discriminator="kind")
]


class JobOut(Output):
    id: UUID
    type: JobType
    status: JobStatus
    attempts: int
    output: JobOutput | None = None
    error: str | None = None
    created_at: datetime
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
