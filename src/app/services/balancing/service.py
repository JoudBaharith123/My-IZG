"""Workload balancing for zoning assignments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from ...models.domain import Customer
from ..geospatial import haversine_km


@dataclass(slots=True)
class BalanceTransfer:
    customer_id: str
    from_zone: str
    to_zone: str
    distance_km: float


@dataclass(slots=True)
class BalanceResult:
    assignments: Dict[str, str]
    transfers: List[BalanceTransfer]
    counts_before: Dict[str, int]
    counts_after: Dict[str, int]
    tolerance: float


def _zone_centroid(customers: Sequence[Customer]) -> Tuple[float, float]:
    if not customers:
        return (0.0, 0.0)
    lat = sum(c.latitude for c in customers) / len(customers)
    lon = sum(c.longitude for c in customers) / len(customers)
    return (lat, lon)


def _compute_bounds(counts: Dict[str, int], tolerance: float) -> Tuple[float, float, float]:
    total = sum(counts.values())
    zones = max(1, len(counts))
    avg = total / zones
    lower = avg * (1 - tolerance)
    upper = avg * (1 + tolerance)
    return avg, lower, upper


def _build_zone_map(assignments: Dict[str, str], customers: Sequence[Customer]) -> Dict[str, List[Customer]]:
    lookup: Dict[str, List[Customer]] = {}
    by_id = {customer.customer_id: customer for customer in customers}
    for cid, zone in assignments.items():
        customer = by_id.get(cid)
        if customer is None:
            continue
        lookup.setdefault(zone, []).append(customer)
    return lookup


def balance_assignments(
    assignments: Dict[str, str],
    customers: Sequence[Customer],
    *,
    tolerance: float = 0.2,
    max_iterations: int | None = None,
) -> BalanceResult:
    if tolerance < 0:
        raise ValueError("tolerance must be >= 0")

    zone_map = _build_zone_map(assignments, customers)
    counts_before = {zone: len(items) for zone, items in zone_map.items()}
    counts = counts_before.copy()
    transfers: list[BalanceTransfer] = []

    avg, lower, upper = _compute_bounds(counts, tolerance)
    if not counts:
        return BalanceResult(assignments=assignments, transfers=[], counts_before={}, counts_after={}, tolerance=tolerance)

    max_iterations = max_iterations or len(assignments)

    for _ in range(max_iterations):
        overloaded = max(counts.items(), key=lambda item: item[1])
        underloaded = min(counts.items(), key=lambda item: item[1])

        over_zone, over_count = overloaded
        under_zone, under_count = underloaded

        if over_count <= upper or under_count >= lower:
            break

        candidates = zone_map.get(over_zone, [])
        if not candidates:
            break

        target_centroid = _zone_centroid(zone_map.get(under_zone, []))
        if target_centroid == (0.0, 0.0) and zone_map.get(under_zone, []):
            target_centroid = _zone_centroid(zone_map[under_zone])

        def customer_distance(customer: Customer) -> float:
            return haversine_km(customer.latitude, customer.longitude, target_centroid[0], target_centroid[1])

        customer_to_move = min(candidates, key=customer_distance)

        zone_map[over_zone].remove(customer_to_move)
        zone_map.setdefault(under_zone, []).append(customer_to_move)
        counts[over_zone] -= 1
        counts[under_zone] += 1
        assignments[customer_to_move.customer_id] = under_zone
        transfers.append(
            BalanceTransfer(
                customer_id=customer_to_move.customer_id,
                from_zone=over_zone,
                to_zone=under_zone,
                distance_km=customer_distance(customer_to_move),
            )
        )

        avg, lower, upper = _compute_bounds(counts, tolerance)

    counts_after = counts
    return BalanceResult(
        assignments=assignments,
        transfers=transfers,
        counts_before=counts_before,
        counts_after=counts_after,
        tolerance=tolerance,
    )
