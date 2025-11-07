"""Geospatial helper functions."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

from shapely.geometry import Point, Polygon

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute distance between two coordinates using the Haversine formula."""

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the initial bearing from (lat1, lon1) to (lat2, lon2)."""

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360) % 360


def point_in_polygon(lat: float, lon: float, polygon_coords: Sequence[tuple[float, float]]) -> bool:
    """Return True if the point is inside the polygon denoted by (lat, lon) pairs."""

    polygon = Polygon([(lng, lat) for lat, lng in polygon_coords])
    return polygon.contains(Point(lon, lat))
