"""HTTP client for interacting with OSRM services."""

from __future__ import annotations

import time
from typing import Sequence

import httpx

from ...config import settings


class OSRMClient:
    def __init__(
        self,
        base_url: str | None = None,
        profile: str | None = None,
        timeout: float = 30.0,
        max_retries: int | None = None,
        backoff_seconds: float | None = None,
    ) -> None:
        self.base_url = base_url or settings.osrm_base_url
        if not self.base_url:
            raise ValueError("OSRM base URL is not configured.")
        self.profile = profile or settings.osrm_profile
        self.max_retries = max_retries if max_retries is not None else settings.osrm_max_retries
        self.backoff_seconds = backoff_seconds if backoff_seconds is not None else settings.osrm_backoff_seconds
        self._client = httpx.Client(timeout=timeout)

    def table(self, coordinates: Sequence[tuple[float, float]]) -> dict:
        if len(coordinates) < 2:
            raise ValueError("At least two coordinates are required for OSRM table.")

        coordinate_str = ";".join(f"{lon},{lat}" for lat, lon in coordinates)
        index_sequence = ";".join(str(i) for i in range(len(coordinates)))
        params = {
            "annotations": "duration,distance",
            "sources": index_sequence,
            "destinations": index_sequence,
        }
        url = f"{self.base_url}/table/v1/{self.profile}/{coordinate_str}"

        attempt = 0
        while True:
            try:
                response = self._client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                if "durations" not in data or "distances" not in data:
                    raise ValueError("OSRM response missing durations/distances.")
                return data
            except (httpx.HTTPError, ValueError) as error:
                attempt += 1
                if attempt > self.max_retries:
                    raise
                time.sleep(self.backoff_seconds * attempt)


def build_coordinate_list(depot_lat: float, depot_lon: float, customers: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    return [(depot_lat, depot_lon), *customers]


def check_health(base_url: str | None = None) -> bool:
    base = base_url or settings.osrm_base_url
    if not base:
        return False
    try:
        response = httpx.get(f"{base}/health", timeout=5.0)
        response.raise_for_status()
        return True
    except httpx.HTTPError:
        return False
