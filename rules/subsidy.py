"""Central Financial Assistance under PM Surya Ghar."""

from dataclasses import dataclass
from decimal import Decimal

from rules.loader import RuleSet, StateCategory, load_rules, to_inr
from rules.steps import Step, fmt


@dataclass(frozen=True)
class SubsidyResult:
    amount_inr: int
    rule_version: str
    citations: tuple[str, ...]
    steps: tuple[Step, ...]


def calculate_subsidy(
    capacity_kw: Decimal,
    category: StateCategory = "general",
    rules: RuleSet | None = None,
) -> SubsidyResult:
    if capacity_kw < 0:
        raise ValueError("capacity_kw cannot be negative")

    ruleset = rules or load_rules()
    subsidy = ruleset.subsidy
    slabs = subsidy.general if category == "general" else subsidy.special
    cap_kw = subsidy.first_slab_kw + subsidy.second_slab_kw

    first_kw = min(capacity_kw, subsidy.first_slab_kw)
    second_kw = min(max(capacity_kw - subsidy.first_slab_kw, Decimal(0)), subsidy.second_slab_kw)
    first_amount = first_kw * slabs.first_slab_inr_per_kw
    second_amount = second_kw * slabs.second_slab_inr_per_kw
    amount = to_inr(first_amount + second_amount)

    citations = ["CFA_SLAB_1"]
    if second_kw > 0:
        citations.append("CFA_SLAB_2")
    if capacity_kw >= cap_kw:
        citations.append("CFA_CAP")
    if capacity_kw != capacity_kw.to_integral_value():
        citations.append("CFA_PRO_RATA")
    if category == "special":
        citations.append("CFA_SPECIAL")

    # Special-category states replace both slab rates, so that rule explains both lines.
    special = category == "special"
    steps = [
        Step(
            "first_slab",
            f"First {fmt(subsidy.first_slab_kw)} kW" + (" (special category)" if special else ""),
            f"{fmt(first_kw)} kW × ₹{slabs.first_slab_inr_per_kw} per kW",
            fmt(first_amount),
            "INR",
            "CFA_SPECIAL" if special else "CFA_SLAB_1",
        )
    ]
    if second_kw > 0:
        steps.append(
            Step(
                "second_slab",
                f"Next {fmt(subsidy.second_slab_kw)} kW"
                + (" (special category)" if special else ""),
                f"{fmt(second_kw)} kW × ₹{slabs.second_slab_inr_per_kw} per kW",
                fmt(second_amount),
                "INR",
                "CFA_SPECIAL" if special else "CFA_SLAB_2",
            )
        )
    if capacity_kw > cap_kw:
        steps.append(
            Step(
                "above_cap",
                f"No subsidy above {fmt(cap_kw)} kW",
                f"{fmt(capacity_kw - cap_kw)} kW above {fmt(cap_kw)} kW × ₹0",
                "0",
                "INR",
                "CFA_CAP",
            )
        )
    parts = [first_amount] + ([second_amount] if second_kw > 0 else [])
    steps.append(
        Step(
            "subsidy",
            "Total subsidy",
            " + ".join(f"₹{fmt(part)}" for part in parts),
            str(amount),
            "INR",
        )
    )

    return SubsidyResult(amount, ruleset.version, tuple(citations), tuple(steps))
