"""Central Financial Assistance under PM Surya Ghar."""

from dataclasses import dataclass
from decimal import Decimal

from rules.loader import RuleSet, StateCategory, load_rules, to_inr


@dataclass(frozen=True)
class SubsidyResult:
    amount_inr: int
    rule_version: str
    citations: tuple[str, ...]


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

    first_kw = min(capacity_kw, subsidy.first_slab_kw)
    second_kw = min(max(capacity_kw - subsidy.first_slab_kw, Decimal(0)), subsidy.second_slab_kw)
    amount = first_kw * slabs.first_slab_inr_per_kw + second_kw * slabs.second_slab_inr_per_kw

    citations = ["CFA_SLAB_1"]
    if second_kw > 0:
        citations.append("CFA_SLAB_2")
    if capacity_kw >= subsidy.first_slab_kw + subsidy.second_slab_kw:
        citations.append("CFA_CAP")
    if capacity_kw != capacity_kw.to_integral_value():
        citations.append("CFA_PRO_RATA")
    if category == "special":
        citations.append("CFA_SPECIAL")

    return SubsidyResult(to_inr(amount), ruleset.version, tuple(citations))
