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
                    # Use City column (supports both Arabic and English via resolve_depot translation)
                    city=(row.get("City") or row.get("city") or row.get("Area") or row.get("area") or "").strip() or None,
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
    """Get customers for a city/area/zone with geographic validation.
    
    Uses City column with coordinate validation to ensure data quality.
    Filters out customers with invalid or out-of-bounds coordinates.
    """
    normalized = location.strip().lower()
    
    # Geographic bounding boxes for each city (lat_min, lat_max, lon_min, lon_max)
    CITY_BOUNDARIES = {
        "jeddah": (21.2, 21.8, 39.0, 39.5),
        "جدة": (21.2, 21.8, 39.0, 39.5),
        "جده": (21.2, 21.8, 39.0, 39.5),
        "riyadh": (24.3, 24.9, 46.4, 47.0),
        "الرياض": (24.3, 24.9, 46.4, 47.0),
        "makkah": (21.3, 21.6, 39.7, 40.0),
        "مكة": (21.3, 21.6, 39.7, 40.0),
        "مكة المكرمة": (21.3, 21.6, 39.7, 40.0),
        "madinah": (24.3, 24.7, 39.4, 39.8),
        "madina": (24.3, 24.7, 39.4, 39.8),
        "المدينة": (24.3, 24.7, 39.4, 39.8),
        "المدينة المنورة": (24.3, 24.7, 39.4, 39.8),
        "dammam": (26.2, 26.6, 49.9, 50.3),
        "الدمام": (26.2, 26.6, 49.9, 50.3),
        "taif": (21.1, 21.5, 40.2, 40.7),
        "الطائف": (21.1, 21.5, 40.2, 40.7),
    }
    
    # Arabic to English city name mappings
    CITY_TRANSLATIONS = {
        "جدة": ["جدة", "jeddah", "جده", "جدّة"],
        "jeddah": ["جدة", "jeddah", "جده", "جدّة"],
        "الرياض": ["الرياض", "riyadh", "رياض"],
        "riyadh": ["الرياض", "riyadh", "رياض"],
        "مكة": ["مكة", "مكة المكرمة", "makkah", "mecca"],
        "مكة المكرمة": ["مكة", "مكة المكرمة", "makkah", "mecca"],
        "makkah": ["مكة", "مكة المكرمة", "makkah", "mecca"],
        "المدينة": ["المدينة", "المدينة المنورة", "madinah", "madina"],
        "المدينة المنورة": ["المدينة", "المدينة المنورة", "madinah", "madina"],
        "madinah": ["المدينة", "المدينة المنورة", "madinah", "madina"],
        "madina": ["المدينة", "المدينة المنورة", "madinah", "madina"],
        "الدمام": ["الدمام", "dammam", "دمام"],
        "dammam": ["الدمام", "dammam", "دمام"],
        "تبوك": ["تبوك", "tabuk"],
        "tabuk": ["تبوك", "tabuk"],
        "الطائف": ["الطائف", "taif"],
        "taif": ["الطائف", "taif"],
    }
    
    # Get all accepted variants for this city
    accepted_variants = CITY_TRANSLATIONS.get(normalized, [normalized])
    accepted_variants_set = set(v.lower() for v in accepted_variants)
    
    # Get geographic boundary for validation
    city_bounds = CITY_BOUNDARIES.get(normalized)
    
    for customer in load_customers(source):
        # Match by City column with variants
        city_match = customer.city and customer.city.lower() in accepted_variants_set
        
        # Match by Zone (for zone-specific queries)
        zone_match = customer.zone and customer.zone.lower() == normalized
        
        if not (city_match or zone_match):
            continue
        
        # Validate coordinates are within city boundaries (if boundary defined)
        if city_bounds and city_match:
            lat_min, lat_max, lon_min, lon_max = city_bounds
            # Skip customers with invalid or out-of-bounds coordinates
            if customer.latitude < lat_min or customer.latitude > lat_max:
                continue
            if customer.longitude < lon_min or customer.longitude > lon_max:
                continue
            # Skip invalid coordinates (0, 0) or negative values
            if customer.latitude <= 0 or customer.longitude <= 0:
                continue
        
        yield customer


def get_customers_for_location(location: str, source: Optional[Path] = None) -> tuple[Customer, ...]:
    return tuple(iter_customers_for_location(location, source))


@functools.lru_cache(maxsize=1)
def get_dc_lookup() -> dict[str, Depot]:
    """Get depot lookup dictionary. Cache is cleared when depots are synced to database."""
    lookup: dict[str, Depot] = {}
    for depot in get_depots():
        key = depot.code.lower()
        lookup[key] = depot
        compact = key.replace(" ", "")
        lookup.setdefault(compact, depot)
        lookup.setdefault(compact[:3], depot)
    return lookup


def clear_dc_lookup_cache() -> None:
    """Clear the depot lookup cache. Call this after syncing depots to database."""
    get_dc_lookup.cache_clear()


def resolve_depot(city: str) -> Optional[Depot]:
    """Resolve depot by city name with Arabic-English translation support."""
    # Arabic to English city name mappings
    CITY_TRANSLATIONS = {
        "جدة": "jeddah",
        "الرياض": "riyadh",
        "رياض": "riyadh",
        "الدمام": "dammam",
        "دمام": "dammam",
        "مكة": "jeddah",  # Makkah uses Jeddah depot
        "مكة المكرمة": "jeddah",  # Makkah uses Jeddah depot
        "المدينة": "madinah",
        "المدينة المنورة": "madinah",
        "تبوك": "tabuk",
        "خميس مشيط": "khames mushait",
        "بريدة": "buraidah",
        "جيزان": "jizan",
        "جازان": "jizan",  # Alternative spelling
        "حائل": "hail",
        "الطائف": "taif",
        "طائف": "taif",
        "ينبع": "yanbu",
        "نجران": "najran",
        "ابها": "khames mushait",  # Abha uses Khamis Mushait depot
        "عسير": "khames mushait",  # Asir uses Khamis Mushait depot
    }
    
    # Alternative English spellings and variations
    ALTERNATIVE_NAMES = {
        "makkah": "jeddah",  # Makkah uses Jeddah depot
        "mecca": "jeddah",
        "madinah": "madinah",
        "medina": "madinah",
        "medinah": "madinah",
        "khames": "khames mushait",
        "khamis": "khames mushait",
        "mushait": "khames mushait",
        "abha": "khames mushait",
        "asir": "khames mushait",
        "baha": "jeddah",  # Al-Baha uses Jeddah depot (nearest)
        "الباحة": "jeddah",
    }
    
    # Regional mappings - cities without direct depots mapped to nearest depot
    REGIONAL_MAPPINGS = {
        "محايل عسير": "khames mushait",  # Muhayil Asir uses Khamis Mushait
        "القصيم": "buraidah",  # Al-Qassim region uses Buraidah
        "عنيزة": "buraidah",  # Unaizah uses Buraidah
        "عرعر": "sakaka",  # Arar uses Sakaka (nearest)
        "الرس": "buraidah",  # Ar Rass uses Buraidah
        "القنفذة": "jeddah",  # Al Qunfudhah uses Jeddah
        "أبو عريش": "jizan",  # Abu Arish uses Jizan
    }
    
    depot_map = get_dc_lookup()
    normalized = city.strip().lower()
    
    # Try direct lookup
    depot = depot_map.get(normalized)
    if depot:
        return depot
    
    # Try without spaces
    depot = depot_map.get(normalized.replace(" ", ""))
    if depot:
        return depot
    
    # Try alternative English names
    if normalized in ALTERNATIVE_NAMES:
        alt_name = ALTERNATIVE_NAMES[normalized]
        depot = depot_map.get(alt_name)
        if depot:
            return depot
    
    # Try Arabic to English translation
    if normalized in CITY_TRANSLATIONS:
        english_name = CITY_TRANSLATIONS[normalized]
        depot = depot_map.get(english_name)
        if depot:
            return depot
    
    # Try regional mappings for cities without direct depots
    if normalized in REGIONAL_MAPPINGS:
        depot_name = REGIONAL_MAPPINGS[normalized]
        depot = depot_map.get(depot_name)
        if depot:
            return depot
    
    # Try partial matching - check if city name contains depot name or vice versa
    for depot_code, depot_obj in depot_map.items():
        depot_normalized = depot_code.lower().replace(" ", "")
        city_normalized = normalized.replace(" ", "")
        
        # Check if depot code is contained in city name or vice versa
        if depot_normalized in city_normalized or city_normalized in depot_normalized:
            # Additional validation: ensure it's a meaningful match (at least 3 chars)
            if len(depot_normalized) >= 3 and len(city_normalized) >= 3:
                return depot_obj
    
    # Try first 3 characters as last resort
    depot = depot_map.get(normalized[:3])
    if depot:
        return depot
    
    return None


def set_active_customer_file(path: Path) -> None:
    """Update the active customer CSV and clear related caches."""

    settings.customer_file = path
    load_customers.cache_clear()
    get_dc_lookup.cache_clear()
