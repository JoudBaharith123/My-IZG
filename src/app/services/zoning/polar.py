"""Polar sector based zoning implementation."""

from __future__ import annotations

import math
from typing import Sequence

from ...models.domain import Customer, Depot
from ..geospatial import bearing_degrees
from .base import ZoningResult, ZoningStrategy


class PolarSectorZoning(ZoningStrategy):
    """Split space around the depot into radial sectors."""

    def generate(
        self,
        *,
        depot: Depot,
        customers: Sequence[Customer],
        target_zones: int,
        rotation_offset: float = 0.0,
    ) -> ZoningResult:
        if target_zones < 1:
            raise ValueError("target_zones must be >= 1")

        sector_size = 360.0 / target_zones
        assignments: dict[str, str] = {}
        for customer in customers:
            bearing = (bearing_degrees(depot.latitude, depot.longitude, customer.latitude, customer.longitude) - rotation_offset) % 360
            sector_index = int(bearing // sector_size)
            zone_id = f"{depot.code[:3].upper()}{sector_index+1:03d}"
            assignments[customer.customer_id] = zone_id
        return ZoningResult(
            assignments,
            metadata={
                "strategy": "polar",
                "sector_size_degrees": sector_size,
                "rotation_offset": rotation_offset,
            },
        )
