"""API routes for zone generation."""

from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, HTTPException, Query, status

from ...persistence.database import (
    get_zones_from_database,
    wkt_to_coordinates,
    geojson_to_coordinates,
    update_zone_geometry,
    unassign_customer_from_zone,
    assign_customer_to_zone,
    get_unassigned_customers,
    delete_zones,
    get_customers_from_zones,
)
from ...schemas.zoning import ZoningRequest, ZoningResponse
from ...schemas.customers import ZoneSummaryModel
from ...services.zoning.service import process_zoning_request

router = APIRouter(prefix="/zones", tags=["zones"])


@router.post("/generate", response_model=ZoningResponse, status_code=status.HTTP_200_OK)
def generate_zones(
    payload: ZoningRequest,
    delete_existing_zones: list[str] | None = Query(default=None, description="Zone IDs to delete before generating new zones"),
) -> ZoningResponse:
    """Generate zones, optionally deleting existing zones first.
    
    If delete_existing_zones is provided, those zones will be deleted from the database
    before generating new zones. This is useful for regenerating specific zones.
    
    When regenerating, existing zone assignments (from other zones) are preserved.
    Only customers from the deleted zones are reassigned to new zones.
    """
    try:
        # If regenerating zones, preserve existing assignments from other zones
        existing_assignments: dict[str, str] = {}
        customers_to_regenerate: set[str] = set()
        
        if delete_existing_zones:
            import logging
            logging.info(f"Regenerating zones: {delete_existing_zones}")
            
            # Get customer IDs from zones that will be deleted
            customers_to_regenerate = set(get_customers_from_zones(delete_existing_zones))
            logging.info(f"Customers in zones to regenerate: {len(customers_to_regenerate)}")
            
            # Get existing zone assignments from database (excluding zones to be deleted)
            existing_zones = get_zones_from_database(city=payload.city, method=None)
            existing_zone_ids_preserved = set()
            for zone in existing_zones:
                zone_id = zone.get("name", "")
                if zone_id not in delete_existing_zones:  # Skip zones that will be deleted
                    existing_zone_ids_preserved.add(zone_id)
                    metadata = zone.get("metadata", {})
                    if isinstance(metadata, dict):
                        customer_ids = metadata.get("customer_ids", [])
                        if customer_ids and isinstance(customer_ids, list):
                            for customer_id in customer_ids:
                                if customer_id:
                                    existing_assignments[str(customer_id)] = zone_id
            
            logging.info(f"Preserving {len(existing_zone_ids_preserved)} existing zones: {list(existing_zone_ids_preserved)}")
            logging.info(f"Preserving assignments for {len(existing_assignments)} customers in existing zones")
            
            # Delete ONLY the specified zones
            logging.info(f"Deleting zones: {delete_existing_zones}")
            delete_zones(delete_existing_zones)
        
        # Generate new zones
        response = process_zoning_request(payload, persist=False)  # Don't persist yet, we'll merge first
        
        # If regenerating, merge assignments: keep existing for customers not in deleted zones
        new_zone_ids: set[str] = set()
        if delete_existing_zones and existing_assignments:
            merged_assignments = existing_assignments.copy()
            # Only update assignments for customers that were in deleted zones
            for customer_id, new_zone_id in response.assignments.items():
                if customer_id in customers_to_regenerate:
                    # This customer was in a deleted zone, use new assignment
                    merged_assignments[customer_id] = new_zone_id
                    new_zone_ids.add(new_zone_id)  # Track which zones are newly generated
                elif customer_id not in merged_assignments:
                    # New customer (shouldn't happen, but handle it)
                    merged_assignments[customer_id] = new_zone_id
                    new_zone_ids.add(new_zone_id)
            
            # Update response with merged assignments
            response.assignments = merged_assignments
            
            # Recalculate counts based on merged assignments
            from collections import Counter
            from ...schemas.zoning import ZoneCount
            counts_dict = Counter(merged_assignments.values())
            response.counts = [
                ZoneCount(zone_id=zone_id, customer_count=count)
                for zone_id, count in counts_dict.items()
            ]
        
        # Now persist to database
        # When regenerating, we need to save only the NEW zones (not existing ones)
        if payload.persist:
            try:
                from ...persistence.database import save_zones_to_database
                
                # If regenerating, filter to only save new zones
                if delete_existing_zones and new_zone_ids:
                    # Get list of existing zone IDs (excluding deleted ones)
                    existing_zone_ids = set(existing_assignments.values())
                    
                    # Filter response to only include newly generated zones
                    filtered_response = response.model_dump()
                    
                    # Filter assignments to only include customers in new zones
                    filtered_assignments = {
                        customer_id: zone_id
                        for customer_id, zone_id in response.assignments.items()
                        if zone_id in new_zone_ids
                    }
                    filtered_response["assignments"] = filtered_assignments
                    
                    # Filter counts to only new zones
                    filtered_counts = [
                        {"zone_id": count.zone_id, "customer_count": count.customer_count}
                        for count in response.counts
                        if count.zone_id in new_zone_ids
                    ]
                    filtered_response["counts"] = filtered_counts
                    
                    # Filter polygons to only new zones
                    if "map_overlays" in filtered_response.get("metadata", {}):
                        polygons = filtered_response["metadata"]["map_overlays"].get("polygons", [])
                        filtered_polygons = [
                            p for p in polygons
                            if p.get("zone_id") in new_zone_ids
                        ]
                        filtered_response["metadata"]["map_overlays"]["polygons"] = filtered_polygons
                    
                    # Save only new zones
                    save_zones_to_database(
                        zones_response=filtered_response,
                        city=payload.city,
                        method=payload.method,
                    )
                else:
                    # Normal generation - save all zones
                    save_zones_to_database(
                        zones_response=response.model_dump(),
                        city=payload.city,
                        method=payload.method,
                    )
            except Exception as exc:
                import logging
                logging.warning(f"Failed to save zones to database: {exc}")
        
        return response
    except ConnectionError as exc:
        # Database connection errors
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(exc)}. Please check your internet connection and try again."
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        # Log the full error for debugging
        import logging
        logging.exception(f"Error generating zones: {exc}")
        # Return a user-friendly error message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate zones: {str(exc)}"
        ) from exc


@router.get("/from-database", status_code=status.HTTP_200_OK)
def get_zones(
    city: str | None = Query(default=None, description="Filter zones by city"),
    method: str | None = Query(default=None, description="Filter zones by method"),
) -> dict[str, Any]:
    """Retrieve zones from database and convert to frontend format.
    
    Returns zones in the same format as generate_zones response so they can
    be displayed on the map.
    """
    try:
        # Get zones from database
        db_zones = get_zones_from_database(city=city, method=method)
        
        if not db_zones:
            return {
                "city": city or "all",
                "method": method or "all",
                "assignments": {},
                "counts": [],
                "metadata": {
                    "map_overlays": {
                        "polygons": []
                    }
                }
            }
        
        # Group zones by their generation run (same city + method + created_at grouping)
        # For simplicity, we'll group all zones for the same city/method together
        assignments: dict[str, str] = {}
        counts: list[dict[str, Any]] = []
        polygons: list[dict[str, Any]] = []
        
        for zone in db_zones:
            zone_id = zone.get("name", "")
            customer_count = zone.get("customer_count", 0)
            method_val = zone.get("method", "")
            metadata = zone.get("metadata", {})
            
            # Extract customer_ids from metadata to build assignments
            if isinstance(metadata, dict):
                customer_ids = metadata.get("customer_ids", [])
                if customer_ids and isinstance(customer_ids, list):
                    # Build assignments: customer_id -> zone_id
                    for customer_id in customer_ids:
                        if customer_id:
                            assignments[str(customer_id)] = zone_id
            
            # Get coordinates from geometry (PostGIS returns as GeoJSON), geometry_wkt, or metadata
            coordinates: list[tuple[float, float]] = []
            
            # Try to get from geometry column first (PostGIS geometry as GeoJSON from Supabase)
            geometry = zone.get("geometry")
            if geometry:
                coordinates = geojson_to_coordinates(geometry)
            
            # If no coordinates from geometry, try geometry_wkt (might still exist)
            if not coordinates:
                geometry_wkt = zone.get("geometry_wkt")
                if geometry_wkt:
                    coordinates = wkt_to_coordinates(geometry_wkt)
            
            # If still no coordinates, try to get from metadata (stored as backup)
            if not coordinates and isinstance(metadata, dict):
                coords_meta = metadata.get("coordinates")
                if coords_meta and isinstance(coords_meta, list) and len(coords_meta) > 0:
                    # Coordinates stored as list of [lat, lon] pairs
                    try:
                        coordinates = []
                        for coord in coords_meta:
                            if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                                lat = float(coord[0])
                                lon = float(coord[1])
                                coordinates.append((lat, lon))
                    except (ValueError, TypeError, IndexError):
                        coordinates = []
                else:
                    # Try geometry_wkt in metadata (old format)
                    geometry_wkt_meta = metadata.get("geometry_wkt")
                    if geometry_wkt_meta:
                        coordinates = wkt_to_coordinates(geometry_wkt_meta)
            
            # Skip if we still don't have coordinates
            if not coordinates or len(coordinates) < 3:
                import logging
                logging.warning(f"Skipping zone {zone_id}: no valid coordinates found. geometry={bool(geometry)}, geometry_wkt={bool(zone.get('geometry_wkt'))}, metadata_coords={bool(metadata.get('coordinates') if isinstance(metadata, dict) else False)}")
                continue
            
            # Add to counts
            counts.append({
                "zone_id": zone_id,
                "customer_count": customer_count
            })
            
            # Build polygon for map overlay
            polygon: dict[str, Any] = {
                "zone_id": zone_id,
                "coordinates": coordinates,
                "customer_count": customer_count,
                "source": "database"
            }
            
            # Add centroid from metadata if available
            if isinstance(metadata, dict) and "centroid" in metadata:
                polygon["centroid"] = metadata["centroid"]
            
            polygons.append(polygon)
        
        # Determine city and method from zones (use first zone if city/method not specified)
        result_city = city
        result_method = method
        if not result_city and db_zones:
            first_meta = db_zones[0].get("metadata", {})
            if isinstance(first_meta, dict) and "city" in first_meta:
                result_city = first_meta["city"]
        if not result_method and db_zones:
            result_method = db_zones[0].get("method", "")
        
        return {
            "city": result_city or "unknown",
            "method": result_method or "unknown",
            "assignments": assignments,  # Now populated from zone metadata customer_ids
            "counts": counts,
            "metadata": {
                "map_overlays": {
                    "polygons": polygons
                },
                "source": "database",
                "loaded_from_db": True
            }
        }
        
    except Exception as exc:
        import logging
        logging.exception(f"Error retrieving zones from database: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve zones from database: {str(exc)}"
        ) from exc


@router.put("/{zone_id}/geometry", status_code=status.HTTP_200_OK)
def update_zone_geometry_endpoint(
    zone_id: str,
    coordinates: list[list[float]],
) -> dict[str, Any]:
    """Update zone geometry (polygon outline).
    
    Args:
        zone_id: Zone ID to update
        coordinates: List of [lat, lon] coordinate pairs for the new polygon outline
    """
    try:
        # Validate coordinates
        if not coordinates or len(coordinates) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 3 coordinate points are required for a polygon"
            )
        
        # Convert to tuple format
        coord_tuples = []
        for coord in coordinates:
            if len(coord) < 2:
                continue
            try:
                lat = float(coord[0])
                lon = float(coord[1])
                coord_tuples.append((lat, lon))
            except (ValueError, TypeError):
                continue
        
        if len(coord_tuples) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid coordinates provided"
            )
        
        # Update zone geometry
        success = update_zone_geometry(zone_id, coord_tuples)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update zone geometry for '{zone_id}'"
            )
        
        return {
            "success": True,
            "zone_id": zone_id,
            "message": f"Zone '{zone_id}' geometry updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        import logging
        logging.exception(f"Error updating zone geometry: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update zone geometry: {str(exc)}"
        ) from exc


@router.post("/{zone_id}/customers/{customer_id}/unassign", status_code=status.HTTP_200_OK)
def unassign_customer_endpoint(zone_id: str, customer_id: str) -> dict[str, Any]:
    """Unassign a customer from a zone.
    
    Moves the customer to the unassigned pool.
    """
    try:
        success = unassign_customer_from_zone(customer_id, zone_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to unassign customer '{customer_id}' from zone '{zone_id}'"
            )
        
        return {
            "success": True,
            "customer_id": customer_id,
            "zone_id": zone_id,
            "message": f"Customer '{customer_id}' unassigned from zone '{zone_id}'"
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        import logging
        logging.exception(f"Error unassigning customer: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unassign customer: {str(exc)}"
        ) from exc


@router.post("/{zone_id}/customers/{customer_id}/assign", status_code=status.HTTP_200_OK)
def assign_customer_endpoint(zone_id: str, customer_id: str) -> dict[str, Any]:
    """Assign/transfer a customer to a zone.
    
    Moves the customer from unassigned pool (or another zone) to the specified zone.
    """
    try:
        success = assign_customer_to_zone(customer_id, zone_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to assign customer '{customer_id}' to zone '{zone_id}'"
            )
        
        return {
            "success": True,
            "customer_id": customer_id,
            "zone_id": zone_id,
            "message": f"Customer '{customer_id}' assigned to zone '{zone_id}'"
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        import logging
        logging.exception(f"Error assigning customer: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign customer: {str(exc)}"
        ) from exc


@router.get("/unassigned-customers", status_code=status.HTTP_200_OK)
def get_unassigned_customers_endpoint(
    city: str | None = Query(default=None, description="Filter by city"),
) -> dict[str, Any]:
    """Get list of unassigned customer IDs.
    
    Returns customer IDs that are not assigned to any zone.
    """
    try:
        customer_ids = get_unassigned_customers(city=city)
        
        return {
            "customer_ids": customer_ids,
            "count": len(customer_ids),
            "city": city or "all",
        }
        
    except Exception as exc:
        import logging
        logging.exception(f"Error getting unassigned customers: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get unassigned customers: {str(exc)}"
        ) from exc


@router.delete("/batch", status_code=status.HTTP_200_OK)
def delete_zones_endpoint(
    zone_ids: list[str] = Query(..., description="List of zone IDs to delete"),
) -> dict[str, Any]:
    """Delete multiple zones from the database.
    
    Args:
        zone_ids: List of zone IDs to delete
        
    Returns:
        Success status and count of deleted zones
    """
    try:
        if not zone_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No zone IDs provided"
            )
        
        success = delete_zones(zone_ids)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete zones: {zone_ids}"
            )
        
        return {
            "success": True,
            "deleted_count": len(zone_ids),
            "zone_ids": zone_ids,
            "message": f"Successfully deleted {len(zone_ids)} zone(s)"
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        import logging
        logging.exception(f"Error deleting zones: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete zones: {str(exc)}"
        ) from exc


@router.get("/summaries", response_model=List[ZoneSummaryModel], status_code=status.HTTP_200_OK)
def get_zone_summaries_from_database(
    city: str | None = Query(default=None, description="Filter zones by city"),
) -> List[ZoneSummaryModel]:
    """Get zone summaries from database (for routing workspace).
    
    Returns zones in ZoneSummary format compatible with routing workspace.
    """
    try:
        # Get zones from database
        db_zones = get_zones_from_database(city=city, method=None)
        
        if not db_zones:
            return []
        
        # Convert to ZoneSummary format
        summaries: list[dict[str, Any]] = []
        seen_zones: set[str] = set()
        
        for zone in db_zones:
            zone_id = zone.get("name", "")
            customer_count = zone.get("customer_count", 0)
            metadata = zone.get("metadata", {})
            
            # Skip duplicates (take first occurrence)
            if zone_id in seen_zones:
                continue
            seen_zones.add(zone_id)
            
            # Get city from metadata
            city_name = None
            if isinstance(metadata, dict) and "city" in metadata:
                city_name = metadata["city"]
            
            summaries.append({
                "zone": zone_id,
                "city": city_name,
                "customers": customer_count,
            })
        
        # Sort by zone ID for consistency
        summaries.sort(key=lambda x: x["zone"])
        
        return [ZoneSummaryModel(**entry) for entry in summaries]
        
    except Exception as exc:
        import logging
        logging.exception(f"Error retrieving zone summaries from database: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve zone summaries from database: {str(exc)}"
        ) from exc
