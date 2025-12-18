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
from .sequence_solver import solve_sequence_only


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
    
    # Check if manual route assignments are provided
    if payload.route_assignments:
        # Manual assignment mode: only optimize sequence
        return _optimize_sequences_only(payload, depot, filtered_customers)

    coordinates = [(customer.latitude, customer.longitude) for customer in filtered_customers]
    
    # Initialize OSRM client with error handling
    try:
        osrm_client = OSRMClient()
    except ValueError as e:
        import logging
        logging.error(f"OSRM client initialization failed: {e}")
        raise ValueError(f"OSRM service is not configured. Please check OSRM_BASE_URL setting.") from e
    
    coordinate_list = build_coordinate_list(depot.latitude, depot.longitude, coordinates)
    
    # Get distance/duration matrix from OSRM with fallback to haversine
    osrm_table = None
    use_haversine_fallback = False
    
    try:
        osrm_table = osrm_client.table(coordinate_list)
        
        # Check if we got too many None values (unreachable routes)
        # If more than 50% of depot-to-customer routes are None, use fallback
        if osrm_table and "durations" in osrm_table and "distances" in osrm_table:
            durations = osrm_table["durations"]
            distances = osrm_table["distances"]
            
            if durations and len(durations) > 0:
                depot_row = durations[0] if len(durations) > 0 else []
                # Count None values in depot-to-customer routes (skip depot itself at index 0)
                unreachable_count = sum(1 for i in range(1, len(depot_row)) if depot_row[i] is None)
                total_customers = len(depot_row) - 1  # Exclude depot
                
                if total_customers > 0:
                    unreachable_rate = unreachable_count / total_customers
                    if unreachable_rate > 0.5:  # More than 50% unreachable
                        logging.warning(
                            f"Too many unreachable routes from OSRM ({unreachable_count}/{total_customers}, "
                            f"{unreachable_rate*100:.1f}%). Using haversine fallback."
                        )
                        use_haversine_fallback = True
                        osrm_table = None
    except (ConnectionError, ValueError) as e:
        import logging
        logging.warning(f"OSRM table request failed: {e}. Using haversine fallback.")
        use_haversine_fallback = True
    except Exception as e:
        import logging
        logging.error(f"Unexpected error getting OSRM table: {e}. Attempting haversine fallback.")
        use_haversine_fallback = True
    
    # Fallback to haversine distance if OSRM failed or returned too many None values
    if use_haversine_fallback or osrm_table is None:
        import logging
        from ...services.geospatial import haversine_km
        
        logging.info(f"Computing distance/duration matrix using haversine fallback for {len(filtered_customers)} customers")
        
        # Build matrix using haversine distance
        # Note: coordinate_list format is (lat, lon) from build_coordinate_list
        n = len(coordinate_list)  # depot + customers
        durations: list[list[float | None]] = [[None] * n for _ in range(n)]
        distances: list[list[float | None]] = [[None] * n for _ in range(n)]
        
        # Average speed for duration estimation (km/h)
        AVERAGE_SPEED_KMH = 40.0
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    durations[i][j] = 0.0
                    distances[i][j] = 0.0
                else:
                    # coordinate_list uses (lat, lon) format
                    lat1, lon1 = coordinate_list[i]
                    lat2, lon2 = coordinate_list[j]
                    distance_km = haversine_km(lat1, lon1, lat2, lon2)
                    duration_minutes = (distance_km / AVERAGE_SPEED_KMH) * 60.0
                    
                    distances[i][j] = distance_km * 1000.0  # Convert to meters for consistency
                    durations[i][j] = duration_minutes * 60.0  # Convert to seconds for consistency
        
        osrm_table = {
            "durations": durations,
            "distances": distances,
        }
        logging.info("Haversine fallback matrix computed successfully")

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

    # Check if we have any routes
    if not routing_result.plans:
        import logging
        status = routing_result.metadata.get("status", "unknown")
        if status == "infeasible":
            reason = routing_result.metadata.get("reason", "Constraints may be too strict.")
            raise ValueError(
                f"No routes generated: {reason} "
                f"Try relaxing constraints (max customers, duration, or distance)."
            )
        else:
            raise ValueError(
                "No routes were generated. This may indicate an issue with the solver or constraints."
            )
    
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
        # Save to database first
        try:
            from ...persistence.database import save_routes_to_database
            save_routes_to_database(
                routes_response=response.model_dump(),
                zone_id=payload.zone_id,
                city=payload.city,
            )
        except Exception as exc:
            # Log error but don't fail the entire request
            import logging
            logging.warning(f"Failed to save routes to database: {exc}")
        
        # Also save to files (backup)
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


def _optimize_sequences_only(
    payload: RoutingRequest,
    depot: Depot,
    all_customers: list[Customer],
) -> RoutingResponse:
    """Optimize sequences for manually assigned routes.
    
    This function handles the case where customers are pre-assigned to routes.
    It only optimizes the visit sequence within each route using OR-Tools + OSRM.
    """
    import logging
    
    # Build customer lookup
    customer_lookup = {c.customer_id: c for c in all_customers}
    
    # Validate route assignments and collect all assigned customers
    route_assignments_dict: dict[str, tuple[str, list[Customer]]] = {}
    assigned_customer_ids = set()
    
    for assignment in payload.route_assignments:
        route_customers = []
        for customer_id in assignment.customer_ids:
            if customer_id not in customer_lookup:
                logging.warning(f"Customer {customer_id} not found in zone, skipping")
                continue
            if customer_id in assigned_customer_ids:
                logging.warning(f"Customer {customer_id} assigned to multiple routes, using first assignment")
                continue
            route_customers.append(customer_lookup[customer_id])
            assigned_customer_ids.add(customer_id)
        
        if route_customers:
            route_assignments_dict[assignment.route_id] = (assignment.day, route_customers)
    
    if not route_assignments_dict:
        raise ValueError("No valid route assignments provided. Ensure customers exist in the zone.")
    
    # Get OSRM matrix for all customers (depot + all assigned customers)
    coordinates = [(customer.latitude, customer.longitude) for customer in all_customers]
    coordinate_list = build_coordinate_list(depot.latitude, depot.longitude, coordinates)
    
    # Build customer_id -> matrix_index mapping
    # Index 0 = depot, indices 1+ = customers in order
    customer_to_index: dict[str, int] = {}
    for idx, customer in enumerate(all_customers, start=1):
        customer_to_index[customer.customer_id] = idx
    
    # Get OSRM matrix
    try:
        osrm_client = OSRMClient()
        osrm_table = osrm_client.table(coordinate_list)
    except Exception as e:
        import logging
        logging.warning(f"OSRM request failed: {e}. Using haversine fallback.")
        # Fallback to haversine
        from ...services.geospatial import haversine_km
        n = len(coordinate_list)
        durations: list[list[float | None]] = [[None] * n for _ in range(n)]
        distances: list[list[float | None]] = [[None] * n for _ in range(n)]
        AVERAGE_SPEED_KMH = 40.0
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    durations[i][j] = 0.0
                    distances[i][j] = 0.0
                else:
                    lat1, lon1 = coordinate_list[i]
                    lat2, lon2 = coordinate_list[j]
                    distance_km = haversine_km(lat1, lon1, lat2, lon2)
                    duration_minutes = (distance_km / AVERAGE_SPEED_KMH) * 60.0
                    distances[i][j] = distance_km * 1000.0
                    durations[i][j] = duration_minutes * 60.0
        
        osrm_table = {"durations": durations, "distances": distances}
    
    # Solve sequence for each route
    routing_result = solve_sequence_only(
        zone_id=payload.zone_id,
        route_assignments=route_assignments_dict,
        customer_to_index=customer_to_index,
        osrm_table=osrm_table,
    )
    
    # Build response (same as automatic mode)
    metadata = routing_result.metadata
    metadata.setdefault("zone_id", payload.zone_id)
    metadata.setdefault("city", payload.city)
    metadata["optimization_mode"] = "sequence_only"
    metadata["description"] = "Sequences optimized using OR-Tools with OSRM distance matrix"
    
    if payload.run_label:
        metadata["run_label"] = payload.run_label
    if payload.requested_by:
        metadata["author"] = payload.requested_by
    if payload.notes:
        metadata["notes"] = payload.notes
    
    route_overlays = _build_route_overlays(
        depot_lat=depot.latitude,
        depot_lon=depot.longitude,
        plans=routing_result.plans,
        customers=all_customers
    )
    if route_overlays:
        metadata.setdefault("map_overlays", {})
        metadata["map_overlays"]["routes"] = route_overlays
    
    response = RoutingResponse(
        zone_id=routing_result.zone_id,
        metadata=metadata,
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
        try:
            from ...persistence.database import save_routes_to_database
            save_routes_to_database(
                routes_response=response.model_dump(),
                zone_id=payload.zone_id,
                city=payload.city,
            )
        except Exception as exc:
            import logging
            logging.warning(f"Failed to save routes to database: {exc}")
        
        storage = FileStorage()
        run_dir = storage.make_run_directory(prefix=f"routes_{payload.zone_id}")
        from ..outputs.routing_formatter import routing_result_to_json, routing_result_to_csv
        storage.write_json(run_dir / "summary.json", routing_result_to_json(routing_result))
        storage.write_csv(run_dir / "assignments.csv", routing_result_to_csv(routing_result))
    
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
