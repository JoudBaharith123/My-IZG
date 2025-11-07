"""Base classes for zoning strategy implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, Sequence

from ...models.domain import Customer, Depot


class ZoneAssignment(dict):
    """Represents a mapping from customer id to zone id."""

    customers: dict[str, str]


class ZoneOutput(Protocol):
    zone_id: str
    name: str
    customers: Sequence[Customer]


class ZoningStrategy(ABC):
    """Contract for zoning strategy implementations."""

    @abstractmethod
    def generate(
        self,
        *,
        depot: Depot,
        customers: Sequence[Customer],
        target_zones: int,
        **kwargs,
    ) -> "ZoningResult":
        raise NotImplementedError


class ZoningResult:
    """Container for resulting zone assignments."""

    def __init__(self, assignments: dict[str, str], metadata: dict | None = None):
        self.assignments = assignments
        self.metadata = metadata or {}

    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for zone_id in self.assignments.values():
            counts[zone_id] = counts.get(zone_id, 0) + 1
        return counts

    def customers_for_zone(self, zone_id: str, customers: Sequence[Customer]) -> list[Customer]:
        ids = {cid for cid, zid in self.assignments.items() if zid == zone_id}
        return [customer for customer in customers if customer.customer_id in ids]
