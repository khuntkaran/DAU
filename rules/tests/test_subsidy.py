from decimal import Decimal

import pytest

from rules.loader import load_rules
from rules.subsidy import calculate_subsidy


def test_rejects_negative_capacity() -> None:
    with pytest.raises(ValueError, match="negative"):
        calculate_subsidy(Decimal(-1))


@pytest.mark.parametrize(
    ("capacity", "category", "expected"),
    [
        ("1", "general", ("CFA_SLAB_1",)),
        ("2.5", "general", ("CFA_SLAB_1", "CFA_SLAB_2", "CFA_PRO_RATA")),
        ("3", "general", ("CFA_SLAB_1", "CFA_SLAB_2", "CFA_CAP")),
        ("3", "special", ("CFA_SLAB_1", "CFA_SLAB_2", "CFA_CAP", "CFA_SPECIAL")),
    ],
)
def test_cites_each_rule_it_used(capacity: str, category: str, expected: tuple[str, ...]) -> None:
    result = calculate_subsidy(Decimal(capacity), category)  # type: ignore[arg-type]
    assert result.citations == expected


def test_every_citation_exists_in_the_rule_set() -> None:
    rules = load_rules()
    result = calculate_subsidy(Decimal("2.5"), "special")
    assert set(result.citations) <= set(rules.citations)
    assert result.rule_version == rules.version
