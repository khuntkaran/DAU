"""Suggests a system size from consumption, limited by usable roof area."""

from dataclasses import dataclass
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from rules.loader import RuleSet, load_rules


@dataclass(frozen=True)
class SizingResult:
    raw_kw: Decimal
    size_kw: Decimal
    max_kw: Decimal
    capped_by_roof: bool
    rule_version: str
    citations: tuple[str, ...]


def _to_step(value: Decimal, step: Decimal, rounding: str) -> Decimal:
    return (value / step).to_integral_value(rounding=rounding) * step


def suggest_size(
    monthly_units: int,
    roof_area_m2: Decimal,
    usable_fraction: Decimal | None = None,
    rules: RuleSet | None = None,
) -> SizingResult:
    if monthly_units < 0:
        raise ValueError("monthly_units cannot be negative")
    if roof_area_m2 < 0:
        raise ValueError("roof_area_m2 cannot be negative")
    if usable_fraction is not None and not Decimal(0) <= usable_fraction <= Decimal(1):
        raise ValueError("usable_fraction must be between 0 and 1")

    ruleset = rules or load_rules()
    sizing = ruleset.sizing
    fraction = sizing.default_usable_fraction if usable_fraction is None else usable_fraction

    raw_kw = Decimal(monthly_units) / sizing.generation_kwh_per_kw_month
    wanted_kw = _to_step(raw_kw, sizing.step_kw, ROUND_HALF_UP)
    # Rounding the roof limit up would suggest panels that do not fit.
    max_kw = _to_step(roof_area_m2 * fraction / sizing.roof_m2_per_kw, sizing.step_kw, ROUND_FLOOR)

    citations = ["SIZE_BANDS", "GENERATION", "ROOF_AREA"]
    if usable_fraction is None:
        citations.append("USABLE_FRACTION")

    return SizingResult(
        raw_kw=raw_kw,
        size_kw=min(wanted_kw, max_kw),
        max_kw=max_kw,
        capped_by_roof=wanted_kw > max_kw,
        rule_version=ruleset.version,
        citations=tuple(citations),
    )
