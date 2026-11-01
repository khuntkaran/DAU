"""One line of working behind a calculated figure, shown in the UI with a link to its rule."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

Unit = Literal["kW", "m²", "kWh", "INR", "%", "years"]


@dataclass(frozen=True)
class Step:
    key: str
    """Stable id, so the web app can translate the label."""
    label: str
    formula: str
    value: str
    unit: Unit | None
    rule_key: str | None = None
    """Citation key for this line, or None for plain arithmetic."""


def fmt(value: Decimal, places: int = 2) -> str:
    """Display form only: rounded for reading, trailing zeros dropped, never in exponent form."""
    rounded = value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return format(rounded.normalize(), "f")
