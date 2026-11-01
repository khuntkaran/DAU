"""Quote rules that sit between the HTTP schema and `rules/`."""

from collections.abc import Iterable

from api.app.enums import LineItemType
from rules.checklist import REQUIRED_INCLUSIONS

# Each checklist item from `rules.checklist`, and the line items that together satisfy it.
# An entry is a list of alternatives; each alternative needs all of its line items.
CHECKLIST_LINE_ITEMS: dict[str, list[frozenset[LineItemType]]] = {
    "net_metering_fee": [
        frozenset({LineItemType.NET_METER}),
        frozenset({LineItemType.DISCOM_FEES}),
    ],
    "mounting_structure": [frozenset({LineItemType.MOUNTING_STRUCTURE})],
    "earthing_and_lightning_arrester": [
        frozenset({LineItemType.EARTHING, LineItemType.LIGHTNING_ARRESTER})
    ],
    "amc": [frozenset({LineItemType.AMC})],
    "insurance": [frozenset({LineItemType.INSURANCE})],
}


def inclusions_from_line_items(
    items: Iterable[tuple[LineItemType, bool]],
) -> frozenset[str]:
    """Checklist items covered by the line items a vendor marked as included."""
    included = {item_type for item_type, is_included in items if is_included}
    return frozenset(
        name
        for name in REQUIRED_INCLUSIONS
        if any(needed <= included for needed in CHECKLIST_LINE_ITEMS[name])
    )
