"""Deterministic quote ranking. Vendor free text has no path into this module."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from rules.checklist import TOTAL_ITEMS, QuoteFacts, missing_items
from rules.loader import RuleSet, load_rules


@dataclass(frozen=True)
class QuoteScore:
    quote_id: str
    score: Decimal
    breakdown: dict[str, Decimal]
    missing: tuple[str, ...]


@dataclass(frozen=True)
class Ranking:
    scores: tuple[QuoteScore, ...]
    recommended_quote_id: str | None
    rule_version: str
    citations: tuple[str, ...]


def _ratio(value: float, target: float) -> Decimal:
    if target <= 0:
        return Decimal(0)
    return min(Decimal(str(value)) / Decimal(str(target)), Decimal(1))


def _lowest_is_best(value: float, best: float) -> Decimal:
    return Decimal(0) if value <= 0 or best <= 0 else _ratio(best, value)


def _cost_per_kw(quote: QuoteFacts) -> float:
    return quote.net_cost_inr / quote.system_kw if quote.system_kw > 0 else 0


def _score_one(
    quote: QuoteFacts, best_cost: float, best_timeline: int, ruleset: RuleSet
) -> QuoteScore:
    rules = ruleset.scoring
    targets = rules.warranty_targets_years
    warranty = (
        _ratio(quote.warranty_panel_yrs, targets.panel)
        + _ratio(quote.warranty_inverter_yrs, targets.inverter)
        + _ratio(quote.warranty_work_yrs, targets.workmanship)
    ) / 3
    known_parts = [quote.dcr is True, bool(quote.panel_brand), bool(quote.inverter_brand)]
    missing = missing_items(quote)

    fractions = {
        "net_cost_per_kw": _lowest_is_best(_cost_per_kw(quote), best_cost),
        "warranty": warranty,
        "component_quality": Decimal(sum(known_parts)) / len(known_parts),
        "completeness": Decimal(TOTAL_ITEMS - len(missing)) / TOTAL_ITEMS,
        "timeline": _lowest_is_best(quote.timeline_days, best_timeline),
        "vendor_rating": _ratio(quote.vendor_rating, float(rules.max_vendor_rating)),
    }
    weights = rules.weights.model_dump()
    breakdown = {
        name: (fraction * weights[name]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        for name, fraction in fractions.items()
    }
    return QuoteScore(quote.quote_id, sum(breakdown.values(), Decimal(0)), breakdown, missing)


def rank_quotes(quotes: list[QuoteFacts], rules: RuleSet | None = None) -> Ranking:
    ruleset = rules or load_rules()
    costs = [cost for cost in map(_cost_per_kw, quotes) if cost > 0]
    timelines = [quote.timeline_days for quote in quotes if quote.timeline_days > 0]
    best_cost = min(costs, default=0)
    best_timeline = min(timelines, default=0)

    scores = [_score_one(quote, best_cost, best_timeline, ruleset) for quote in quotes]
    # quote_id breaks ties so the same input always gives the same order.
    ordered = tuple(sorted(scores, key=lambda item: (-item.score, item.quote_id)))
    recommended = ordered[0].quote_id if ordered else None
    return Ranking(ordered, recommended, ruleset.version, ("SCORE_MODEL",))
