from api.app.enums import LineItemType as L
from api.app.services.quotes import CHECKLIST_LINE_ITEMS, inclusions_from_line_items
from rules.checklist import REQUIRED_INCLUSIONS


def test_every_checklist_item_can_be_met_by_line_items() -> None:
    assert set(CHECKLIST_LINE_ITEMS) == set(REQUIRED_INCLUSIONS)


def test_full_quote_covers_the_whole_checklist() -> None:
    items = [
        (L.NET_METER, True),
        (L.MOUNTING_STRUCTURE, True),
        (L.EARTHING, True),
        (L.LIGHTNING_ARRESTER, True),
        (L.AMC, True),
        (L.INSURANCE, True),
    ]
    assert inclusions_from_line_items(items) == set(REQUIRED_INCLUSIONS)


def test_discom_fees_also_count_as_the_net_metering_fee() -> None:
    assert inclusions_from_line_items([(L.DISCOM_FEES, True)]) == {"net_metering_fee"}


def test_earthing_without_a_lightning_arrester_is_not_enough() -> None:
    assert inclusions_from_line_items([(L.EARTHING, True)]) == frozenset()


def test_excluded_line_items_do_not_count() -> None:
    assert inclusions_from_line_items([(L.AMC, False), (L.INSURANCE, True)]) == {"insurance"}
