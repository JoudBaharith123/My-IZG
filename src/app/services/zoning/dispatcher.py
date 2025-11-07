"""Factory for zoning strategies based on user selection."""

from __future__ import annotations

from typing import Any

from .base import ZoningResult, ZoningStrategy
from .clustering import ClusteringZoning
from .isochrone import IsochroneZoning
from .manual import ManualPolygonZoning
from .polar import PolarSectorZoning


def get_strategy(method: str, **kwargs: Any) -> ZoningStrategy:
    match method:
        case "polar":
            return PolarSectorZoning()
        case "isochrone":
            return IsochroneZoning()
        case "clustering":
            return ClusteringZoning(**{k: v for k, v in kwargs.items() if k in {"balance_tolerance"}})
        case "manual":
            return ManualPolygonZoning()
        case _:
            raise ValueError(f"Unknown zoning method '{method}'.")


def execute_strategy(method: str, **kwargs: Any) -> ZoningResult:
    strategy = get_strategy(method, **kwargs)
    return strategy.generate(**kwargs)
