"""Customer analytics helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

from datetime import datetime, timezone
from ...data.customers_repository import load_customers
from ...config import settings


def compute_customer_stats(top_n: int = 3) -> dict:
    customers = load_customers()
    total_customers = len(customers)

    zone_counts: Counter[str] = Counter()
    for customer in customers:
        zone = (customer.zone or "").strip()
        if zone:
            zone_counts[zone] += 1

    assigned_total = sum(zone_counts.values())
    unassigned_total = total_customers - assigned_total
    unassigned_percentage = 0.0
    if total_customers:
        unassigned_percentage = round((unassigned_total / total_customers) * 100, 1)

    top_zones: List[dict] = []
    if assigned_total:
        for zone, count in zone_counts.most_common(top_n):
            ratio = round(count / assigned_total, 2)
            top_zones.append({"code": zone, "ratio": ratio, "customers": count})

    source_file = settings.customer_file
    file_meta: dict[str, object] = {
        "fileName": source_file.name,
        "sizeBytes": None,
        "modifiedAt": None,
    }
    try:
        stat = source_file.stat()
        file_meta["sizeBytes"] = stat.st_size
        file_meta["modifiedAt"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        pass

    return {
        "totalCustomers": total_customers,
        "unassignedPercentage": unassigned_percentage,
        "zonesDetected": len(zone_counts),
        "topZones": top_zones,
        "lastUpload": file_meta,
    }


def list_customer_cities(limit: Optional[int] = None) -> list[dict]:
    """Return a list of cities/areas present in the active dataset."""

    customers = load_customers()
    counts: Counter[str] = Counter()
    for customer in customers:
        label = _resolve_city_label(customer)
        if not label:
            continue
        counts[label] += 1

    ranked = sorted(
        counts.items(),
        key=lambda item: (-item[1], item[0].lower()),
    )
    items = [{"name": city, "customers": count} for city, count in ranked]
    if limit is not None:
        return items[: max(limit, 0)]
    return items


def compute_zone_summaries(city: Optional[str] = None) -> list[dict]:
    """Aggregate customer counts per zone, optionally filtered by city."""

    customers = load_customers()
    normalized_filter = city.lower() if city else None

    zone_totals: Dict[str, int] = {}
    zone_city_counts: Dict[str, Counter[str]] = defaultdict(Counter)

    for customer in customers:
        zone = (customer.zone or "").strip()
        if not zone:
            continue

        zone_totals[zone] = zone_totals.get(zone, 0) + 1

        candidate_city = _resolve_city_label(customer)
        if candidate_city:
            zone_city_counts[zone][candidate_city] += 1

    summaries: list[dict] = []
    for zone, total in zone_totals.items():
        city_label: Optional[str] = None
        if zone_city_counts.get(zone):
            city_label = zone_city_counts[zone].most_common(1)[0][0]

        if normalized_filter:
            if not city_label or city_label.lower() != normalized_filter:
                continue

        summaries.append(
            {
                "zone": zone,
                "city": city_label,
                "customers": total,
            }
        )

    return sorted(
        summaries,
        key=lambda item: ((item["city"] or "").lower(), item["zone"].lower()),
    )


def list_customer_locations(
    city: Optional[str] = None,
    zone: Optional[str] = None,
    *,
    offset: int = 0,
    limit: Optional[int] = None,
) -> Tuple[list[dict], int]:
    """Return customer coordinates, filtered by city and/or zone, with pagination support."""

    customers = load_customers()
    normalized_city = city.strip().lower() if isinstance(city, str) and city.strip() else None
    normalized_zone = zone.strip().lower() if isinstance(zone, str) and zone.strip() else None

    results: list[dict] = []
    matched_total = 0
    for customer in customers:
        if normalized_city and not _matches_city_filter(customer, normalized_city):
            continue
        if normalized_zone:
            zone_value = (customer.zone or "").strip().lower()
            if zone_value != normalized_zone:
                continue

        matched_total += 1
        if matched_total <= offset:
            continue

        if limit and len(results) >= limit:
            continue

        results.append(
            {
                "customer_id": customer.customer_id,
                "customer_name": customer.customer_name,
                "city": customer.city,
                "zone": customer.zone,
                "latitude": customer.latitude,
                "longitude": customer.longitude,
            }
        )
    return results, matched_total


def _resolve_city_label(customer: object) -> Optional[str]:
    """Return a displayable city label for a customer record."""

    for attribute in ("city", "area", "region"):
        value = getattr(customer, attribute, None)
        if value:
            label = str(value).strip()
            if label:
                return label
    return None


def _matches_city_filter(customer: object, normalized: str) -> bool:
    for attribute in ("city", "area", "region"):
        value = getattr(customer, attribute, None)
        if isinstance(value, str) and value.strip().lower() == normalized:
            return True
    return False


def analyze_customer_issues() -> dict:
    """Produce validation insights for the Upload & Validate workflow."""

    customers = load_customers()
    total_records = len(customers)

    missing_coordinates: list[dict] = []
    duplicates: dict[str, list[dict]] = defaultdict(list)
    finance_clearance: list[dict] = []

    seen_ids: Dict[str, int] = {}
    for customer in customers:
        record = {
            "customer_id": customer.customer_id,
            "customer_name": customer.customer_name,
            "city": customer.city,
            "zone": customer.zone,
            "latitude": customer.latitude,
            "longitude": customer.longitude,
            "status": customer.status,
        }

        if customer.latitude is None or customer.longitude is None:
            missing_coordinates.append(record)

        normalized_id = customer.customer_id.strip()
        if normalized_id:
            seen_ids.setdefault(normalized_id, 0)
            duplicates[normalized_id].append(record)

        if _requires_finance_clearance(customer):
            finance_clearance.append(record)

    duplicate_entries = [
        {"customer_id": customer_id, "records": records}
        for customer_id, records in duplicates.items()
        if len(records) > 1
    ]

    clearance_count = len(finance_clearance)
    return {
        "totalRecords": total_records,
        "issues": {
            "missingCoordinates": {
                "count": len(missing_coordinates),
                "sample": missing_coordinates[:10],
            },
            "duplicateCustomers": {
                "count": len(duplicate_entries),
                "duplicates": duplicate_entries[:5],
            },
            "financeClearance": {
                "count": clearance_count,
                "sample": finance_clearance[:10],
            },
        },
    }


def _requires_finance_clearance(customer: object) -> bool:
    """Heuristic to determine finance clearance need based on raw record."""

    raw = getattr(customer, "raw", {}) or {}
    status = _normalize_string(raw.get("FinanceClearance") or raw.get("Finance_Status") or customer.status)
    outstanding = _normalize_string(raw.get("PaymentStatus"))
    finance_flag = _normalize_string(raw.get("FinanceFlag"))

    keywords = {"pending", "required", "needs clearance", "open"}
    if status in keywords or finance_flag in keywords:
        return True
    if outstanding in {"pending", "past_due"}:
        return True
    return False


def _normalize_string(value: Optional[str]) -> str:
    return value.strip().lower() if isinstance(value, str) else ""
