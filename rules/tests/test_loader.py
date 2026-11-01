from decimal import Decimal

import pytest
from pydantic import ValidationError

from rules.loader import RULE_FILE, load_rules, parse_rules, to_inr


def test_rule_file_is_valid() -> None:
    rules = load_rules()
    assert rules.version == "pm_surya_ghar_v2024_03"
    assert rules.checked_on.isoformat() == "2026-11-01"


def test_weights_must_total_100() -> None:
    text = RULE_FILE.read_text(encoding="utf-8").replace(
        "net_cost_per_kw: 30", "net_cost_per_kw: 31"
    )
    with pytest.raises(ValidationError, match="total 100"):
        parse_rules(text)


def test_unknown_keys_are_rejected() -> None:
    text = RULE_FILE.read_text(encoding="utf-8") + "\nsurprise: true\n"
    with pytest.raises(ValidationError):
        parse_rules(text)


def test_rules_cannot_be_changed_at_runtime() -> None:
    with pytest.raises(ValidationError):
        load_rules().subsidy.general.first_slab_inr_per_kw = 1  # type: ignore[misc]


def test_assumptions_never_claim_a_source_link() -> None:
    for citation in load_rules().citations.values():
        if citation.status == "assumption":
            assert citation.url is None


def test_sourced_rules_have_a_link() -> None:
    for citation in load_rules().citations.values():
        if citation.status != "assumption":
            assert citation.url


@pytest.mark.parametrize(("amount", "expected"), [("10.4", 10), ("10.5", 11), ("11.5", 12)])
def test_rounds_half_up(amount: str, expected: int) -> None:
    assert to_inr(Decimal(amount)) == expected
