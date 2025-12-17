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
    unassign_all_customers_from_zones,
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
            
            # CRITICAL: Unassign all customers from zones BEFORE deleting them
            # This ensures customers are properly unassigned and prevents orphaned assignments
            logging.info(f"Unassigning all customers from zones before deletion: {delete_existing_zones}")
            unassign_success = unassign_all_customers_from_zones(delete_existing_zones)
            if not unassign_success:
                logging.warning(f"⚠️ Failed to unassign some customers from zones, continuing with deletion anyway")
            
            # Delete ONLY the specified zones (now with customers already unassigned)
            # Use verify=True to ensure complete deletion before proceeding
            logging.info(f"Deleting zones from database: {delete_existing_zones}")
            delete_success = delete_zones(delete_existing_zones, verify=True)
            if not delete_success:
                raise ValueError(
                    f"Failed to delete zones completely: {delete_existing_zones}. "
                    f"Some zones may still exist in the database. Please try again or delete manually."
                )
            
            logging.info(f"✅ Successfully deleted and verified removal of {len(delete_existing_zones)} zone(s)")
        
        # Generate new zones
        response = process_zoning_request(payload, persist=False)  # Don't persist yet, we'll merge first
        
        # If regenerating, merge assignments: keep existing for customers not in deleted zones
        if delete_existing_zones and existing_assignments:
            merged_assignments = existing_assignments.copy()
            # Update assignments for customers that were in deleted zones
            for customer_id, new_zone_id in response.assignments.items():
                if customer_id in customers_to_regenerate:
                    # This customer was in a deleted zone, use new assignment
                    merged_assignments[customer_id] = new_zone_id
                elif customer_id not in merged_assignments:
                    # New customer (shouldn't happen, but handle it)
                    merged_assignments[customer_id] = new_zone_id
            
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
        # CRITICAL: When regenerating, we save ALL zones from the response
        # The old zones were already deleted, so we need to save all new zones
        # Pass the deleted zone IDs so duplicate check knows these were just deleted
        if payload.persist:
            try:
                from ...persistence.database import save_zones_to_database
                
                # Save ALL zones from the response
                # If we just deleted zones, pass that info so duplicate check is smarter
                recently_deleted_zones = delete_existing_zones if delete_existing_zones else None
                save_zones_to_database(
                    zones_response=response.model_dump(),
                    city=payload.city,
                    method=payload.method,
                    check_duplicates=True,  # Ensure no duplicates - this will delete any remaining old zones
                    recently_deleted_zone_ids=recently_deleted_zones,  # Zones we just deleted - skip duplicate check for these
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
        
        # CRITICAL: Deduplicate zones by zone_id - keep only the most recent one
        # This prevents old and new zones with the same ID from appearing together
        # This is essential to prevent overlapping zones that ERB cannot accept
        # NOTE: We only deduplicate in the response, NOT in the database
        # Database cleanup should happen during regeneration, not during retrieval
        seen_zone_ids: set[str] = set()
        unique_zones: list[dict[str, Any]] = []
        duplicate_count = 0
        
        # Zones are already ordered by created_at desc, so first occurrence is most recent
        for zone in db_zones:
            zone_id = zone.get("name", "")
            if zone_id:
                if zone_id not in seen_zone_ids:
                    seen_zone_ids.add(zone_id)
                    unique_zones.append(zone)
                else:
                    duplicate_count += 1
                    # Log duplicate for debugging (but don't delete - that should happen during regeneration)
                    import logging
                    logging.warning(f"⚠️ Duplicate zone_id found and skipped in response: {zone_id} (created_at: {zone.get('created_at')})")
        
        if duplicate_count > 0:
            import logging
            logging.warning(
                f"⚠️ Found {duplicate_count} duplicate zone record(s) - kept only most recent versions in response. "
                f"To clean up duplicates, regenerate the affected zones."
            )
        
        # Group zones by their generation run (same city + method + created_at grouping)
        # For simplicity, we'll group all zones for the same city/method together
        assignments: dict[str, str] = {}
        counts: list[dict[str, Any]] = []
        polygons: list[dict[str, Any]] = []
        
        for zone in unique_zones:
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
            
            # Get coordinates from metadata (primary after edits), geometry_wkt, or geometry
            coordinates: list[tuple[float, float]] = []
            
            # PRIORITY 1: Check metadata.coordinates first (this is where edits are saved)
            if isinstance(metadata, dict):
                coords_meta = metadata.get("coordinates")
                if coords_meta and isinstance(coords_meta, list) and len(coords_meta) >= 3:
                    try:
                        for coord in coords_meta:
                            if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                                lat = float(coord[0])
                                lon = float(coord[1])
                                coordinates.append((lat, lon))
                    except (ValueError, TypeError, IndexError):
                        coordinates = []
            
            # PRIORITY 2: Try geometry_wkt (also updated during edits)
            if not coordinates or len(coordinates) < 3:
                geometry_wkt = zone.get("geometry_wkt")
                if geometry_wkt:
                    coordinates = wkt_to_coordinates(geometry_wkt)
            
            # PRIORITY 3: Fall back to PostGIS geometry column (original data)
            if not coordinates or len(coordinates) < 3:
                geometry = zone.get("geometry")
                if geometry:
                    coordinates = geojson_to_coordinates(geometry)
            
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
        error_msg = str(exc)
        logging.exception(f"Error updating zone geometry: {exc}")
        
        # Provide more helpful error messages
        if "getaddrinfo" in error_msg or "11001" in error_msg:
            detail = (
                f"Cannot connect to database. DNS resolution failed. "
                f"Please check:\n"
                f"1. Your internet connection\n"
                f"2. IZG_SUPABASE_URL in .env file is correct\n"
                f"3. Supabase project is active and accessible"
            )
        elif "not configured" in error_msg.lower():
            detail = (
                f"Database not configured. Please set IZG_SUPABASE_URL and IZG_SUPABASE_KEY in .env file"
            )
        else:
            detail = f"Failed to update zone geometry: {error_msg}"
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
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
