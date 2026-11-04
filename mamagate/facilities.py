"""Receiving-facility lookup for referrals.

The bundled list is SYNTHETIC demo data placed around Kano. It exists
so the referral flow can be shown end to end without implying that any
real hospital has, or lacks, emergency obstetric capability. A pilot
would replace it with a verified registry such as GRID3 Nigeria health
facilities (CC BY 4.0), keeping the ``emonc`` field "unknown" unless a
source confirms it.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "facilities_synthetic.json"
EARTH_RADIUS_KM = 6371.0
ASSUMED_ROAD_FACTOR = 1.3
ASSUMED_SPEED_KMH = 40.0


@dataclass(frozen=True)
class Facility:
    """A candidate receiving facility."""

    facility_id: str
    name: str
    level: str
    lat: float
    lon: float
    emonc: str
    open_24h: str
    phone: str
    synthetic: bool = True


def load_facilities(path: Path = DATA_PATH) -> list[Facility]:
    """Load the facility list from JSON."""
    with open(path, encoding="utf-8") as handle:
        rows = json.load(handle)
    return [Facility(**row) for row in rows]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance between two points in km."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _check_nigeria(lat: float, lon: float) -> None:
    """Reject coordinates outside Nigeria's bounding box."""
    if not (4.0 <= lat <= 14.0 and 2.5 <= lon <= 15.0):
        raise ValueError(
            f"Coordinates ({lat}, {lon}) are outside Nigeria; check that "
            "latitude and longitude are not swapped.")


def rank_facilities(
    lat: float,
    lon: float,
    urgency: str,
    limit: int = 3,
    facilities: list[Facility] | None = None,
) -> list[dict]:
    """Rank receiving facilities for a referral.

    For ``REFER_NOW`` only secondary or tertiary facilities are
    candidates, and a facility whose emergency obstetric capability is
    recorded as ``yes`` is ranked ahead of one recorded as ``unknown``.
    Travel time is a straight-line estimate and is labelled as such.

    Args:
        lat: Latitude of the referring PHC.
        lon: Longitude of the referring PHC.
        urgency: Gate urgency for the case.
        limit: Maximum number of facilities to return.
        facilities: Optional facility list, mainly for tests.

    Returns:
        Facilities as dictionaries with distance and estimate fields.

    """
    _check_nigeria(lat, lon)
    pool = facilities if facilities is not None else load_facilities()
    if urgency == "REFER_NOW":
        pool = [f for f in pool if f.level in {"secondary", "tertiary"}]
    capability_rank = {"yes": 0, "unknown": 1, "no": 2}
    scored = []
    for fac in pool:
        km = haversine_km(lat, lon, fac.lat, fac.lon)
        road_km = km * ASSUMED_ROAD_FACTOR
        minutes = road_km / ASSUMED_SPEED_KMH * 60
        row = asdict(fac)
        row.update(
            straight_line_km=round(km, 1),
            est_road_km=round(road_km, 1),
            est_minutes=round(minutes),
            estimate_method=(
                "straight line x1.3 at 40 km/h; not a routed time"),
        )
        scored.append((capability_rank.get(fac.emonc, 1), minutes, row))
    scored.sort(key=lambda item: (item[0], item[1]))
    return [row for _, _, row in scored[:limit]]
