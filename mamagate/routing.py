"""Road routing from the referring PHC to a receiving facility.

Providers are tried in order and the first that answers wins:

1. Amazon Location Service Routes (``geo-routes`` CalculateRoutes),
   authorised with the caller's IAM credentials, no API key.
2. OSRM public demo server (OpenStreetMap data), only when
   ``MAMAGATE_ENABLE_OSRM=1`` because the demo server is for light use.
3. A straight-line estimate, always available and labelled as such.

Every result names the provider that produced it, so a routed time is
never confused with an estimate.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from dataclasses import asdict, dataclass

from mamagate.facilities import (
    ASSUMED_ROAD_FACTOR,
    ASSUMED_SPEED_KMH,
    haversine_km,
)

LOGGER = logging.getLogger(__name__)
REGION = os.environ.get("AWS_REGION", "us-east-1")
OSRM_URL = "https://router.project-osrm.org/route/v1/driving/"


@dataclass(frozen=True)
class Route:
    """A road distance and travel time between two points."""

    distance_km: float
    minutes: int
    provider: str
    note: str


def _amazon_location(
    origin: tuple[float, float], dest: tuple[float, float]
) -> Route:
    """Route with Amazon Location Service (positions are lon, lat)."""
    import boto3

    client = boto3.client("geo-routes", region_name=REGION)
    response = client.calculate_routes(
        Origin=[origin[1], origin[0]],
        Destination=[dest[1], dest[0]],
        TravelMode="Car",
        DepartNow=True,
    )
    summary = response["Routes"][0]["Summary"]
    return Route(
        distance_km=round(summary["Distance"] / 1000, 1),
        minutes=round(summary["Duration"] / 60),
        provider="amazon-location-service",
        note="Routed by car, departing now.",
    )


def _osrm(origin: tuple[float, float], dest: tuple[float, float]) -> Route:
    """Route with the OSRM public demo server (positions are lon, lat)."""
    url = (f"{OSRM_URL}{origin[1]},{origin[0]};{dest[1]},{dest[0]}"
           "?overview=false")
    request = urllib.request.Request(
        url, headers={"User-Agent": "mamagate-demo"})
    with urllib.request.urlopen(request, timeout=8) as handle:  # noqa: S310
        body = json.load(handle)
    leg = body["routes"][0]
    return Route(
        distance_km=round(leg["distance"] / 1000, 1),
        minutes=round(leg["duration"] / 60),
        provider="osrm-demo",
        note="Routed on OpenStreetMap data (no traffic).",
    )


def _straight_line(
    origin: tuple[float, float], dest: tuple[float, float]
) -> Route:
    """Estimate road distance and time from the straight-line distance."""
    km = haversine_km(*origin, *dest) * ASSUMED_ROAD_FACTOR
    return Route(
        distance_km=round(km, 1),
        minutes=round(km / ASSUMED_SPEED_KMH * 60),
        provider="straight-line-estimate",
        note="Not routed: straight line x1.3 at 40 km/h.",
    )


def route(
    origin: tuple[float, float], dest: tuple[float, float]
) -> dict:
    """Return the best available route as a dictionary.

    Args:
        origin: (latitude, longitude) of the referring PHC.
        dest: (latitude, longitude) of the receiving facility.

    Returns:
        Distance, minutes, provider name and a note on the method.

    """
    providers = []
    if os.environ.get("MAMAGATE_DISABLE_AWS_ROUTES") != "1":
        providers.append(_amazon_location)
    if os.environ.get("MAMAGATE_ENABLE_OSRM") == "1":
        providers.append(_osrm)
    for provider in providers:
        try:
            return asdict(provider(origin, dest))
        except Exception as exc:  # noqa: BLE001 - fall through to next
            LOGGER.warning("%s failed: %s", provider.__name__, exc)
    return asdict(_straight_line(origin, dest))
