"""API routes for zone generation."""

from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, HTTPException, Query, status

from ...persistence.database import get_zones_from_database, wkt_to_coordinates, geojson_to_coordinates, update_zone_geometry
from ...schemas.zoning import ZoningRequest, ZoningResponse
from ...schemas.customers import ZoneSummaryModel
from ...services.zoning.service import process_zoning_request

router = APIRouter(prefix="/zones", tags=["zones"])


@router.post("/generate", response_model=ZoningResponse, status_code=status.HTTP_200_OK)
def generate_zones(payload: ZoningRequest) -> ZoningResponse:
    try:
        return process_zoning_request(payload, persist=payload.persist)
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
            "assignments": assignments,  # Empty - would need customer assignments to populate
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
