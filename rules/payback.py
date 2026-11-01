"""Net cost, savings and simple payback."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from rules.loader import RuleSet, load_rules, to_inr
from rules.steps import Step, fmt


@dataclass(frozen=True)
class PaybackResult:
    net_cost_inr: int
    annual_generation_kwh: Decimal
    annual_consumption_kwh: Decimal
    annual_saving_inr: int
    monthly_saving_inr: int
    bill_reduction_pct: Decimal | None
    payback_years: Decimal | None
    rule_version: str
    citations: tuple[str, ...]
    steps: tuple[Step, ...]


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

    per_kw_month = ruleset.sizing.generation_kwh_per_kw_month
    generation = capacity_kw * per_kw_month * 12
    consumption = Decimal(monthly_units * 12)
    # Only energy the household would otherwise buy counts as a saving.
    offset = min(generation, consumption)
    raw_saving = offset * tariff
    saving = to_inr(raw_saving)
    monthly_saving = to_inr(raw_saving / 12)
    net_cost = max(price_inr - subsidy_inr, 0)

    bill_reduction = None
    if consumption > 0:
        bill_reduction = (offset / consumption * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    payback_years = None
    if saving > 0:
        payback_years = (Decimal(net_cost) / saving).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

    steps = [
        Step(
            "annual_generation",
            "Yearly generation",
            f"{fmt(capacity_kw)} kW × {fmt(per_kw_month)} units × 12 months",
            fmt(generation),
            "kWh",
            "GENERATION",
        ),
        Step(
            "annual_consumption",
            "Yearly usage",
            f"{monthly_units} units × 12 months",
            fmt(consumption),
            "kWh",
        ),
        Step(
            "annual_saving",
            "Yearly saving",
            f"smaller of {fmt(generation)} and {fmt(consumption)} kWh × ₹{fmt(tariff)} per kWh",
            str(saving),
            "INR",
            "TARIFF_DEFAULT" if tariff_inr_per_kwh is None else None,
        ),
        Step(
            "monthly_saving",
            "Monthly saving",
            f"₹{fmt(raw_saving)} ÷ 12 months",
            str(monthly_saving),
            "INR",
        ),
    ]
    if bill_reduction is not None:
        steps.append(
            Step(
                "bill_reduction",
                "Share of your usage covered",
                f"{fmt(offset)} kWh ÷ {fmt(consumption)} kWh × 100",
                fmt(bill_reduction),
                "%",
            )
        )
    steps.append(
        Step(
            "net_cost",
            "Your cost after subsidy",
            f"₹{price_inr} − ₹{subsidy_inr}" + (", but never below ₹0" if net_cost == 0 else ""),
            str(net_cost),
            "INR",
        )
    )
    if payback_years is None:
        steps.append(
            Step("payback", "Payback", "No yearly saving, so it never pays back", "never", None)
        )
    else:
        steps.append(
            Step(
                "payback",
                "Payback",
                f"₹{net_cost} ÷ ₹{saving} per year",
                fmt(payback_years),
                "years",
            )
        )

    return PaybackResult(
        net_cost_inr=net_cost,
        annual_generation_kwh=generation,
        annual_consumption_kwh=consumption,
        annual_saving_inr=saving,
        monthly_saving_inr=monthly_saving,
        bill_reduction_pct=bill_reduction,
        payback_years=payback_years,
        rule_version=ruleset.version,
        citations=tuple(citations),
        steps=tuple(steps),
    )
