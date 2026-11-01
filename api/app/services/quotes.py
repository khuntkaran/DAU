"""Submitting quotes, the code half of their review, and comparing them.

Vendor notes are untrusted. They are stored and shown to the household, but nothing here
reads them: the checklist, warnings and ranking use structured fields only.
"""

import hashlib
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import CursorResult, or_, select, tuple_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app import models
from api.app.db import utcnow
from api.app.enums import (
    Level,
    LineItemType,
    QuoteSource,
    QuoteStatus,
    RequestStatus,
)
from api.app.errors import ApiError
from api.app.jobs import quote_review
from api.app.schemas import (
    AcceptResult,
    LineItemOut,
    Page,
    QuoteComparison,
    QuoteCreate,
    QuoteOut,
    QuoteReviewOut,
    QuoteScoreOut,
    ScoreLine,
    VendorContact,
    VendorQuoteSummary,
    VendorSummary,
)
from api.app.services.calculations import quote_financials
from api.app.services.codes import CODE_RETRIES, next_code
from api.app.services.pagination import decode_cursor, encode_cursor
from api.app.services.requests import (
    VISIBLE_TO_VENDORS,
    calculation_out,
    fields_of,
    household_contact,
    required,
)
from api.app.services.rules import citations_for
from rules.checklist import REQUIRED_INCLUSIONS, TOTAL_ITEMS, QuoteFacts, missing_items
from rules.loader import load_rules
from rules.scoring import QuoteScore, Ranking, rank_quotes

CHECKLIST_VERSION = "1"
MAX_QUOTES_COMPARED = 50

# Each checklist item from `rules.checklist`, and the line items that together satisfy it.
# An entry is a list of alternatives; each alternative needs all of its line items.
CHECKLIST_LINE_ITEMS: dict[str, list[frozenset[LineItemType]]] = {
    "net_metering_fee": [
        frozenset({LineItemType.NET_METER}),
        frozenset({LineItemType.DISCOM_FEES}),
    ],
    "mounting_structure": [frozenset({LineItemType.MOUNTING_STRUCTURE})],
    "earthing_and_lightning_arrester": [
        frozenset({LineItemType.EARTHING, LineItemType.LIGHTNING_ARRESTER})
    ],
    "amc": [frozenset({LineItemType.AMC})],
    "insurance": [frozenset({LineItemType.INSURANCE})],
}

# Plain-language reasons shown beside each missing item. Copy, not rule values.
MISSING_ITEM_TEXT: dict[str, tuple[Level, str]] = {
    "dcr_panels": (Level.HIGH, "The subsidy needs domestic (DCR) panels; this is not stated."),
    "inverter_warranty": (Level.MEDIUM, "Without it, an inverter failure is your cost to fix."),
    "workmanship_warranty": (
        Level.MEDIUM,
        "Covers leaks, loose fittings and wiring faults from the installation itself.",
    ),
    "mnre_vendor_registration": (
        Level.HIGH,
        "Only registered vendors can install systems under PM Surya Ghar.",
    ),
    "net_metering_fee": (
        Level.HIGH,
        "Net metering lets you sell surplus power. Its fee is often added later if not quoted.",
    ),
    "mounting_structure": (
        Level.MEDIUM,
        "The frame that holds the panels. Sometimes charged extra on site.",
    ),
    "earthing_and_lightning_arrester": (
        Level.HIGH,
        "Needed for safety; protects the house and the system.",
    ),
    "amc": (Level.LOW, "Yearly cleaning and checks keep generation up."),
    "insurance": (Level.LOW, "Covers damage to the system during and after installation."),
}

_NOT_FOUND = ApiError(404, "not_found", "Request not found.")


def inclusions_from_line_items(
    items: Iterable[tuple[LineItemType, bool]],
) -> frozenset[str]:
    """Checklist items covered by the line items a vendor marked as included."""
    included = {item_type for item_type, is_included in items if is_included}
    return frozenset(
        name
        for name in REQUIRED_INCLUSIONS
        if any(needed <= included for needed in CHECKLIST_LINE_ITEMS[name])
    )


def _facts(
    quote: models.Quote, vendor: models.Vendor, financials: models.Calculation
) -> QuoteFacts:
    # `notes` is deliberately left out: free text must never reach the checklist or ranking.
    return QuoteFacts(
        quote_id=str(quote.id),
        net_cost_inr=financials.net_cost_inr or 0,
        system_kw=float(quote.system_kw),
        warranty_panel_yrs=quote.panel_performance_warranty_yrs or 0,
        warranty_inverter_yrs=quote.inverter_warranty_yrs or 0,
        warranty_work_yrs=quote.workmanship_warranty_yrs or 0,
        timeline_days=quote.timeline_days,
        vendor_rating=float(vendor.avg_rating or 0),
        dcr=quote.dcr_compliant,
        panel_brand=quote.panel_brand,
        inverter_brand=quote.inverter_brand,
        mnre_registered=bool(vendor.mnre_registration_no),
        inclusions=inclusions_from_line_items(
            (item.item_type, item.included) for item in quote.line_items
        ),
    )


def _warnings(quote: models.Quote, estimate: models.Calculation | None) -> list[str]:
    warnings = []
    if not quote.dcr_compliant:
        warnings.append("Panels are not DCR, so this system may not qualify for the subsidy.")
    roof_cap = estimate.roof_cap_kw if estimate is not None else None
    if roof_cap is not None and quote.system_kw > roof_cap:
        warnings.append(
            f"{quote.system_kw.normalize():f} kW is more than the roof fits "
            f"({roof_cap.normalize():f} kW)."
        )
    return warnings


def _financials(db: Session, quote: models.Quote) -> models.Calculation:
    calc = db.scalars(
        select(models.Calculation).where(models.Calculation.quote_id == quote.id)
    ).first()
    return required(calc, "quote financials")


# --- Submitting -----------------------------------------------------------------------------


def submit_quote(
    db: Session, user: models.User, request_id: uuid.UUID, body: QuoteCreate
) -> tuple[models.Quote, models.AiJob, bool]:
    vendor = user.vendor
    if vendor is None:
        raise ApiError(403, "forbidden", "Complete your vendor profile first.")
    request = db.get(models.SolarRequest, request_id)
    if request is None:
        raise _NOT_FOUND
    expired = request.expires_at is not None and request.expires_at <= utcnow()
    if request.status not in VISIBLE_TO_VENDORS or expired:
        raise ApiError(409, "request_closed", "This request is no longer taking quotes.")
    if db.scalar(
        select(models.Quote.id).where(
            models.Quote.request_id == request.id, models.Quote.vendor_id == vendor.id
        )
    ):
        raise ApiError(409, "already_quoted", "You have already quoted this request.")

    for attempt in range(CODE_RETRIES):
        try:
            return insert_quote(db, user, vendor, request, body)
        except IntegrityError:
            db.rollback()
            # A duplicate quote from a double click is a conflict, not a code clash.
            if db.scalar(
                select(models.Quote.id).where(
                    models.Quote.request_id == request.id, models.Quote.vendor_id == vendor.id
                )
            ):
                raise ApiError(
                    409, "already_quoted", "You have already quoted this request."
                ) from None
            if attempt == CODE_RETRIES - 1:
                raise
    raise AssertionError("unreachable")


def insert_quote(
    db: Session,
    user: models.User,
    vendor: models.Vendor,
    request: models.SolarRequest,
    body: QuoteCreate,
    *,
    code: str | None = None,
    submitted_at: datetime | None = None,
) -> tuple[models.Quote, models.AiJob, bool]:
    """Stores a quote with its financials, code review and queued AI review. The seed script
    passes a fixed code and time; the API leaves both to be generated."""
    now = submitted_at or utcnow()
    quote = models.Quote(
        **body.model_dump(exclude={"line_items"}),
        quote_code=code or next_code(db, models.Quote.quote_code, "Q"),
        request_id=request.id,
        vendor_id=vendor.id,
        status=QuoteStatus.SUBMITTED,
        source=QuoteSource.FORM,
        submitted_at=now,
    )
    quote.line_items = [
        models.QuoteLineItem(sort_order=i, **item.model_dump())
        for i, item in enumerate(body.line_items)
    ]
    db.add(quote)
    db.flush()

    financials = quote_financials(quote, request)
    db.add(financials)
    db.flush()

    estimate = db.get(models.Calculation, request.latest_estimate_id)
    review = models.QuoteReview(
        quote_id=quote.id,
        rule_set_id=request.rule_set_id,
        checklist_version=CHECKLIST_VERSION,
        missing_items=[
            {
                "item": item,
                "severity": MISSING_ITEM_TEXT[item][0],
                "why": MISSING_ITEM_TEXT[item][1],
            }
            for item in missing_items(_facts(quote, vendor, financials))
        ],
        warnings=_warnings(quote, estimate),
        injection_detected=False,
        reviewed_at=now,
    )
    db.add(review)
    # The pattern check runs now, so a flagged quote shows its warning even with the AI down.
    quote_review.pattern_check(quote, review)
    db.flush()
    job, needs_run = quote_review.queue_review(db, quote, review, user)

    if request.status == RequestStatus.OPEN:
        request.status = RequestStatus.QUOTED
        db.add(
            models.RequestStatusHistory(
                request_id=request.id,
                from_status=RequestStatus.OPEN,
                to_status=RequestStatus.QUOTED,
                changed_by=user.id,
                created_at=now,
            )
        )
    # Counted in SQL, so two vendors quoting at once cannot overwrite each other's count.
    db.execute(
        update(models.SolarRequest)
        .where(models.SolarRequest.id == request.id)
        .values(quotes_count=models.SolarRequest.quotes_count + 1)
    )
    db.commit()
    return quote, job, needs_run


# --- Showing --------------------------------------------------------------------------------


def _review_out(db: Session, quote: models.Quote) -> QuoteReviewOut | None:
    review = quote_review.latest_review(db, quote)
    return quote_review.review_out(db, review) if review else None


def quote_out(db: Session, quote: models.Quote, score: QuoteScoreOut | None = None) -> QuoteOut:
    return QuoteOut.model_validate(
        {
            **fields_of(quote, QuoteOut),
            "vendor": VendorSummary.model_validate(quote.vendor),
            "line_items": [LineItemOut.model_validate(i) for i in quote.line_items],
            "financials": calculation_out(db, _financials(db, quote)),
            "review": _review_out(db, quote),
            "score": score,
        }
    )


def _score_out(score: QuoteScore, facts: QuoteFacts) -> QuoteScoreOut:
    weights = load_rules().scoring.weights.model_dump()
    per_kw = Decimal(facts.net_cost_inr) / Decimal(str(facts.system_kw or 1))
    inputs = {
        "net_cost_per_kw": f"₹{per_kw:.0f} per kW after subsidy",
        "warranty": (
            f"panels {facts.warranty_panel_yrs}, inverter {facts.warranty_inverter_yrs},"
            f" workmanship {facts.warranty_work_yrs} years"
        ),
        "component_quality": (
            f"DCR {'yes' if facts.dcr else 'no'}; panel and inverter brands"
            f" {'named' if facts.panel_brand and facts.inverter_brand else 'missing'}"
        ),
        "completeness": f"{TOTAL_ITEMS - len(score.missing)} of {TOTAL_ITEMS} checklist items",
        "timeline": f"{facts.timeline_days} days",
        "vendor_rating": f"{facts.vendor_rating:g} of 5",
    }
    return QuoteScoreOut(
        total_score=score.score,
        weights=weights,
        explanation=[
            ScoreLine(
                criterion=name,
                input=inputs[name],
                formula=f"{points} of {weights[name]} points",
                points=points,
            )
            for name, points in score.breakdown.items()
        ],
    )


@dataclass(frozen=True)
class Ranked:
    """Quotes on a request in submission order, their facts, and the ranking from code."""

    quotes: list[models.Quote]
    facts: dict[str, QuoteFacts]
    ranking: Ranking

    @property
    def by_id(self) -> dict[str, models.Quote]:
        return {str(q.id): q for q in self.quotes}


def ranked_quotes(db: Session, request: models.SolarRequest) -> Ranked:
    quotes = list(
        db.scalars(
            select(models.Quote)
            .where(
                models.Quote.request_id == request.id,
                models.Quote.status != QuoteStatus.WITHDRAWN,
            )
            .order_by(models.Quote.submitted_at, models.Quote.id)
            .limit(MAX_QUOTES_COMPARED)
        )
    )
    facts = {str(q.id): _facts(q, q.vendor, _financials(db, q)) for q in quotes}
    return Ranked(quotes, facts, rank_quotes(list(facts.values())))


def quotes_fingerprint(quotes: list[models.Quote]) -> str:
    """Changes whenever a quote is added, revised or decided, so old advice shows as stale."""
    parts = sorted(f"{q.id}:{q.revision}:{q.status}" for q in quotes)
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def score_out(score: QuoteScore, facts: QuoteFacts) -> QuoteScoreOut:
    return _score_out(score, facts)


def compare_quotes(db: Session, user: models.User, request_id: uuid.UUID) -> QuoteComparison:
    request = db.get(models.SolarRequest, request_id)
    if request is None or request.household_id != user.id:
        raise _NOT_FOUND
    ranked = ranked_quotes(db, request)
    ranking, facts, by_id = ranked.ranking, ranked.facts, ranked.by_id

    rule_set = required(db.get(models.RuleSet, request.rule_set_id), "rule set")
    citations = citations_for(db, rule_set.id)
    return QuoteComparison(
        request_id=request.id,
        quotes=[
            quote_out(db, by_id[s.quote_id], _score_out(s, facts[s.quote_id]))
            for s in ranking.scores
        ],
        top_quote_id=uuid.UUID(ranking.recommended_quote_id)
        if ranking.recommended_quote_id
        else None,
        rule_version=rule_set.version,
        citations=[citations[k] for k in ranking.citations if k in citations],
    )


def my_quotes(
    db: Session, user: models.User, limit: int, cursor: str | None
) -> Page[VendorQuoteSummary]:
    vendor = user.vendor
    if vendor is None:
        return Page[VendorQuoteSummary](items=[], next_cursor=None)
    query = (
        select(models.Quote, models.SolarRequest)
        .join(models.SolarRequest, models.SolarRequest.id == models.Quote.request_id)
        .where(models.Quote.vendor_id == vendor.id)
        .order_by(models.Quote.created_at.desc(), models.Quote.id.desc())
        .limit(limit + 1)
    )
    if cursor is not None:
        query = query.where(
            tuple_(models.Quote.created_at, models.Quote.id) < tuple_(*decode_cursor(cursor))
        )
    rows = db.execute(query).all()

    def summary(quote: models.Quote, request: models.SolarRequest) -> VendorQuoteSummary:
        accepted = quote.status == QuoteStatus.ACCEPTED
        extra: dict[str, Any] = {
            "request_code": request.request_code,
            "contact": household_contact(db, request) if accepted else None,
        }
        return VendorQuoteSummary.model_validate({**fields_of(quote, VendorQuoteSummary), **extra})

    last = rows[limit - 1][0] if len(rows) > limit else None
    return Page[VendorQuoteSummary](
        items=[summary(q, r) for q, r in rows[:limit]],
        next_cursor=encode_cursor(last.created_at, last.id) if last else None,
    )


# --- Accepting ------------------------------------------------------------------------------

_DECIDABLE = (QuoteStatus.SUBMITTED, QuoteStatus.REVISED)


def accept_quote(db: Session, user: models.User, quote_id: uuid.UUID) -> AcceptResult:
    """Accepts one quote and rejects the rest, in one transaction.

    The request moves from quoted to accepted by a conditional update, so of two accepts
    racing, exactly one changes the row and the other gets 409. The partial unique index on
    accepted quotes stops a second winner even if that check were bypassed.
    """
    quote = db.get(models.Quote, quote_id)
    request = db.get(models.SolarRequest, quote.request_id) if quote else None
    if quote is None or request is None or request.household_id != user.id:
        raise ApiError(404, "not_found", "Quote not found.")
    now = utcnow()
    closed = ApiError(409, "request_not_open", "This request has already been decided.")
    # An early, friendlier answer; the conditional update below is what actually decides.
    expired = request.expires_at is not None and request.expires_at <= now
    if request.status != RequestStatus.QUOTED or expired:
        raise closed
    if quote.status not in _DECIDABLE:
        raise ApiError(409, "quote_not_available", "This quote can no longer be accepted.")
    moved = cast(
        CursorResult[Any],
        db.execute(
            update(models.SolarRequest)
            .where(
                models.SolarRequest.id == request.id,
                models.SolarRequest.status == RequestStatus.QUOTED,
                or_(
                    models.SolarRequest.expires_at.is_(None),
                    models.SolarRequest.expires_at > now,
                ),
            )
            .values(status=RequestStatus.ACCEPTED, accepted_quote_id=quote.id, closed_at=now)
        ),
    )
    if moved.rowcount != 1:
        db.rollback()
        raise closed

    db.execute(
        update(models.Quote)
        .where(models.Quote.id == quote.id)
        .values(status=QuoteStatus.ACCEPTED, decided_at=now)
    )
    rejected = list(
        db.scalars(
            select(models.Quote.id).where(
                models.Quote.request_id == request.id,
                models.Quote.id != quote.id,
                models.Quote.status.in_(_DECIDABLE),
            )
        )
    )
    if rejected:
        db.execute(
            update(models.Quote)
            .where(models.Quote.id.in_(rejected))
            .values(status=QuoteStatus.REJECTED, decided_at=now)
        )
    db.add(
        models.RequestStatusHistory(
            request_id=request.id,
            from_status=RequestStatus.QUOTED,
            to_status=RequestStatus.ACCEPTED,
            changed_by=user.id,
            created_at=now,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise closed from None

    vendor = required(db.get(models.Vendor, quote.vendor_id), "vendor")
    return AcceptResult(
        request_id=request.id,
        request_status=RequestStatus.ACCEPTED,
        accepted_quote_id=quote.id,
        rejected_quote_ids=rejected,
        vendor_contact=VendorContact(
            company_name=vendor.company_name,
            contact_person=vendor.contact_person,
            contact_phone=vendor.contact_phone or vendor.user.phone,
            contact_email=vendor.contact_email,
        ),
    )
