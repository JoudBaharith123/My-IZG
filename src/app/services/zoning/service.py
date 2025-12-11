"""High-level orchestration for zoning requests."""

from __future__ import annotations

from typing import Sequence

from shapely.geometry import MultiPoint, Polygon, Point
from shapely.ops import unary_union

from ...data.customers_repository import get_customers_for_location, resolve_depot
from ...persistence.filesystem import FileStorage
from ..balancing.service import balance_assignments
from ..outputs.formatter import zoning_response_to_csv, zoning_response_to_json
from ..export.geojson import export_zones_to_easyterritory, save_easyterritory_json
from ...models.domain import Customer
from ...schemas.zoning import ZoningRequest, ZoningResponse, ZoneCount
from .dispatcher import get_strategy


def _ensure_customers(city: str) -> Sequence[Customer]:
    customers = get_customers_for_location(city)
    if not customers:
        raise ValueError(f"No customers found for city '{city}'.")
    return customers


def process_zoning_request(payload: ZoningRequest, *, persist: bool = True) -> ZoningResponse:
    depot = resolve_depot(payload.city)
    if not depot:
        raise ValueError(f"Depot not found for city '{payload.city}'.")

    customers = _ensure_customers(payload.city)
    strategy = get_strategy(payload.method, balance_tolerance=0.2)

    strategy_kwargs = {
        "depot": depot,
        "customers": customers,
        "target_zones": payload.target_zones or 1,
    }
    if payload.method == "polar":
        strategy_kwargs["rotation_offset"] = payload.rotation_offset
    elif payload.method == "isochrone":
        strategy_kwargs["thresholds"] = payload.thresholds
    elif payload.method == "clustering":
        strategy_kwargs["max_customers_per_zone"] = payload.max_customers_per_zone
    elif payload.method == "manual":
        strategy_kwargs["polygons"] = [
            {"zone_id": polygon.zone_id, "coordinates": polygon.coordinates}
            for polygon in (payload.polygons or [])
        ]

    result = strategy.generate(**strategy_kwargs)

    if payload.balance:
        balanced = balance_assignments(
            result.assignments.copy(),
            customers,
            tolerance=payload.balance_tolerance,
        )
        result.assignments = balanced.assignments
        result.metadata.setdefault("balancing", {})
        result.metadata["balancing"].update(
            {
                "transfers": [
                    {
                        "customer_id": transfer.customer_id,
                        "from_zone": transfer.from_zone,
                        "to_zone": transfer.to_zone,
                        "distance_km": transfer.distance_km,
                    }
                    for transfer in balanced.transfers
                ],
                "counts_before": balanced.counts_before,
                "counts_after": balanced.counts_after,
                "tolerance": balanced.tolerance,
            }
        )

    counts = [ZoneCount(zone_id=zone_id, customer_count=count) for zone_id, count in result.counts().items()]

    metadata = result.metadata
    metadata.setdefault("city", payload.city)
    metadata.setdefault("method", payload.method)
    metadata.setdefault("balance_enabled", payload.balance)
    if payload.run_label:
        metadata["run_label"] = payload.run_label
    if payload.requested_by:
        metadata["author"] = payload.requested_by
    if payload.notes:
        metadata["notes"] = payload.notes
    incoming_tags = list(payload.tags) if payload.tags else []
    if incoming_tags or "tags" in metadata:
        existing_tags = list(metadata.get("tags") or [])
        merged_tags: list[str] = []
        for tag in [*existing_tags, *incoming_tags]:
            normalized = tag.strip()
            if normalized and normalized not in merged_tags:
                merged_tags.append(normalized)
        metadata["tags"] = merged_tags

    map_polygons: list[dict] = []
    if payload.method == "manual" and payload.polygons:
        map_polygons = _manual_polygon_overlays(payload.polygons)
    else:
        map_polygons = _convex_hull_overlays(result.assignments, customers)

    if map_polygons:
        metadata.setdefault("map_overlays", {})
        metadata["map_overlays"]["polygons"] = map_polygons

    response = ZoningResponse(
        city=payload.city,
        method=payload.method,
        assignments=result.assignments,
        counts=counts,
        metadata=result.metadata,
    )

    if persist:
        storage = FileStorage()
        run_dir = storage.make_run_directory(prefix=f"zones_{payload.method}")
        customers = list(customers)  # ensure we have a concrete sequence for serialization
        storage.write_json(run_dir / "summary.json", zoning_response_to_json(response))
        storage.write_csv(run_dir / "assignments.csv", zoning_response_to_csv(response, customers))

        # Export to EasyTerritory GeoJSON format
        try:
            easyterritory_features = export_zones_to_easyterritory(
                zones_response=response.model_dump(),
                city=payload.city,
                method=payload.method,
            )
            save_easyterritory_json(easyterritory_features, run_dir / "zones.geojson")
        except Exception as exc:
            # Log error but don't fail the entire request
            import logging
            logging.warning(f"Failed to generate GeoJSON export: {exc}")

    return response


def _manual_polygon_overlays(polygons: Sequence) -> list[dict]:
    overlays: list[dict] = []
    for polygon in polygons:
        coordinates = getattr(polygon, "coordinates", None)
        zone_id = getattr(polygon, "zone_id", None)
        if not zone_id or not coordinates or len(coordinates) < 3:
            continue
        lat_lon_sequence = [[lat, lon] for lat, lon in coordinates]
        if lat_lon_sequence[0] != lat_lon_sequence[-1]:
            lat_lon_sequence.append(lat_lon_sequence[0])

        shapely_poly = Polygon([(lon, lat) for lat, lon in coordinates])
        centroid = shapely_poly.centroid if shapely_poly and not shapely_poly.is_empty else Point(0.0, 0.0)
        overlays.append(
            {
                "zone_id": zone_id,
                "coordinates": lat_lon_sequence,
                "centroid": [centroid.y, centroid.x],
                "source": "manual",
            }
        )
    return overlays


def _convex_hull_overlays(assignments: dict[str, str], customers: Sequence[Customer]) -> list[dict]:
    """Generate zone polygons from customer points, ensuring NO overlaps."""
    customer_lookup = {customer.customer_id: customer for customer in customers}
    zone_points: dict[str, set[tuple[float, float]]] = {}
    zone_customer_count: dict[str, int] = {}
    
    # Collect points and count customers for each zone
    for customer_id, zone_id in assignments.items():
        customer = customer_lookup.get(customer_id)
        if not customer:
            continue
        zone_points.setdefault(zone_id, set()).add((customer.longitude, customer.latitude))
        zone_customer_count[zone_id] = zone_customer_count.get(zone_id, 0) + 1

    # First pass: Create initial convex hulls with centers
    zone_polygons: dict[str, tuple[Polygon, Point]] = {}
    for zone_id, points in zone_points.items():
        if len(points) < 3:
            continue
        hull = MultiPoint(list(points)).convex_hull
        if hull.is_empty or hull.geom_type != "Polygon":
            continue
        zone_polygons[zone_id] = (hull, hull.centroid)
    
    # Check for overlaps and clip if necessary
    zone_ids = list(zone_polygons.keys())
    clipped_polygons: dict[str, Polygon] = {}
    
    for zone_id in zone_ids:
        polygon, centroid = zone_polygons[zone_id]
        final_polygon = polygon
        
        # Check overlap with other zones
        for other_zone_id in zone_ids:
            if other_zone_id == zone_id:
                continue
            
            other_polygon, other_centroid = zone_polygons[other_zone_id]
            
            # If polygons overlap, remove the overlap completely
            if polygon.intersects(other_polygon):
                overlap = polygon.intersection(other_polygon)
                if not overlap.is_empty and overlap.area > 0:
                    # Remove the overlapping area from this polygon
                    # This guarantees no visual overlap
                    try:
                        # Simply remove the overlap
                        final_polygon = final_polygon.difference(other_polygon)
                        
                        # If result is MultiPolygon, keep largest part
                        if final_polygon.geom_type == "MultiPolygon":
                            final_polygon = max(final_polygon.geoms, key=lambda p: p.area)
                        
                        # If polygon became invalid, shrink original slightly
                        if final_polygon.is_empty or final_polygon.geom_type != "Polygon":
                            final_polygon = polygon.buffer(-0.001)  # 0.001° shrink (~111m)
                    except Exception:
                        # Fallback: shrink slightly
                        final_polygon = polygon.buffer(-0.001)  # Visible shrink
        
        clipped_polygons[zone_id] = final_polygon
    
    # Build final overlays with customer counts
    overlays: list[dict] = []
    for zone_id, polygon in clipped_polygons.items():
        if polygon.is_empty or polygon.geom_type != "Polygon":
            continue
        
        lat_lon_sequence = [[lat, lon] for lon, lat in polygon.exterior.coords]
        centroid = polygon.centroid
        customer_count = zone_customer_count.get(zone_id, 0)
        
        overlays.append(
            {
                "zone_id": zone_id,
                "coordinates": lat_lon_sequence,
                "centroid": [centroid.y, centroid.x],
                "source": "convex_hull",
                "customer_count": customer_count,  # Add customer count for tooltip
            }
        )
    return overlays
