"""Suggests a system size from consumption, limited by usable roof area."""

from dataclasses import dataclass
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from rules.loader import RuleSet, load_rules
from rules.steps import Step, fmt


@dataclass(frozen=True)
class SizingResult:
    raw_kw: Decimal
    size_kw: Decimal
    max_kw: Decimal
    capped_by_roof: bool
    rule_version: str
    citations: tuple[str, ...]
    steps: tuple[Step, ...]


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

    size_kw = min(wanted_kw, max_kw)

    citations = ["SIZE_BANDS", "GENERATION", "ROOF_AREA"]
    if usable_fraction is None:
        citations.append("USABLE_FRACTION")

    usable_area = roof_area_m2 * fraction
    step = fmt(sizing.step_kw)
    steps = (
        Step(
            "raw_kw",
            "Size that covers your usage",
            f"{monthly_units} units ÷ {fmt(sizing.generation_kwh_per_kw_month)} units per kW"
            " per month",
            fmt(raw_kw),
            "kW",
            "GENERATION",
        ),
        Step(
            "wanted_kw",
            "Rounded to a standard size",
            f"{fmt(raw_kw)} kW rounded to the nearest {step} kW",
            fmt(wanted_kw),
            "kW",
        ),
        Step(
            "usable_area",
            "Usable roof area",
            f"{fmt(roof_area_m2)} m² × {fmt(fraction)} usable",
            fmt(usable_area),
            "m²",
            "USABLE_FRACTION" if usable_fraction is None else None,
        ),
        Step(
            "max_kw",
            "Largest system the roof fits",
            f"{fmt(usable_area)} m² ÷ {fmt(sizing.roof_m2_per_kw)} m² per kW,"
            f" rounded down to {step} kW",
            fmt(max_kw),
            "kW",
            "ROOF_AREA",
        ),
        Step(
            "size_kw",
            "Suggested size",
            f"smaller of {fmt(wanted_kw)} kW and {fmt(max_kw)} kW",
            fmt(size_kw),
            "kW",
        ),
    )

    return SizingResult(
        raw_kw=raw_kw,
        size_kw=size_kw,
        max_kw=max_kw,
        capped_by_roof=wanted_kw > max_kw,
        rule_version=ruleset.version,
        citations=tuple(citations),
        steps=steps,
    )
