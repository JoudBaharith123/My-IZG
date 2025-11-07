"""Routing domain models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(slots=True)
class RouteStop:
    customer_id: str
    sequence: int
    arrival_min: float
    distance_from_prev_km: float


@dataclass(slots=True)
class RoutePlan:
    route_id: str
    day: str
    total_distance_km: float
    total_duration_min: float
    customer_count: int
    stops: List[RouteStop]
    constraint_violations: dict[str, float]


@dataclass(slots=True)
class RoutingResult:
    zone_id: str
    plans: List[RoutePlan]
    metadata: dict
