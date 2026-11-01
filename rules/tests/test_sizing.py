from decimal import Decimal

import pytest

from rules.loader import load_rules
from rules.sizing import suggest_size


@pytest.mark.parametrize(
    ("units", "expected"),
    [(0, "0"), (100, "1.0"), (150, "1.5"), (300, "2.5"), (330, "3.0"), (600, "5.0")],
)
def test_rounds_to_nearest_half_kw(units: int, expected: str) -> None:
    assert suggest_size(units, Decimal(1000)).size_kw == Decimal(expected)


def test_roof_limit_caps_size_and_rounds_down() -> None:
    result = suggest_size(600, Decimal(20), Decimal("0.75"))
    assert result.max_kw == Decimal("1.5")
    assert result.size_kw == Decimal("1.5")
    assert result.capped_by_roof is True


def test_assessed_fraction_replaces_default_and_its_citation() -> None:
    assert "USABLE_FRACTION" in suggest_size(300, Decimal(40)).citations
    assert "USABLE_FRACTION" not in suggest_size(300, Decimal(40), Decimal("0.5")).citations


def test_zero_usable_fraction_is_not_treated_as_missing() -> None:
    assert suggest_size(300, Decimal(40), Decimal(0)).size_kw == Decimal(0)


@pytest.mark.parametrize(
    ("units", "area", "fraction"),
    [(-1, "40", None), (100, "-1", None), (100, "40", "1.1"), (100, "40", "-0.1")],
)
def test_rejects_invalid_input(units: int, area: str, fraction: str | None) -> None:
    usable = None if fraction is None else Decimal(fraction)
    with pytest.raises(ValueError, match=r"negative|between"):
        suggest_size(units, Decimal(area), usable)


def test_citations_exist() -> None:
    assert set(suggest_size(100, Decimal(40)).citations) <= set(load_rules().citations)
