"""Isochrone-based zoning leveraging OSRM routing durations."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import httpx

from ...config import settings
from ...models.domain import Customer, Depot
from ..geospatial import haversine_km
from .base import ZoningResult, ZoningStrategy


class IsochroneZoning(ZoningStrategy):
    """Assign customers to concentric time bands from the depot."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=30.0)

    def generate(
        self,
        *,
        depot: Depot,
        customers: Sequence[Customer],
        target_zones: int | None = None,
        thresholds: Sequence[int] | None = None,
        max_batch_size: int = 90,
    ) -> ZoningResult:
        thresholds = sorted(thresholds or settings.default_isochrones)
        durations = self._compute_travel_minutes(depot, customers, max_batch_size=max_batch_size)
        assignments: dict[str, str] = {}
        for customer, duration in zip(customers, durations):
            zone_label = self._match_threshold(duration, thresholds, target_zones)
            assignments[customer.customer_id] = zone_label
        metadata = {"strategy": "isochrone", "thresholds": thresholds, "uses_osrm": bool(settings.osrm_base_url)}
        return ZoningResult(assignments, metadata=metadata)

    def _compute_travel_minutes(
        self,
        depot: Depot,
        customers: Sequence[Customer],
        *,
        max_batch_size: int,
    ) -> list[float]:
        """Compute travel durations in minutes from depot to customers.
        
        Note: This method is kept for backward compatibility. The new implementation
        in service.py computes both duration and distance for all zone types.
        """
        if not settings.osrm_base_url:
            return self._fallback_haversine_minutes(depot, customers)

        durations: list[float] = []
        coords = [(depot.longitude, depot.latitude)] + [(c.longitude, c.latitude) for c in customers]
        # Chunk to respect OSRM table limits.
        for start in range(1, len(coords), max_batch_size):
            chunk = coords[0:1] + coords[start : start + max_batch_size]
            chunk_durations, _ = self._call_osrm_table(chunk)  # Get durations, ignore distances for now
            durations.extend(chunk_durations)
        return durations

    def _call_osrm_table(self, coords: list[tuple[float, float]]) -> tuple[list[float], list[float]]:
        """Call OSRM table endpoint and return both durations and distances.
        
        Returns:
            Tuple of (durations_minutes, distances_km)
        """
        coordinates = ";".join(f"{lon},{lat}" for lon, lat in coords)
        params = {
            "annotations": "duration,distance",  # Get both duration and distance
            "sources": "0",
            "destinations": ";".join(str(i) for i in range(1, len(coords))),
        }
        url = f"{settings.osrm_base_url}/table/v1/{settings.osrm_profile}/{coordinates}"
        response = self._client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        durations_seconds = data.get("durations", [[]])[0] if "durations" in data else []
        distances_meters = data.get("distances", [[]])[0] if "distances" in data else []
        
        durations_min = [value / 60.0 if value is not None else math.inf for value in durations_seconds]
        distances_km = [value / 1000.0 if value is not None else math.inf for value in distances_meters]
        
        return durations_min, distances_km

    @staticmethod
    def _fallback_haversine_minutes(depot: Depot, customers: Sequence[Customer], average_speed_kmh: float = 40.0) -> list[float]:
        durations: list[float] = []
        for customer in customers:
            distance = haversine_km(depot.latitude, depot.longitude, customer.latitude, customer.longitude)
            durations.append((distance / average_speed_kmh) * 60.0)
        return durations

    @staticmethod
    def _match_threshold(duration: float, thresholds: Sequence[int], target_zones: int | None) -> str:
        for threshold in thresholds:
            if duration <= threshold:
                return f"ISO{threshold:03d}"
        if target_zones and len(thresholds) < target_zones:
            extra_index = min(len(thresholds) + 1, target_zones)
            return f"ISOX{extra_index:02d}"
        return "ISO_OUT_OF_RANGE"
