from decimal import Decimal

import pytest

from rules.loader import load_rules
from rules.payback import calculate_payback


def test_saving_is_limited_by_generation_when_usage_is_higher() -> None:
    result = calculate_payback(100_000, 30_000, Decimal(1), 500, Decimal(10))
    assert result.annual_saving_inr == 14_400


def test_saving_is_limited_by_consumption_when_generation_is_higher() -> None:
    result = calculate_payback(100_000, 30_000, Decimal(10), 100, Decimal(10))
    assert result.annual_saving_inr == 12_000


def test_payback_is_none_when_there_is_no_saving() -> None:
    assert calculate_payback(100_000, 30_000, Decimal(3), 0).payback_years is None


def test_net_cost_never_goes_below_zero() -> None:
    assert calculate_payback(50_000, 78_000, Decimal(3), 300).net_cost_inr == 0


def test_default_tariff_is_cited_only_when_used() -> None:
    assert "TARIFF_DEFAULT" in calculate_payback(1, 0, Decimal(1), 100).citations
    assert "TARIFF_DEFAULT" not in calculate_payback(1, 0, Decimal(1), 100, Decimal(7)).citations


@pytest.mark.parametrize(
    ("price", "subsidy", "capacity", "units"),
    [(-1, 0, "1", 100), (1, -1, "1", 100), (1, 0, "-1", 100), (1, 0, "1", -100)],
)
def test_rejects_negative_input(price: int, subsidy: int, capacity: str, units: int) -> None:
    with pytest.raises(ValueError, match="negative"):
        calculate_payback(price, subsidy, Decimal(capacity), units)


def test_citations_exist() -> None:
    citations = calculate_payback(1, 0, Decimal(1), 100).citations
    assert set(citations) <= set(load_rules().citations)
