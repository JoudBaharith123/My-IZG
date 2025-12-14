"""Database persistence for zones and routes."""

from __future__ import annotations

from typing import Any

from ..db.supabase import get_supabase_client
from ..data.customers_repository import resolve_depot
from ..services.export.geojson import polygon_to_wkt
import re


def save_zones_to_database(
    zones_response: dict[str, Any],
    city: str,
    method: str,
) -> None:
    """Save generated zones to Supabase database.
    
    Args:
        zones_response: Zone generation response with assignments, counts, and metadata
        city: City name for the zones
        method: Zoning method used (polar, isochrone, clustering, manual)
    """
    supabase = get_supabase_client()
    if not supabase:
        # Database not configured, skip silently
        import logging
        logging.info("Supabase not configured - zones will only be saved to files")
        return
    
    try:
        # Get depot code for the city
        depot = resolve_depot(city)
        depot_code = depot.code if depot else None
        
        # Get map overlays (polygons) from metadata
        map_overlays = zones_response.get("metadata", {}).get("map_overlays", {})
        polygons = map_overlays.get("polygons", [])
        
        # Get zone counts
        counts = zones_response.get("counts", [])
        count_map = {count["zone_id"]: count["customer_count"] for count in counts}
        
        # Prepare zones for database insertion
        zones_to_insert = []
        for polygon in polygons:
            zone_id = polygon.get("zone_id")
            coordinates = polygon.get("coordinates", [])
            
            if not zone_id or not coordinates or len(coordinates) < 3:
                continue
            
            try:
                # Convert to WKT format for PostGIS
                geometry_wkt = polygon_to_wkt(coordinates)
                
                # Get customer count for this zone
                customer_count = count_map.get(zone_id, 0)
                
                # Prepare metadata (store coordinates as backup for retrieval)
                metadata = {
                    "zone_id": zone_id,
                    "city": city,
                    "method": method,
                    "centroid": polygon.get("centroid"),
                    "source": polygon.get("source", "unknown"),
                    "coordinates": coordinates,  # Store coordinates in metadata as backup
                }
                
                # Add any additional metadata from the response
                response_metadata = zones_response.get("metadata", {})
                if "max_customers_per_zone" in response_metadata:
                    metadata["max_customers_per_zone"] = response_metadata["max_customers_per_zone"]
                if "target_zones" in response_metadata:
                    metadata["target_zones"] = response_metadata["target_zones"]
                
                zones_to_insert.append({
                    "name": zone_id,
                    "geometry_wkt": geometry_wkt,  # Use geometry_wkt column (converted by trigger)
                    "depot_code": depot_code,
                    "customer_count": customer_count,
                    "method": method,
                    "metadata": metadata,
                })
            except (ValueError, KeyError) as e:
                # Skip invalid polygons but continue processing
                import logging
                logging.warning(f"Skipping invalid polygon for zone {zone_id}: {e}")
                continue
        
        # Insert zones into database
        if zones_to_insert:
            import logging
            logging.info(f"Attempting to save {len(zones_to_insert)} zones to database")
            
            inserted_count = 0
            failed_count = 0
            
            for zone_data in zones_to_insert:
                try:
                    # Try RPC function first (if it exists in database)
                    try:
                        result = supabase.rpc(
                            "insert_zone_with_geometry",
                            {
                                "zone_name": zone_data["name"],
                                "geometry_wkt": zone_data["geometry_wkt"],
                                "depot_code": zone_data["depot_code"],
                                "customer_count": zone_data["customer_count"],
                                "method": zone_data["method"],
                                "metadata": zone_data["metadata"],
                            }
                        ).execute()
                        inserted_count += 1
                        logging.info(f"✓ Inserted zone {zone_data['name']} via RPC function")
                    except Exception as rpc_error:
                        # Fallback: Try using geometry_wkt column with trigger
                        try:
                            supabase.table("zones").insert({
                                "name": zone_data["name"],
                                "geometry_wkt": zone_data["geometry_wkt"],
                                "depot_code": zone_data["depot_code"],
                                "customer_count": zone_data["customer_count"],
                                "method": zone_data["method"],
                                "metadata": zone_data["metadata"],
                            }).execute()
                            inserted_count += 1
                            logging.info(f"✓ Inserted zone {zone_data['name']} via geometry_wkt trigger")
                        except Exception as trigger_error:
                            # Last fallback: Store WKT in metadata (geometry will be null)
                            try:
                                metadata_with_wkt = {**zone_data["metadata"], "geometry_wkt": zone_data["geometry_wkt"]}
                                supabase.table("zones").insert({
                                    "name": zone_data["name"],
                                    "depot_code": zone_data["depot_code"],
                                    "customer_count": zone_data["customer_count"],
                                    "method": zone_data["method"],
                                    "metadata": metadata_with_wkt,
                                }).execute()
                                inserted_count += 1
                                logging.warning(f"⚠ Inserted zone {zone_data['name']} without geometry (WKT in metadata). RPC error: {rpc_error}, Trigger error: {trigger_error}")
                            except Exception as final_error:
                                failed_count += 1
                                logging.error(f"✗ Failed to insert zone {zone_data['name']}: RPC={rpc_error}, Trigger={trigger_error}, Final={final_error}")
                                continue
                except Exception as e:
                    failed_count += 1
                    logging.error(f"✗ Unexpected error inserting zone {zone_data['name']}: {e}")
                    continue
            
            if inserted_count > 0:
                logging.info(f"✓ Successfully inserted {inserted_count} out of {len(zones_to_insert)} zones to database")
            if failed_count > 0:
                logging.warning(f"⚠ Failed to insert {failed_count} zones. Check database configuration and schema.")
                    
    except Exception as e:
        # Log error but don't fail the entire request
        import logging
        logging.warning(f"Failed to save zones to database: {e}")


def wkt_to_coordinates(wkt: str) -> list[tuple[float, float]]:
    """Convert WKT POLYGON string to coordinates.
    
    Args:
        wkt: WKT POLYGON string (format: POLYGON((lon lat, lon lat, ...)))
        
    Returns:
        List of [lat, lon] coordinate pairs
    """
    if not wkt:
        return []
    
    # Handle WKT format
    if wkt.startswith("POLYGON"):
        # Extract coordinates from POLYGON((...)) format
        # Match the content between the double parentheses
        match = re.search(r'POLYGON\(\(([^)]+)\)\)', wkt)
        if not match:
            return []
        
        coord_string = match.group(1)
        # Split by comma and parse lon lat pairs
        coords = []
        for pair in coord_string.split(','):
            pair = pair.strip()
            parts = pair.split()
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    # Return as [lat, lon] to match frontend format
                    coords.append((lat, lon))
                except (ValueError, IndexError):
                    continue
        
        return coords
    
    return []


def geojson_to_coordinates(geojson: dict[str, Any]) -> list[tuple[float, float]]:
    """Convert GeoJSON geometry to coordinates.
    
    Args:
        geojson: GeoJSON geometry object (from Supabase PostGIS)
        
    Returns:
        List of [lat, lon] coordinate pairs
    """
    if not geojson:
        return []
    
    # Handle GeoJSON format from Supabase
    # Supabase returns PostGIS geometry as: {"type": "Polygon", "coordinates": [[[lon, lat], ...]]}
    if isinstance(geojson, dict):
        geom_type = geojson.get("type", "").upper()
        coords_array = geojson.get("coordinates", [])
        
        if geom_type == "POLYGON" and coords_array:
            # Polygon coordinates are [[[lon, lat], [lon, lat], ...]]
            # Take the first ring (exterior ring)
            ring = coords_array[0] if coords_array else []
            coords = []
            for coord in ring:
                if len(coord) >= 2:
                    try:
                        lon = float(coord[0])
                        lat = float(coord[1])
                        # Return as [lat, lon] to match frontend format
                        coords.append((lat, lon))
                    except (ValueError, TypeError):
                        continue
            return coords
    
    return []


def get_zones_from_database(city: str | None = None, method: str | None = None) -> list[dict[str, Any]]:
    """Retrieve zones from database.
    
    Args:
        city: Optional city filter
        method: Optional method filter
        
    Returns:
        List of zone records from database
    """
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        # Select all columns including geometry (Supabase will return PostGIS geometry as GeoJSON)
        # Note: We rely on metadata.coordinates as primary source, geometry is fallback
        query = supabase.table("zones").select("*")
        
        if city:
            # Filter by city in metadata
            query = query.contains("metadata", {"city": city})
        
        if method:
            query = query.eq("method", method)
        
        response = query.order("created_at", desc=True).execute()
        zones_data = response.data if response.data else []
        
        # Log for debugging
        if zones_data:
            import logging
            logging.info(f"Retrieved {len(zones_data)} zones from database (city={city}, method={method})")
        
        return zones_data
    except Exception as e:
        import logging
        logging.warning(f"Failed to retrieve zones from database: {e}")
        return []

