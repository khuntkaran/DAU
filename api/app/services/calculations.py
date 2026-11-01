"""Turns `rules/` results into `calculations` rows. The only place the API computes a figure."""

from dataclasses import asdict
from decimal import Decimal
from typing import Any, Literal

from api.app import models
from api.app.enums import CalculationScope, StateCategory
from rules.loader import to_inr
from rules.payback import calculate_payback
from rules.sizing import suggest_size
from rules.steps import Step
from rules.subsidy import calculate_subsidy

ENGINE_VERSION = "1"

# Without a price there is no net cost or payback, so those lines are left out of an estimate.
_PRICE_STEPS = {"net_cost", "payback"}


def _category(value: StateCategory) -> Literal["general", "special"]:
    return "special" if value == StateCategory.SPECIAL else "general"


def _jsonable(values: dict[str, Any]) -> dict[str, Any]:
    return {k: str(v) if isinstance(v, Decimal) else v for k, v in values.items()}


def _citations(*groups: tuple[str, ...]) -> list[str]:
    return list(dict.fromkeys(key for group in groups for key in group))


def _steps(steps: list[Step]) -> list[dict[str, Any]]:
    return [asdict(step) for step in steps]


def request_estimate(request: models.SolarRequest) -> models.Calculation:
    """Size, subsidy and savings for a new request, before any vendor has quoted."""
    if request.roof_area_sqm is None:
        raise ValueError("an estimate needs the roof area")
    category = _category(request.state_category)

    size = suggest_size(request.monthly_units, request.roof_area_sqm)
    subsidy = calculate_subsidy(size.size_kw, category)
    savings = calculate_payback(0, subsidy.amount_inr, size.size_kw, request.monthly_units)

    return models.Calculation(
        scope=CalculationScope.REQUEST_ESTIMATE,
        request_id=request.id,
        rule_set_id=request.rule_set_id,
        recommended_kw=size.size_kw,
        roof_cap_kw=size.max_kw,
        system_kw=size.size_kw,
        subsidy_inr=subsidy.amount_inr,
        annual_generation_kwh=to_inr(savings.annual_generation_kwh),
        annual_savings_inr=savings.annual_saving_inr,
        monthly_savings_inr=savings.monthly_saving_inr,
        bill_reduction_pct=savings.bill_reduction_pct,
        inputs_snapshot=_jsonable(
            {
                "monthly_units": request.monthly_units,
                "roof_area_sqm": request.roof_area_sqm,
                "state_category": category,
            }
        ),
        steps=_steps(
            [
                *size.steps,
                *subsidy.steps,
                *(s for s in savings.steps if s.key not in _PRICE_STEPS),
            ]
        ),
        citation_keys=_citations(size.citations, subsidy.citations, savings.citations),
        engine_version=ENGINE_VERSION,
    )


def quote_financials(quote: models.Quote, request: models.SolarRequest) -> models.Calculation:
    """Subsidy, net cost, savings and payback for one quote."""
    category = _category(request.state_category)
    subsidy = calculate_subsidy(quote.system_kw, category)
    payback = calculate_payback(
        quote.price_total_inr, subsidy.amount_inr, quote.system_kw, request.monthly_units
    )

    return models.Calculation(
        scope=CalculationScope.QUOTE_FINANCIALS,
        request_id=request.id,
        quote_id=quote.id,
        rule_set_id=request.rule_set_id,
        system_kw=quote.system_kw,
        gross_cost_inr=quote.price_total_inr,
        subsidy_inr=subsidy.amount_inr,
        net_cost_inr=payback.net_cost_inr,
        annual_generation_kwh=to_inr(payback.annual_generation_kwh),
        annual_savings_inr=payback.annual_saving_inr,
        monthly_savings_inr=payback.monthly_saving_inr,
        bill_reduction_pct=payback.bill_reduction_pct,
        payback_years=payback.payback_years,
        inputs_snapshot=_jsonable(
            {
                "price_total_inr": quote.price_total_inr,
                "system_kw": quote.system_kw,
                "monthly_units": request.monthly_units,
                "state_category": category,
            }
        ),
        steps=_steps([*subsidy.steps, *payback.steps]),
        citation_keys=_citations(subsidy.citations, payback.citations),
        engine_version=ENGINE_VERSION,
    )
