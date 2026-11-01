"""Distances and the approximate location vendors see before a quote is accepted."""

import math
from decimal import ROUND_HALF_UP, Decimal

EARTH_RADIUS_KM = 6371.0088
# 0.005 degrees is about 550 m north to south, so a vendor sees a point within ~275 m.
GRID_DEG = 0.005


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def approx_point(lat: float, lng: float) -> tuple[float, float]:
    """The centre of the grid cell holding the point. Neighbours share a cell, so the exact
    house cannot be told apart from others nearby."""

    def snap(value: float) -> float:
        return round((math.floor(value / GRID_DEG) + 0.5) * GRID_DEG, 6)

    return snap(lat), snap(lng)


def km(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
