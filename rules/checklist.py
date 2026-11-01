"""Flags items a quote should state but does not."""

from dataclasses import dataclass, field

REQUIRED_INCLUSIONS = (
    "net_metering_fee",
    "mounting_structure",
    "earthing_and_lightning_arrester",
    "amc",
    "insurance",
)


@dataclass(frozen=True)
class QuoteFacts:
    """Structured quote data. `notes` is untrusted, and no calculation may read it."""

    quote_id: str
    net_cost_inr: int
    system_kw: float
    warranty_panel_yrs: int = 0
    warranty_inverter_yrs: int = 0
    warranty_work_yrs: int = 0
    timeline_days: int = 0
    vendor_rating: float = 0
    dcr: bool | None = None
    panel_brand: str = ""
    inverter_brand: str = ""
    mnre_registered: bool = False
    inclusions: frozenset[str] = field(default_factory=frozenset)
    notes: str = ""


def missing_items(quote: QuoteFacts) -> tuple[str, ...]:
    missing: list[str] = []
    if quote.dcr is None:
        missing.append("dcr_panels")
    if quote.warranty_inverter_yrs <= 0:
        missing.append("inverter_warranty")
    if quote.warranty_work_yrs <= 0:
        missing.append("workmanship_warranty")
    if not quote.mnre_registered:
        missing.append("mnre_vendor_registration")
    missing.extend(item for item in REQUIRED_INCLUSIONS if item not in quote.inclusions)
    return tuple(missing)


TOTAL_ITEMS = 4 + len(REQUIRED_INCLUSIONS)
