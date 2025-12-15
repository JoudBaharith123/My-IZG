"""Routing orchestration service."""

from __future__ import annotations

from dataclasses import asdict
from typing import Sequence

from ...data.customers_repository import get_customers_for_location, resolve_depot
from ...models.domain import Customer
from ...persistence.filesystem import FileStorage
from ...schemas.routing import (
    RoutePlanModel,
    RouteStopModel,
    RoutingRequest,
    RoutingResponse,
)
from ..outputs.routing_formatter import routing_result_to_csv, routing_result_to_json
from ..export.geojson import export_routes_to_easyterritory, save_easyterritory_json
from .models import RoutePlan, RoutingResult
from .osrm_client import OSRMClient, build_coordinate_list
from .solver import SolverConstraints, solve_vrp


def _filter_customers(customers: Sequence[Customer], customer_ids: Sequence[str] | None) -> list[Customer]:
    if not customer_ids:
        return list(customers)
    id_set = {cid.strip() for cid in customer_ids}
    return [customer for customer in customers if customer.customer_id in id_set]


def _build_constraints(payload: RoutingRequest) -> SolverConstraints:
    base = SolverConstraints()
    overrides = payload.constraints
    return SolverConstraints(
        max_customers_per_route=overrides.max_customers_per_route
        if overrides and overrides.max_customers_per_route is not None
        else base.max_customers_per_route,
        min_customers_per_route=overrides.min_customers_per_route
        if overrides and overrides.min_customers_per_route is not None
        else base.min_customers_per_route,
        max_route_duration_minutes=overrides.max_route_duration_minutes
        if overrides and overrides.max_route_duration_minutes is not None
        else base.max_route_duration_minutes,
        max_distance_per_route_km=overrides.max_distance_per_route_km
        if overrides and overrides.max_distance_per_route_km is not None
        else base.max_distance_per_route_km,
    )


def optimize_routes(payload: RoutingRequest) -> RoutingResponse:
    import logging
    
    depot = resolve_depot(payload.city)
    if not depot:
        raise ValueError(f"Depot not found for city '{payload.city}'.")

    # Try to get customers from database zone assignments first
    # Falls back to CSV zone matching if zone not in database
    try:
        from ...persistence.database import get_customers_for_zone
        customers = get_customers_for_zone(payload.zone_id)
        logging.info(f"Retrieved {len(customers)} customers for zone '{payload.zone_id}' from database")
    except Exception as e:
        logging.error(f"Failed to retrieve customers for zone '{payload.zone_id}': {e}")
        raise ValueError(f"Failed to retrieve customers for zone '{payload.zone_id}': {str(e)}") from e
    
    if not customers:
        raise ValueError(f"No customers found for zone '{payload.zone_id}'. Make sure the zone has customers assigned in the database.")

    filtered_customers = _filter_customers(customers, payload.customer_ids)
    if not filtered_customers:
        raise ValueError("Customer list after filtering is empty.")

    coordinates = [(customer.latitude, customer.longitude) for customer in filtered_customers]
    
    # Initialize OSRM client with error handling
    try:
        osrm_client = OSRMClient()
    except ValueError as e:
        import logging
        logging.error(f"OSRM client initialization failed: {e}")
        raise ValueError(f"OSRM service is not configured. Please check OSRM_BASE_URL setting.") from e
    
    coordinate_list = build_coordinate_list(depot.latitude, depot.longitude, coordinates)
    
    # Get distance/duration matrix from OSRM
    try:
        osrm_table = osrm_client.table(coordinate_list)
    except Exception as e:
        import logging
        logging.error(f"OSRM table request failed: {e}")
        raise ValueError(f"Failed to get routing data from OSRM service: {str(e)}. Please ensure OSRM is running and accessible.") from e

    constraints = _build_constraints(payload)
    routing_result = solve_vrp(
        zone_id=payload.zone_id,
        customers=filtered_customers,
        osrm_table=osrm_table,
        constraints=constraints,
    )

    metadata = routing_result.metadata
    metadata.setdefault("status", metadata.get("status", "complete"))
    metadata.setdefault("zone_id", payload.zone_id)
    metadata.setdefault("city", payload.city)
    if payload.run_label:
        metadata["run_label"] = payload.run_label
    if payload.requested_by:
        metadata["author"] = payload.requested_by
    if payload.notes:
        metadata["notes"] = payload.notes
    incoming_tags = payload.tags or []
    if incoming_tags or "tags" in metadata:
        existing_tags = list(metadata.get("tags") or [])
        merged_tags: list[str] = []
        for tag in [*existing_tags, *incoming_tags]:
            normalized = tag.strip()
            if normalized and normalized not in merged_tags:
                merged_tags.append(normalized)
        metadata["tags"] = merged_tags

    route_overlays = _build_route_overlays(depot_lat=depot.latitude, depot_lon=depot.longitude, plans=routing_result.plans, customers=filtered_customers)
    if route_overlays:
        metadata.setdefault("map_overlays", {})
        metadata["map_overlays"]["routes"] = route_overlays

    response = RoutingResponse(
        zone_id=routing_result.zone_id,
        metadata=routing_result.metadata,
        plans=[
            RoutePlanModel(
                route_id=plan.route_id,
                day=plan.day,
                total_distance_km=plan.total_distance_km,
                total_duration_min=plan.total_duration_min,
                customer_count=plan.customer_count,
                constraint_violations=plan.constraint_violations,
                stops=[RouteStopModel(**asdict(stop)) for stop in plan.stops],
            )
            for plan in routing_result.plans
        ],
    )

    if payload.persist:
        storage = FileStorage()
        run_dir = storage.make_run_directory(prefix=f"routes_{payload.zone_id}")
        storage.write_json(run_dir / "summary.json", routing_result_to_json(routing_result))
        storage.write_csv(run_dir / "assignments.csv", routing_result_to_csv(routing_result))

        # Export to EasyTerritory GeoJSON format
        try:
            easyterritory_features = export_routes_to_easyterritory(
                routes_response=response.model_dump(),
                city=payload.city,
                zone=payload.zone_id,
            )
            save_easyterritory_json(easyterritory_features, run_dir / "routes.geojson")
        except Exception as exc:
            # Log error but don't fail the entire request
            import logging
            logging.warning(f"Failed to generate GeoJSON export: {exc}")

    return response


def _build_route_overlays(
    *,
    depot_lat: float,
    depot_lon: float,
    plans: Sequence[RoutePlan],
    customers: Sequence[Customer],
) -> list[dict]:
    if not plans:
        return []
    customer_lookup = {customer.customer_id: customer for customer in customers}
    overlays: list[dict] = []
    for plan in plans:
        coordinates: list[list[float]] = [[depot_lat, depot_lon]]
        for stop in plan.stops:
            customer = customer_lookup.get(stop.customer_id)
            if not customer:
                continue
            coordinates.append([customer.latitude, customer.longitude])
        # close the loop back to depot for display purposes
        coordinates.append([depot_lat, depot_lon])
        overlays.append(
            {
                "route_id": plan.route_id,
                "coordinates": coordinates,
                "source": "sequence",
            }
        )
    return overlays
