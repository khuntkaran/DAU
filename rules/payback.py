"""Net cost, annual saving and simple payback."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from rules.loader import RuleSet, load_rules, to_inr


@dataclass(frozen=True)
class PaybackResult:
    net_cost_inr: int
    annual_generation_kwh: Decimal
    annual_consumption_kwh: Decimal
    annual_saving_inr: int
    payback_years: Decimal | None
    rule_version: str
    citations: tuple[str, ...]


def calculate_payback(
    price_inr: int,
    subsidy_inr: int,
    capacity_kw: Decimal,
    monthly_units: int,
    tariff_inr_per_kwh: Decimal | None = None,
    rules: RuleSet | None = None,
) -> PaybackResult:
    if price_inr < 0 or subsidy_inr < 0:
        raise ValueError("price and subsidy cannot be negative")
    if capacity_kw < 0 or monthly_units < 0:
        raise ValueError("capacity and usage cannot be negative")

    ruleset = rules or load_rules()
    tariff = tariff_inr_per_kwh
    citations = ["GENERATION"]
    if tariff is None:
        tariff = ruleset.payback.default_tariff_inr_per_kwh
        citations.append("TARIFF_DEFAULT")

    generation = capacity_kw * ruleset.sizing.generation_kwh_per_kw_month * 12
    consumption = Decimal(monthly_units * 12)
    # Only energy the household would otherwise buy counts as a saving.
    saving = to_inr(min(generation, consumption) * tariff)
    net_cost = max(price_inr - subsidy_inr, 0)

    payback_years = None
    if saving > 0:
        payback_years = (Decimal(net_cost) / saving).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

    return PaybackResult(
        net_cost_inr=net_cost,
        annual_generation_kwh=generation,
        annual_consumption_kwh=consumption,
        annual_saving_inr=saving,
        payback_years=payback_years,
        rule_version=ruleset.version,
        citations=tuple(citations),
    )
