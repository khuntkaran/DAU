"""Golden cases. A failure here means a number shown to households changed."""

from decimal import Decimal

import pytest

from rules.payback import calculate_payback
from rules.sizing import suggest_size
from rules.subsidy import calculate_subsidy


@pytest.mark.parametrize(
    ("capacity", "general", "special"),
    [
        ("0", 0, 0),
        ("1", 30_000, 33_000),
        ("2", 60_000, 66_000),
        ("2.5", 69_000, 75_900),
        ("3", 78_000, 85_800),
        ("5", 78_000, 85_800),
        ("10", 78_000, 85_800),
    ],
)
def test_subsidy_slabs(capacity: str, general: int, special: int) -> None:
    assert calculate_subsidy(Decimal(capacity)).amount_inr == general
    assert calculate_subsidy(Decimal(capacity), "special").amount_inr == special


def test_ahmedabad_household_end_to_end() -> None:
    """The design document shows 28,080 and 3.8 years, which ignores the consumption cap."""
    sizing = suggest_size(monthly_units=330, roof_area_m2=Decimal(40))
    assert sizing.raw_kw == Decimal("2.75")
    assert sizing.size_kw == Decimal("3.0")
    assert sizing.max_kw == Decimal("3.0")
    assert sizing.capped_by_roof is False

    subsidy = calculate_subsidy(sizing.size_kw)
    assert subsidy.amount_inr == 78_000

    result = calculate_payback(
        price_inr=185_000,
        subsidy_inr=subsidy.amount_inr,
        capacity_kw=sizing.size_kw,
        monthly_units=330,
        tariff_inr_per_kwh=Decimal("6.50"),
    )
    assert result.net_cost_inr == 107_000
    assert result.annual_generation_kwh == Decimal(4320)
    assert result.annual_consumption_kwh == Decimal(3960)
    assert result.annual_saving_inr == 25_740
    assert result.payback_years == Decimal("4.2")
