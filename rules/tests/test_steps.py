"""The working shown beside each figure. Steps must agree with the numbers they explain."""

from decimal import Decimal

import pytest

from rules.loader import load_rules
from rules.payback import PaybackResult, calculate_payback
from rules.sizing import SizingResult, suggest_size
from rules.steps import Step, fmt
from rules.subsidy import SubsidyResult, calculate_subsidy

Result = SizingResult | SubsidyResult | PaybackResult


def _table(steps: tuple[Step, ...]) -> list[tuple[str, str, str]]:
    return [(s.key, s.formula, s.value) for s in steps]


def test_sizing_steps_for_the_golden_household() -> None:
    result = suggest_size(monthly_units=330, roof_area_m2=Decimal(40))

    assert _table(result.steps) == [
        ("raw_kw", "330 units ÷ 120 units per kW per month", "2.75"),
        ("wanted_kw", "2.75 kW rounded to the nearest 0.5 kW", "3"),
        ("usable_area", "40 m² × 0.8 usable", "32"),
        ("max_kw", "32 m² ÷ 10 m² per kW, rounded down to 0.5 kW", "3"),
        ("size_kw", "smaller of 3 kW and 3 kW", "3"),
    ]
    rule_keys = [s.rule_key for s in result.steps]
    assert rule_keys == ["GENERATION", None, "USABLE_FRACTION", "ROOF_AREA", None]


def test_assessed_roof_fraction_has_no_assumption_citation() -> None:
    result = suggest_size(330, Decimal(40), Decimal("0.5"))
    usable = next(s for s in result.steps if s.key == "usable_area")
    assert (usable.formula, usable.value, usable.rule_key) == ("40 m² × 0.5 usable", "20", None)


def test_subsidy_steps_at_the_cap() -> None:
    result = calculate_subsidy(Decimal(5))

    assert _table(result.steps) == [
        ("first_slab", "2 kW × ₹30000 per kW", "60000"),
        ("second_slab", "1 kW × ₹18000 per kW", "18000"),
        ("above_cap", "2 kW above 3 kW × ₹0", "0"),
        ("subsidy", "₹60000 + ₹18000", "78000"),
    ]
    assert [s.rule_key for s in result.steps] == ["CFA_SLAB_1", "CFA_SLAB_2", "CFA_CAP", None]


def test_subsidy_steps_below_the_second_slab() -> None:
    result = calculate_subsidy(Decimal("1.5"))
    assert _table(result.steps) == [
        ("first_slab", "1.5 kW × ₹30000 per kW", "45000"),
        ("subsidy", "₹45000", "45000"),
    ]


def test_special_category_cites_the_special_rates() -> None:
    result = calculate_subsidy(Decimal(3), "special")
    assert [s.rule_key for s in result.steps] == ["CFA_SPECIAL", "CFA_SPECIAL", None]
    assert result.steps[-1].value == "85800"


def test_payback_steps_for_the_golden_household() -> None:
    result = calculate_payback(185_000, 78_000, Decimal(3), 330)

    assert _table(result.steps) == [
        ("annual_generation", "3 kW × 120 units × 12 months", "4320"),
        ("annual_consumption", "330 units × 12 months", "3960"),
        ("annual_saving", "smaller of 4320 and 3960 kWh × ₹6.5 per kWh", "25740"),
        ("monthly_saving", "₹25740 ÷ 12 months", "2145"),
        ("bill_reduction", "3960 kWh ÷ 3960 kWh × 100", "100"),
        ("net_cost", "₹185000 − ₹78000", "107000"),
        ("payback", "₹107000 ÷ ₹25740 per year", "4.2"),
    ]
    assert result.monthly_saving_inr == 2145
    assert result.bill_reduction_pct == Decimal(100)


def test_partial_offset_reduces_the_bill_by_less_than_all() -> None:
    result = calculate_payback(100_000, 30_000, Decimal(1), 500, Decimal(10))
    assert result.bill_reduction_pct == Decimal(24)
    assert result.monthly_saving_inr == 1200


def test_no_saving_says_so_instead_of_a_number() -> None:
    result = calculate_payback(100_000, 30_000, Decimal(3), 0)

    payback = result.steps[-1]
    assert (payback.key, payback.value, payback.unit) == ("payback", "never", None)
    assert result.bill_reduction_pct is None


@pytest.mark.parametrize(
    "result",
    [
        suggest_size(330, Decimal(40)),
        suggest_size(600, Decimal(20), Decimal("0.75")),
        calculate_subsidy(Decimal("2.5"), "special"),
        calculate_subsidy(Decimal(0)),
        calculate_payback(185_000, 78_000, Decimal(3), 330, Decimal(7)),
        calculate_payback(100_000, 30_000, Decimal(3), 0),
    ],
)
def test_every_step_cites_a_rule_the_result_also_cites(result: Result) -> None:
    known = set(load_rules().citations)
    for step in result.steps:
        if step.rule_key is not None:
            assert step.rule_key in result.citations
            assert step.rule_key in known
        assert step.label
        assert step.key


def test_final_steps_match_the_returned_figures() -> None:
    sizing = suggest_size(330, Decimal(40))
    subsidy = calculate_subsidy(sizing.size_kw)
    payback = calculate_payback(185_000, subsidy.amount_inr, sizing.size_kw, 330)

    assert sizing.steps[-1].value == fmt(sizing.size_kw)
    assert subsidy.steps[-1].value == str(subsidy.amount_inr)
    assert payback.steps[-1].value == fmt(payback.payback_years or Decimal(0))


@pytest.mark.parametrize(
    ("value", "expected"),
    [("3.0", "3"), ("2.75", "2.75"), ("0.833333", "0.83"), ("100", "100"), ("4320.00", "4320")],
)
def test_fmt_drops_trailing_zeros_and_never_uses_exponents(value: str, expected: str) -> None:
    assert fmt(Decimal(value)) == expected
