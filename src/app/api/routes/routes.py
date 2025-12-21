"""Routing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from ...schemas.routing import RoutePlanModel, RouteStopModel, RoutingRequest, RoutingResponse
from ...services.routing.service import optimize_routes
from ...persistence.database import delete_all_routes_from_database, get_routes_from_database, update_route_customer, remove_customer_from_route

router = APIRouter(prefix="/routes", tags=["routes"])


class RemoveCustomerRequest(BaseModel):
    zone_id: str
    route_id: str
    customer_id: str


class TransferCustomerRequest(BaseModel):
    zone_id: str
    from_route_id: str
    to_route_id: str
    customer_id: str


@router.post("/optimize", response_model=RoutingResponse, status_code=status.HTTP_200_OK)
def optimize(payload: RoutingRequest) -> RoutingResponse:
    try:
        return optimize_routes(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        # Log the full error for debugging
        import logging
        logging.exception(f"Error optimizing routes: {exc}")
        # Return a user-friendly error message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize routes: {str(exc)}"
        ) from exc


@router.post("/remove-customer", status_code=status.HTTP_200_OK)
def remove_customer(payload: RemoveCustomerRequest) -> dict:
    """Remove a customer from a route."""
    try:
        success = remove_customer_from_route(
            zone_id=payload.zone_id,
            route_id=payload.route_id,
            customer_id=payload.customer_id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer {payload.customer_id} not found in route {payload.route_id}"
            )
        return {
            "success": True,
            "message": f"Customer {payload.customer_id} removed from route {payload.route_id}"
        }
    except HTTPException:
        raise
    except Exception as exc:
        import logging
        logging.exception(f"Error removing customer from route: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove customer from route: {str(exc)}"
        ) from exc


@router.post("/transfer-customer", status_code=status.HTTP_200_OK)
def transfer_customer(payload: TransferCustomerRequest) -> dict:
    """Transfer a customer from one route to another."""
    try:
        success = update_route_customer(
            zone_id=payload.zone_id,
            from_route_id=payload.from_route_id,
            to_route_id=payload.to_route_id,
            customer_id=payload.customer_id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed to transfer customer {payload.customer_id} from {payload.from_route_id} to {payload.to_route_id}"
            )
        return {
            "success": True,
            "message": f"Customer {payload.customer_id} transferred from {payload.from_route_id} to {payload.to_route_id}"
        }
    except HTTPException:
        raise
    except Exception as exc:
        import logging
        logging.exception(f"Error transferring customer: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transfer customer: {str(exc)}"
        ) from exc


@router.get("/from-database", response_model=RoutingResponse, status_code=status.HTTP_200_OK)
def get_routes(
    zone_id: str | None = Query(default=None, description="Filter routes by zone ID"),
    city: str | None = Query(default=None, description="Filter routes by city"),
) -> RoutingResponse:
    """Retrieve routes from database and convert to frontend format.
    
    Returns routes in the same format as optimize response so they can
    be displayed on the map and in the routing workspace.
    """
    try:
        # Get routes from database
        db_routes = get_routes_from_database(zone_id=zone_id, city=city)
        
        if not db_routes:
            # Return empty response
            if not zone_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="zone_id is required to retrieve routes"
                )
            return RoutingResponse(
                zone_id=zone_id,
                metadata={
                    "status": "empty",
                    "source": "database",
                    "message": f"No routes found for zone '{zone_id}'"
                },
                plans=[],
            )
        
        # Group routes by zone (in case multiple zones were returned)
        # Use the first route's zone info as the zone_id
        first_route = db_routes[0]
        zone_info = first_route.get("zone_info", {})
        if isinstance(zone_info, dict):
            zone_name = zone_info.get("name", zone_id or "unknown")
        else:
            zone_name = zone_id or "unknown"
        
        # Convert database routes to RoutePlanModel format
        plans = []
        for route in db_routes:
            try:
                stops_data = route.get("stops", [])
                if not stops_data:
                    continue
                
                stops = [
                    RouteStopModel(
                        customer_id=stop.get("customer_id", ""),
                        sequence=stop.get("sequence", 0),
                        arrival_min=float(stop.get("arrival_min", 0.0)) if stop.get("arrival_min") is not None else 0.0,
                        distance_from_prev_km=float(stop.get("distance_from_prev_km", 0.0)) if stop.get("distance_from_prev_km") is not None else 0.0,
                    )
                    for stop in stops_data
                ]
                
                # Get route metadata
                vehicle_id = route.get("vehicle_id", "")
                total_distance_km = float(route.get("total_distance_km", 0.0)) if route.get("total_distance_km") is not None else 0.0
                total_duration_min = float(route.get("total_duration_min", 0.0)) if route.get("total_duration_min") is not None else 0.0
                
                plan = RoutePlanModel(
                    route_id=vehicle_id,
                    day="",  # Day is not stored in routes table, can be empty
                    total_distance_km=total_distance_km,
                    total_duration_min=total_duration_min,
                    customer_count=len(stops),
                    constraint_violations={},  # Not stored in database
                    stops=stops,
                )
                plans.append(plan)
            except Exception as e:
                import logging
                logging.warning(f"Error converting route {route.get('vehicle_id', 'unknown')} to RoutePlanModel: {e}")
                continue
        
        # Get zone metadata if available
        zone_metadata = {}
        if isinstance(zone_info, dict):
            zone_metadata = zone_info.get("metadata", {})
        
        # Get city from metadata
        resolved_city = city
        if isinstance(zone_metadata, dict) and "city" in zone_metadata:
            resolved_city = zone_metadata["city"]
        
        # Get depot and customers for route overlays
        route_overlays = []
        try:
            from ...data.customers_repository import resolve_depot
            from ...persistence.database import get_customers_for_zone
            from ...services.routing.service import _build_route_overlays
            from ...services.routing.models import RoutePlan, RouteStop
            
            depot = resolve_depot(resolved_city or "Jeddah")  # Fallback to Jeddah if city not found
            if depot:
                customers = get_customers_for_zone(zone_name)
                
                # Convert RoutePlanModel to RoutePlan domain model for _build_route_overlays
                route_plans_domain = []
                for plan in plans:
                    route_stops = [
                        RouteStop(
                            customer_id=stop.customer_id,
                            sequence=stop.sequence,
                            arrival_min=stop.arrival_min,
                            distance_from_prev_km=stop.distance_from_prev_km,
                        )
                        for stop in plan.stops
                    ]
                    
                    route_plan_domain = RoutePlan(
                        route_id=plan.route_id,
                        day=plan.day,
                        total_distance_km=plan.total_distance_km,
                        total_duration_min=plan.total_duration_min,
                        customer_count=plan.customer_count,
                        constraint_violations=plan.constraint_violations,
                        stops=route_stops,
                    )
                    route_plans_domain.append(route_plan_domain)
                
                # Try to get start_from_depot from metadata (default to True for backward compatibility)
                start_from_depot = True
                if isinstance(zone_metadata, dict) and "start_from_depot" in zone_metadata:
                    start_from_depot = bool(zone_metadata.get("start_from_depot", True))
                
                route_overlays = _build_route_overlays(
                    depot_lat=depot.latitude,
                    depot_lon=depot.longitude,
                    plans=route_plans_domain,
                    customers=customers,
                    start_from_depot=start_from_depot,
                )
        except Exception as e:
            import logging
            logging.warning(f"Failed to build route overlays for database routes: {e}")
            route_overlays = []
        
        # Build response metadata
        metadata = {
            "status": "complete",
            "source": "database",
            "zone_id": zone_name,
            "loaded_from_db": True,
        }
        if resolved_city:
            metadata["city"] = resolved_city
        
        if route_overlays:
            metadata.setdefault("map_overlays", {})
            metadata["map_overlays"]["routes"] = route_overlays
        
        return RoutingResponse(
            zone_id=zone_name,
            metadata=metadata,
            plans=plans,
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        import logging
        logging.exception(f"Error retrieving routes from database: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve routes from database: {str(exc)}"
        ) from exc


@router.delete("/all", status_code=status.HTTP_200_OK)
def delete_all_routes() -> dict:
    """Delete all routes from the database.
    
    WARNING: This will delete ALL routes from the database.
    Use with caution.
    """
    try:
        deleted_count = delete_all_routes_from_database()
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Successfully deleted {deleted_count} route(s) from database"
        }
        
    except Exception as exc:
        import logging
        logging.exception(f"Error deleting all routes: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete routes: {str(exc)}"
        ) from exc
