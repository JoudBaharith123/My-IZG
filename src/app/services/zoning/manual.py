"""Manual polygon-based zoning assignment."""

from __future__ import annotations

from typing import Sequence

from ...models.domain import Customer, Depot
from ..geospatial import point_in_polygon
from .base import ZoningResult, ZoningStrategy


class ManualPolygonZoning(ZoningStrategy):
    """Assign customers to zones defined by user-supplied polygons."""

    def generate(
        self,
        *,
        depot: Depot,
        customers: Sequence[Customer],
        target_zones: int | None = None,
        polygons: Sequence[dict],
    ) -> ZoningResult:
        if not polygons:
            raise ValueError("polygons must be provided for manual zoning.")

        assignments: dict[str, str] = {}
        unassigned: list[str] = []
        for customer in customers:
            assigned_zone = None
            for polygon in polygons:
                coords = polygon["coordinates"]
                zone_id = polygon.get("zone_id")
                if not zone_id:
                    raise ValueError("polygon definition missing 'zone_id'.")
                if point_in_polygon(customer.latitude, customer.longitude, coords):
                    assigned_zone = zone_id
                    break
            if assigned_zone:
                assignments[customer.customer_id] = assigned_zone
            else:
                unassigned.append(customer.customer_id)

        metadata = {
            "strategy": "manual",
            "unassigned_customers": unassigned,
            "polygons": [polygon.get("zone_id") for polygon in polygons],
        }
        return ZoningResult(assignments, metadata=metadata)
