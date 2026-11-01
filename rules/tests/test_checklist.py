from rules.checklist import REQUIRED_INCLUSIONS, TOTAL_ITEMS, QuoteFacts, missing_items


def test_bare_quote_is_missing_everything() -> None:
    assert len(missing_items(QuoteFacts("q", 100_000, 3))) == TOTAL_ITEMS


def test_complete_quote_is_missing_nothing() -> None:
    quote = QuoteFacts(
        "q",
        100_000,
        3,
        warranty_inverter_yrs=10,
        warranty_work_yrs=5,
        dcr=True,
        mnre_registered=True,
        inclusions=frozenset(REQUIRED_INCLUSIONS),
    )
    assert missing_items(quote) == ()


def test_stating_non_dcr_panels_is_an_answer_not_a_gap() -> None:
    assert "dcr_panels" not in missing_items(QuoteFacts("q", 100_000, 3, dcr=False))
