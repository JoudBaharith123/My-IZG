"""Routing orchestration service."""

from __future__ import annotations

from dataclasses import asdict
from typing import Sequence

from ...data.customers_repository import get_customers_for_location, resolve_depot
from ...models.domain import Customer, Depot
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
    start_from_depot = payload.start_from_depot if payload.start_from_depot is not None else True
    routing_result = solve_vrp(
        zone_id=payload.zone_id,
        customers=filtered_customers,
        osrm_table=osrm_table,
        constraints=constraints,
        start_from_depot=start_from_depot,
    )

    metadata = routing_result.metadata
    metadata.setdefault("status", metadata.get("status", "complete"))
    metadata.setdefault("zone_id", payload.zone_id)
    metadata.setdefault("city", payload.city)
    metadata["start_from_depot"] = start_from_depot  # Save for later retrieval
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

    route_overlays = _build_route_overlays(
        depot_lat=depot.latitude,
        depot_lon=depot.longitude,
        plans=routing_result.plans,
        customers=filtered_customers,
        start_from_depot=start_from_depot,
    )
    if route_overlays:
        metadata.setdefault("map_overlays", {})
        metadata["map_overlays"]["routes"] = route_overlays
        # Log summary of route overlays
        import logging
        logging.info(f"=== Route Overlays Summary ===")
        logging.info(f"start_from_depot={start_from_depot}, num_routes={len(route_overlays)}")
        for overlay in route_overlays:
            route_id = overlay.get("route_id", "unknown")
            coords = overlay.get("coordinates", [])
            source = overlay.get("source", "unknown")
            if coords:
                first_coord = coords[0]
                logging.info(f"  Route {route_id}: {len(coords)} coordinates, source={source}, first_coord=({first_coord[0]:.6f}, {first_coord[1]:.6f})")

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

    # Always save routes to database (regardless of persist flag)
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
        import traceback
        logging.error(f"CRITICAL: Failed to save routes to database: {exc}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        # Don't re-raise - routes are still valid and should be returned to user
        # Database save failure should not prevent route generation from succeeding
    
    if payload.persist:
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
    
    start_from_depot = payload.start_from_depot if payload.start_from_depot is not None else True
    metadata["start_from_depot"] = start_from_depot  # Save for later retrieval
    
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
        customers=all_customers,
        start_from_depot=start_from_depot,
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
    
    # Always save routes to database (regardless of persist flag)
    try:
        from ...persistence.database import save_routes_to_database
        save_routes_to_database(
            routes_response=response.model_dump(),
            zone_id=payload.zone_id,
            city=payload.city,
        )
    except Exception as exc:
        # Log error but don't fail the entire request - routes should still be returned
        import logging
        import traceback
        logging.error(f"CRITICAL: Failed to save routes to database: {exc}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        # Don't re-raise - routes are still valid and should be returned to user
        # Database save failure should not prevent route generation from succeeding
    
    if payload.persist:
        # Also save to files (backup)
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
    start_from_depot: bool = True,
) -> list[dict]:
    """Build route overlays with street-level geometry from OSRM.
    
    Uses OSRM route endpoint to get actual street paths between stops,
    preventing routes from crossing water or other impassable areas.
    Falls back to straight-line paths if OSRM is unavailable.
    """
    import logging
    
    if not plans:
        return []
    
    customer_lookup = {customer.customer_id: customer for customer in customers}
    overlays: list[dict] = []
    
    # Try to initialize OSRM client for street-level routing
    osrm_client = None
    try:
        osrm_client = OSRMClient()
    except (ValueError, ConnectionError) as e:
        logging.warning(f"OSRM not available for route geometry: {e}. Using straight-line paths.")
    
    for plan in plans:
        # Build waypoints for this route
        # CRITICAL: When start_from_depot=False, waypoints must ONLY contain customer coordinates
        # Do NOT use build_coordinate_list here - it always includes depot
        # We build waypoints directly to control whether depot is included
        import logging
        logging.info(f"=== Building route overlay for {plan.route_id} ===")
        logging.info(f"  Route has {len(plan.stops)} stops: {[s.customer_id for s in plan.stops]}")
        if plan.stops:
            logging.info(f"  First customer: {plan.stops[0].customer_id}, Last customer: {plan.stops[-1].customer_id}")
        
        waypoints: list[tuple[float, float]] = []
        
        if start_from_depot:
            # Start from depot: depot -> stop1 -> stop2 -> ... -> depot
            waypoints.append((depot_lat, depot_lon))
        
        # Add customer coordinates in sequence order (NEVER use build_coordinate_list for route waypoints)
        for stop in plan.stops:
            customer = customer_lookup.get(stop.customer_id)
            if not customer:
                logging.warning(f"Customer {stop.customer_id} not found in lookup, skipping")
                continue
            # Validate coordinates before adding
            if not (-90 <= customer.latitude <= 90) or not (-180 <= customer.longitude <= 180):
                logging.error(f"❌ Invalid coordinates for customer {stop.customer_id}: ({customer.latitude}, {customer.longitude})")
                continue
            if abs(customer.latitude) < 1e-6 and abs(customer.longitude) < 1e-6:
                logging.error(f"❌ Zero/Invalid coordinates for customer {stop.customer_id}: ({customer.latitude}, {customer.longitude})")
                continue
            waypoints.append((customer.latitude, customer.longitude))
        
        if start_from_depot:
            # Close the loop back to depot
            waypoints.append((depot_lat, depot_lon))
        
        # Verification: When start_from_depot=False, waypoints must NOT include depot
        # OSRM routes between the waypoints we provide, so excluding depot ensures route starts from first customer
        if not start_from_depot:
            # Verify no depot coordinates are in waypoints
            for wp in waypoints:
                if abs(wp[0] - depot_lat) < 0.0001 and abs(wp[1] - depot_lon) < 0.0001:
                    import logging
                    logging.error(f"ERROR: Depot found in waypoints when start_from_depot=False! This should never happen.")
                    # Remove depot coordinate if accidentally included
                    waypoints = [wp for wp in waypoints if not (abs(wp[0] - depot_lat) < 0.0001 and abs(wp[1] - depot_lon) < 0.0001)]
                    break
        
        # If we have OSRM, get street-level route geometry
        if osrm_client and len(waypoints) >= 2:
            try:
                # CRITICAL VERIFICATION: Log exact waypoints before calling OSRM
                import logging
                logging.info(f"=== Route {plan.route_id} OSRM route() call ===")
                logging.info(f"start_from_depot={start_from_depot}, num_waypoints={len(waypoints)}")
                if waypoints:
                    first_wp = waypoints[0]
                    last_wp = waypoints[-1]
                    # Calculate distance from depot to first waypoint
                    from ...services.geospatial import haversine_km
                    first_to_depot_dist = haversine_km(depot_lat, depot_lon, first_wp[0], first_wp[1])
                    last_to_depot_dist = haversine_km(depot_lat, depot_lon, last_wp[0], last_wp[1])
                    
                    logging.info(f"First waypoint: ({first_wp[0]:.6f}, {first_wp[1]:.6f}), distance from depot: {first_to_depot_dist:.3f} km")
                    logging.info(f"Last waypoint: ({last_wp[0]:.6f}, {last_wp[1]:.6f}), distance from depot: {last_to_depot_dist:.3f} km")
                    
                    if not start_from_depot:
                        # Verify first waypoint is NOT depot
                        if first_to_depot_dist < 0.1:  # Within 100m of depot
                            logging.error(f"❌ ERROR: First waypoint is at depot ({first_to_depot_dist:.3f} km away) when start_from_depot=False!")
                            logging.error(f"   This will cause OSRM to return route starting from depot instead of first customer!")
                        else:
                            logging.info(f"✓ First waypoint is a customer ({first_to_depot_dist:.3f} km from depot) - correct!")
                        
                        # Verify last waypoint is NOT depot
                        if last_to_depot_dist < 0.1:
                            logging.error(f"❌ ERROR: Last waypoint is at depot ({last_to_depot_dist:.3f} km away) when start_from_depot=False!")
                        else:
                            logging.info(f"✓ Last waypoint is a customer ({last_to_depot_dist:.3f} km from depot) - correct!")
                    
                    # Log all waypoints for debugging
                    logging.debug(f"All waypoints: {[(lat, lon) for lat, lon in waypoints]}")
                
                # Get route geometry from OSRM
                route_data = osrm_client.route(waypoints)
                
                # Extract geometry from OSRM response
                if route_data.get("routes") and len(route_data["routes"]) > 0:
                    route = route_data["routes"][0]
                    geometry_encoded = route.get("geometry")
                    
                    if geometry_encoded:
                        # Decode polyline to get coordinates
                        from .osrm_client import decode_polyline
                        decoded_coords = decode_polyline(geometry_encoded)
                        
                        # Convert to [lat, lon] format for frontend
                        coordinates = [[lat, lon] for lat, lon in decoded_coords]
                        
                        # CRITICAL FIX: When start_from_depot=False, ensure route starts from first customer
                        # and remove any coordinates that are too close to depot
                        if not start_from_depot and plan.stops and len(coordinates) > 0:
                            first_stop = plan.stops[0]
                            first_customer = customer_lookup.get(first_stop.customer_id)
                            last_stop = plan.stops[-1] if len(plan.stops) > 0 else None
                            last_customer = customer_lookup.get(last_stop.customer_id) if last_stop else None
                            
                            if first_customer:
                                first_customer_coord = [first_customer.latitude, first_customer.longitude]
                                
                                # Remove any coordinates at the beginning that are too close to depot
                                # OSRM might include depot coordinates even if we didn't include depot in waypoints
                                DEPOT_PROXIMITY_THRESHOLD_KM = 0.5  # 500 meters
                                filtered_coords = []
                                found_first_customer = False
                                
                                for coord in coordinates:
                                    lat, lon = coord[0], coord[1]
                                    # Skip invalid coordinates
                                    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                                        continue
                                    
                                    # Calculate distance from depot
                                    dist_from_depot = haversine_km(depot_lat, depot_lon, lat, lon)
                                    # Calculate distance from first customer
                                    dist_from_first = haversine_km(first_customer.latitude, first_customer.longitude, lat, lon)
                                    
                                    # If we haven't found the first customer yet, skip coordinates too close to depot
                                    if not found_first_customer:
                                        if dist_from_depot < DEPOT_PROXIMITY_THRESHOLD_KM:
                                            # This coordinate is too close to depot, skip it
                                            logging.debug(f"  Skipping coord ({lat:.6f}, {lon:.6f}) - too close to depot ({dist_from_depot:.3f} km)")
                                            continue
                                        elif dist_from_first < 0.1:  # Within 100m of first customer
                                            # Found first customer! Start including coordinates from here
                                            found_first_customer = True
                                            filtered_coords.append(first_customer_coord)  # Use exact first customer location
                                            logging.info(f"✓ Found first customer {first_stop.customer_id} at coord ({lat:.6f}, {lon:.6f}), distance from depot: {dist_from_depot:.3f} km")
                                        else:
                                            # This coordinate is far from depot and not the first customer
                                            # It might be part of the route, but we want to start from first customer
                                            # So we'll skip it and wait for first customer
                                            continue
                                    else:
                                        # We've already found the first customer, include all remaining coordinates
                                        filtered_coords.append(coord)
                                
                                # If we didn't find first customer in the coordinates, force it at the beginning
                                if not found_first_customer:
                                    logging.warning(f"⚠ First customer {first_stop.customer_id} not found in OSRM coordinates, forcing it at start")
                                    filtered_coords = [first_customer_coord] + filtered_coords
                                else:
                                    # Ensure first coordinate is exactly first customer location
                                    filtered_coords[0] = first_customer_coord
                                
                                coordinates = filtered_coords
                                logging.info(f"✓✓ Route {plan.route_id}: Filtered to {len(coordinates)} coords starting from customer {first_stop.customer_id}")
                            
                            # Ensure last coordinate is exactly last customer location
                            if last_customer and len(coordinates) > 0:
                                last_customer_lat = last_customer.latitude
                                last_customer_lon = last_customer.longitude
                                
                                # Validate last customer coordinates
                                if not (-90 <= last_customer_lat <= 90) or not (-180 <= last_customer_lon <= 180):
                                    logging.error(f"❌ Invalid last customer coordinates for {last_stop.customer_id}: ({last_customer_lat}, {last_customer_lon})")
                                else:
                                    # Find coordinate closest to last customer (search from end backwards)
                                    min_dist = float('inf')
                                    end_idx = len(coordinates) - 1
                                    
                                    for idx in range(len(coordinates) - 1, -1, -1):
                                        lat, lon = coordinates[idx][0], coordinates[idx][1]
                                        # Skip invalid coordinates
                                        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                                            continue
                                        dist = haversine_km(last_customer_lat, last_customer_lon, lat, lon)
                                        if dist < min_dist:
                                            min_dist = dist
                                            end_idx = idx
                                    
                                    logging.info(f"  Closest coordinate to last customer {last_stop.customer_id} at index {end_idx}, distance={min_dist:.3f} km")
                                
                                    # Trim to end at last customer (keep coordinates up to and including end_idx)
                                    if end_idx < len(coordinates) - 1:
                                        coordinates = coordinates[:end_idx + 1]
                                        logging.info(f"  Trimmed coordinates from end, keeping first {len(coordinates)} coordinates")
                                    
                                    # Force last coordinate to be EXACTLY last customer location
                                    if coordinates:
                                        coordinates[-1] = [last_customer_lat, last_customer_lon]
                                        logging.info(f"✓ Last coord forced to customer {last_stop.customer_id}: ({coordinates[-1][0]:.6f}, {coordinates[-1][1]:.6f})")
                                    else:
                                        logging.error(f"❌ ERROR: No coordinates to set last coordinate for {last_stop.customer_id}!")
                        
                        # Final verification: log first and last coordinates before adding to overlays
                        if coordinates and plan.stops:
                            first_final = coordinates[0]
                            last_final = coordinates[-1]
                            final_depot_dist_first = haversine_km(depot_lat, depot_lon, first_final[0], first_final[1])
                            final_depot_dist_last = haversine_km(depot_lat, depot_lon, last_final[0], last_final[1])
                            
                            # Get first and last customer IDs for verification
                            first_stop_id = plan.stops[0].customer_id
                            last_stop_id = plan.stops[-1].customer_id
                            first_cust = customer_lookup.get(first_stop_id)
                            last_cust = customer_lookup.get(last_stop_id)
                            
                            if first_cust:
                                first_cust_dist = haversine_km(first_cust.latitude, first_cust.longitude, first_final[0], first_final[1])
                                logging.info(f"✓✓ Route {plan.route_id} FINAL: {len(coordinates)} coords")
                                logging.info(f"  First customer: {first_stop_id} at ({first_cust.latitude:.6f}, {first_cust.longitude:.6f})")
                                logging.info(f"  First coord: ({first_final[0]:.6f}, {first_final[1]:.6f}), distance from first customer={first_cust_dist:.3f} km, from depot={final_depot_dist_first:.3f} km")
                            
                            if last_cust:
                                last_cust_dist = haversine_km(last_cust.latitude, last_cust.longitude, last_final[0], last_final[1])
                                logging.info(f"  Last customer: {last_stop_id} at ({last_cust.latitude:.6f}, {last_cust.longitude:.6f})")
                                logging.info(f"  Last coord: ({last_final[0]:.6f}, {last_final[1]:.6f}), distance from last customer={last_cust_dist:.3f} km, from depot={final_depot_dist_last:.3f} km")
                            
                            # Verify coordinates are correct
                            if not start_from_depot and first_cust:
                                first_cust_dist_check = haversine_km(first_cust.latitude, first_cust.longitude, first_final[0], first_final[1])
                                if first_cust_dist_check > 0.05:  # More than 50m away
                                    logging.error(f"❌ ERROR: First coordinate is {first_cust_dist_check:.3f} km away from first customer {first_stop_id}!")
                                
                                if final_depot_dist_first < 0.5:  # Less than 500m from depot
                                    logging.error(f"❌ ERROR: First coordinate is {final_depot_dist_first:.3f} km from depot! Route should start from customer, not depot!")
                            
                            if last_cust:
                                last_cust_dist_check = haversine_km(last_cust.latitude, last_cust.longitude, last_final[0], last_final[1])
                                if last_cust_dist_check > 0.05:  # More than 50m away
                                    logging.error(f"❌ ERROR: Last coordinate is {last_cust_dist_check:.3f} km away from last customer {last_stop_id}!")
                        
                        # Create completely fresh copy of coordinates for this route (deep copy to avoid any sharing)
                        route_coordinates = [[float(c[0]), float(c[1])] for c in coordinates]
                        
                        # FINAL VERIFICATION: When start_from_depot=False, ensure first coordinate is first customer
                        if not start_from_depot and plan.stops and route_coordinates:
                            first_stop_final = plan.stops[0]
                            first_cust_final = customer_lookup.get(first_stop_final.customer_id)
                            if first_cust_final:
                                # ABSOLUTE FINAL CHECK - replace first coordinate with first customer
                                route_coordinates[0] = [float(first_cust_final.latitude), float(first_cust_final.longitude)]
                                logging.info(f"✓✓✓ Route {plan.route_id} ABSOLUTE FINAL: First coord = ({route_coordinates[0][0]:.6f}, {route_coordinates[0][1]:.6f}) = customer {first_stop_final.customer_id}")
                        
                        overlays.append(
                            {
                                "route_id": plan.route_id,
                                "coordinates": route_coordinates,  # Fresh list - each route has unique coordinates
                                "source": "osrm",
                            }
                        )
                        continue
            except Exception as e:
                logging.warning(f"Failed to get OSRM route geometry for {plan.route_id}: {e}. Using straight-line path.")
        
        # Fallback: use straight-line path (original behavior)
        coordinates: list[list[float]] = [[lat, lon] for lat, lon in waypoints]
        
        # If not starting from depot, ensure first coordinate is exactly first customer and last is exactly last customer
        if not start_from_depot and plan.stops and coordinates:
            first_stop = plan.stops[0]
            first_customer = customer_lookup.get(first_stop.customer_id)
            if first_customer:
                # Force first coordinate to be exactly first customer location
                coordinates[0] = [first_customer.latitude, first_customer.longitude]
                logging.info(f"✓ Fallback: Route {plan.route_id} first coord set to first customer {first_stop.customer_id}: ({coordinates[0][0]:.6f}, {coordinates[0][1]:.6f})")
            
            # Also ensure last coordinate is exactly last customer
            if len(plan.stops) > 0:
                last_stop = plan.stops[-1]
                last_customer = customer_lookup.get(last_stop.customer_id)
                if last_customer and coordinates:
                    coordinates[-1] = [last_customer.latitude, last_customer.longitude]
                    logging.info(f"✓ Fallback: Route {plan.route_id} last coord set to last customer {last_stop.customer_id}: ({coordinates[-1][0]:.6f}, {coordinates[-1][1]:.6f})")
        
        # CRITICAL: Make a copy of coordinates to ensure each route has unique coordinates (no shared references)
        final_coordinates_fallback = [coord[:] for coord in coordinates]
        
        overlays.append(
            {
                "route_id": plan.route_id,
                "coordinates": final_coordinates_fallback,  # Use copied coordinates - ensure unique per route
                "source": "sequence",
            }
        )
    
    return overlays
