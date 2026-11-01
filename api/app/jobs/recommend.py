"""Recommendation (work plan 4.5): code ranks the quotes, the LLM explains the ranking.

The model gets a table of scores under neutral labels (Quote A, B, ...) in submission order.
No vendor name, note or other vendor text reaches it, so nothing a vendor writes can steer it.
Code then checks that the model backs the quote code ranked first, drops any line with a
figure in it, and falls back to a template written from the score breakdown when the model is
unavailable or its answer fails those checks. A household always gets a recommendation.
"""

import uuid
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app import models
from api.app.enums import JobPriority, JobType
from api.app.errors import ApiError
from api.app.jobs.runner import JobContext, enqueue, handler, record
from api.app.llm.base import Part, Text
from api.app.llm.gateway import AiUnavailable
from api.app.llm.guard import clean_notes
from api.app.llm.providers.fake import script
from api.app.schemas import RankedQuote, RecommendationOut
from api.app.services.quotes import Ranked, quotes_fingerprint, ranked_quotes
from api.app.services.requests import required
from api.app.services.rules import citations_for
from rules.checklist import QuoteFacts
from rules.loader import load_rules
from rules.scoring import QuoteScore

PROMPT_VERSION = "recommend.v1"

SYSTEM = """You explain to a household in India why one rooftop solar quote is recommended.
The ranking is already decided by a scoring formula; you do not change it. The table lists
each quote by label with its score and the facts behind it.
Write:
- recommended: the label of the quote with the highest score.
- reasons: two to four short sentences on why that quote leads, in plain English.
- others: one short sentence for each other quote on where it falls behind.
- caveats: one sentence if something needs checking before signing, otherwise null.
Do not write numbers, prices or units; the app shows every figure beside your words.
Reply with JSON only."""

# Plain sentences for the template, one per scoring criterion in `rules.scoring`.
STRENGTHS = {
    "net_cost_per_kw": "Best value: a low cost per kW once the subsidy is taken off.",
    "warranty": "Strong warranties on the panels, the inverter and the workmanship.",
    "component_quality": "Named, DCR-compliant panels and inverter.",
    "completeness": "Few or no items missing from the quote.",
    "timeline": "A quick installation timeline.",
    "vendor_rating": "Well rated by other households.",
}
WEAKER_ON = {
    "net_cost_per_kw": "cost per kW after the subsidy",
    "warranty": "warranties",
    "component_quality": "the components quoted",
    "completeness": "items missing from the quote",
    "timeline": "installation time",
    "vendor_rating": "vendor rating",
}
FLAGGED = "contained instructions aimed at the AI. They were ignored and did not affect its score."


class OtherNote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(max_length=4)
    note: str = Field(max_length=240)


class RecommendAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recommended: str = Field(max_length=4)
    reasons: list[str] = Field(min_length=1, max_length=4)
    others: list[OtherNote] = Field(default_factory=list, max_length=49)
    caveats: str | None = Field(None, max_length=300)


def _labels(ranked: Ranked) -> dict[str, str]:
    """Quote id to a neutral label, in submission order so the label says nothing of rank."""
    letters = [chr(ord("A") + i) for i in range(26)]
    labels = letters + [f"{a}{b}" for a in letters for b in letters]
    return {str(q.id): labels[i] for i, q in enumerate(ranked.quotes)}


def _fractions(score: QuoteScore) -> dict[str, Decimal]:
    weights = load_rules().scoring.weights.model_dump()
    return {k: v / weights[k] if weights[k] else Decimal(0) for k, v in score.breakdown.items()}


def score_table(ranked: Ranked, labels: dict[str, str]) -> str:
    rows = []
    for score in sorted(ranked.ranking.scores, key=lambda s: labels[s.quote_id]):
        facts: QuoteFacts = ranked.facts[score.quote_id]
        per_kw = round(facts.net_cost_inr / facts.system_kw) if facts.system_kw else 0
        points = ", ".join(f"{k} {v}" for k, v in score.breakdown.items())
        missing = ", ".join(m.replace("_", " ") for m in score.missing) or "none"
        warranties = (
            f"panel {facts.warranty_panel_yrs}, inverter {facts.warranty_inverter_yrs}, "
            f"workmanship {facts.warranty_work_yrs} years"
        )
        rows.append(
            f"Quote {labels[score.quote_id]} | score {score.score} out of 100 | points: {points} | "
            f"net cost per kW after subsidy {per_kw} | warranties {warranties} | "
            f"timeline {facts.timeline_days} days | DCR panels {'yes' if facts.dcr else 'no'} | "
            f"missing items: {missing}"
        )
    return "\n".join(rows)


def template(ranked: Ranked) -> tuple[list[str], dict[str, str]]:
    """Reasons and per-quote lines written from the score breakdown alone."""
    scores = ranked.ranking.scores
    top = _fractions(scores[0])
    best = sorted(top, key=lambda k: top[k], reverse=True)
    reasons = [STRENGTHS[k] for k in best[:3] if top[k] > 0] or [
        "It has the highest overall score."
    ]
    others = {}
    for score in scores[1:]:
        mine = _fractions(score)
        gap = max(top, key=lambda k: top[k] - mine[k])
        others[score.quote_id] = (
            f"Scores lower than the top quote, mainly on {WEAKER_ON[gap]}."
            if top[gap] > mine[gap]
            else "Scores slightly lower than the top quote overall."
        )
    return reasons, others


def _caveats(ranked: Ranked, model_caveat: str | None) -> str | None:
    # Real quote codes here: the household never sees the neutral labels the model used.
    lines = [
        f"Quote {q.quote_code} from {q.vendor.company_name} {FLAGGED}"
        for q in ranked.quotes
        if q.injection_flag
    ]
    if model_caveat:
        lines.extend(clean_notes([model_caveat], limit=1))
    return " ".join(lines) or None


def _out(
    db: Session, rec: models.Recommendation, request: models.SolarRequest, stale: bool
) -> RecommendationOut:
    rule_set = required(db.get(models.RuleSet, request.rule_set_id), "rule set")
    citations = citations_for(db, rule_set.id)
    text = rec.reasons if isinstance(rec.reasons, dict) else {}
    return RecommendationOut(
        id=rec.id,
        request_id=rec.request_id,
        recommended_quote_id=rec.recommended_quote_id,
        ranking=[RankedQuote.model_validate(r) for r in rec.ranking],
        reasons=list(text.get("top", [])),
        other_notes=dict(text.get("others", {})),
        caveats=rec.caveats,
        written_by=text.get("written_by", "template"),
        stale=stale,
        created_at=rec.created_at,
        rule_version=rule_set.version,
        citations=[citations["SCORE_MODEL"]] if "SCORE_MODEL" in citations else [],
    )


# --- Endpoints --------------------------------------------------------------------------------


def _owned_request(db: Session, user: models.User, request_id: uuid.UUID) -> models.SolarRequest:
    request = db.get(models.SolarRequest, request_id)
    if request is None or request.household_id != user.id:
        raise ApiError(404, "not_found", "Request not found.")
    return request


def request_recommendation(
    db: Session, user: models.User, request_id: uuid.UUID
) -> tuple[models.AiJob, bool]:
    request = _owned_request(db, user, request_id)
    ranked = ranked_quotes(db, request)
    if not ranked.quotes:
        raise ApiError(409, "no_quotes", "There are no quotes to compare yet.")
    # The same quotes give the same job, so the advice is reused until a quote changes.
    job, needs_run = enqueue(
        db,
        job_type=JobType.RECOMMEND,
        entity_type="solar_request",
        entity_id=request.id,
        payload={"quotes": quotes_fingerprint(ranked.quotes)},
        prompt_version=PROMPT_VERSION,
        priority=JobPriority.HIGH,
        requested_by=user.id,
    )
    db.commit()
    return job, needs_run


def latest_recommendation(
    db: Session, user: models.User, request_id: uuid.UUID
) -> RecommendationOut:
    request = _owned_request(db, user, request_id)
    rec = db.scalars(
        select(models.Recommendation)
        .where(models.Recommendation.request_id == request.id)
        .order_by(models.Recommendation.created_at.desc())
        .limit(1)
    ).first()
    if rec is None:
        raise ApiError(404, "not_found", "No recommendation yet. Ask for one first.")
    current = quotes_fingerprint(ranked_quotes(db, request).quotes)
    return _out(db, rec, request, stale=rec.quotes_fingerprint != current)


# --- Job --------------------------------------------------------------------------------------


@handler(JobType.RECOMMEND)
def recommend(ctx: JobContext) -> dict[str, Any]:
    db, job = ctx.db, ctx.job
    request = db.get(models.SolarRequest, job.entity_id)
    if request is None:
        raise LookupError("request is missing")
    ranked = ranked_quotes(db, request)
    if not ranked.quotes:
        raise LookupError("no quotes to recommend")
    labels = _labels(ranked)
    by_label = {label: quote_id for quote_id, label in labels.items()}
    top_id = ranked.ranking.scores[0].quote_id

    written_by: Literal["ai", "template"] = "template"
    reasons, others = template(ranked)
    model_caveat, model = None, None
    try:
        parts: list[Part] = [Text(score_table(ranked, labels))]
        result = ctx.gateway.generate(
            task="recommend",
            system=SYSTEM,
            parts=parts,
            schema=RecommendAnswer,
            priority=job.priority,
            prefer_fast=True,
        )
        record(job, result)
        answer = result.output
        kept = clean_notes(answer.reasons)
        # Winner check: the words must back the quote that code ranked first.
        if by_label.get(answer.recommended.strip()) == top_id and kept:
            written_by, reasons, model = "ai", kept, result.model
            model_caveat = answer.caveats
            for other in answer.others:
                quote_id = by_label.get(other.label.strip())
                note = clean_notes([other.note], limit=1)
                if quote_id and quote_id != top_id and note:
                    others[quote_id] = note[0]
    except AiUnavailable:
        pass

    rec = models.Recommendation(
        request_id=request.id,
        recommended_quote_id=uuid.UUID(top_id),
        quotes_fingerprint=quotes_fingerprint(ranked.quotes),
        ranking=[
            {"quote_id": s.quote_id, "rank": i, "score": str(s.score)}
            for i, s in enumerate(ranked.ranking.scores, start=1)
        ],
        reasons={"top": reasons, "others": others, "written_by": written_by},
        caveats=_caveats(ranked, model_caveat),
        ai_job_id=job.id,
        model=model,
    )
    db.add(rec)
    db.flush()
    return _out(db, rec, request, stale=False).model_dump(mode="json")


@script("recommend")
def _fake_recommendation(parts: list[Part]) -> dict[str, Any]:
    """The demo answer when AI_PROVIDER=fake: back the top-scoring row of the table."""
    text = " ".join(p.text for p in parts if isinstance(p, Text))
    rows = [line for line in text.splitlines() if line.startswith("Quote ")]
    best = max(rows, key=lambda row: float(row.split("score ")[1].split()[0]))
    return {
        "recommended": best.split()[1],
        "reasons": [
            "It gives the best balance of price, warranties and completeness.",
            "Nothing important is missing from it.",
        ],
        "others": [],
        "caveats": None,
    }
