"""Data access helpers for loading customer and depot information."""

from __future__ import annotations

import csv
import functools
from pathlib import Path
from typing import Iterable, Iterator, Optional

from .dc_repository import get_depots
from ..config import settings
from ..models.domain import Customer, Depot


def _coerce_float(value: Optional[str]) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value.replace(",", ""))
    except ValueError as exc:
        raise ValueError(f"Unable to parse float from value '{value}'") from exc


@functools.lru_cache(maxsize=1)
def load_customers(source: Optional[Path] = None) -> tuple[Customer, ...]:
    """Load customers from the configured CSV file."""

    csv_path = (source or settings.customer_file)
    if not csv_path.exists():
        raise FileNotFoundError(f"Customer file not found: {csv_path}")

    customers: list[Customer] = []
    with csv_path.open(mode="r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"Customer file '{csv_path}' is missing a header row.")
        for row in reader:
            lat = _coerce_float(row.get("Latitude") or row.get("latitude"))
            lon = _coerce_float(row.get("Longitude") or row.get("longitude"))
            if lat is None or lon is None:
                continue  # ignore records without coordinates
            customers.append(
                Customer(
                    area=(row.get("Area") or row.get("area") or "").strip() or None,
                    region=(row.get("Region") or row.get("region") or "").strip() or None,
                    city=(row.get("City") or row.get("city") or "").strip() or None,
                    zone=(row.get("Zone") or row.get("zone") or "").strip() or None,
                    agent_id=(row.get("AgentId") or row.get("agent_id") or "").strip() or None,
                    agent_name=(row.get("AgentName") or row.get("agent_name") or "").strip() or None,
                    customer_id=(row.get("CusId") or row.get("customer_id") or row.get("CustomerId") or "").strip(),
                    customer_name=(row.get("CusName") or row.get("customer_name") or row.get("CustomerName") or "").strip(),
                    latitude=lat,
                    longitude=lon,
                    status=(row.get("Status") or row.get("status") or "").strip() or None,
                    raw=row,
                )
            )
    return tuple(customers)


def iter_customers_for_location(location: str, source: Optional[Path] = None) -> Iterator[Customer]:
    normalized = location.strip().lower()
    for customer in load_customers(source):
        if customer.city and customer.city.lower() == normalized:
            yield customer
            continue
        if customer.area and customer.area.lower() == normalized:
            yield customer
            continue
        if customer.zone and customer.zone.lower() == normalized:
            yield customer


def get_customers_for_location(location: str, source: Optional[Path] = None) -> tuple[Customer, ...]:
    return tuple(iter_customers_for_location(location, source))


@functools.lru_cache(maxsize=1)
def get_dc_lookup() -> dict[str, Depot]:
    lookup: dict[str, Depot] = {}
    for depot in get_depots():
        key = depot.code.lower()
        lookup[key] = depot
        compact = key.replace(" ", "")
        lookup.setdefault(compact, depot)
        lookup.setdefault(compact[:3], depot)
    return lookup


def resolve_depot(city: str) -> Optional[Depot]:
    depot_map = get_dc_lookup()
    normalized = city.strip().lower()
    return depot_map.get(normalized) or depot_map.get(normalized.replace(" ", "")) or depot_map.get(normalized[:3])


def set_active_customer_file(path: Path) -> None:
    """Update the active customer CSV and clear related caches."""

    settings.customer_file = path
    load_customers.cache_clear()
    get_dc_lookup.cache_clear()
