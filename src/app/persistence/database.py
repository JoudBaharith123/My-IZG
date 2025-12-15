"""Database persistence for zones and routes."""

from __future__ import annotations

from typing import Any

from ..db.supabase import get_supabase_client
from ..data.customers_repository import resolve_depot
from ..models.domain import Customer
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
                
                # Store assignments for this zone (customer_id -> zone_id mapping)
                assignments = zones_response.get("assignments", {})
                zone_assignments = {
                    customer_id: assigned_zone
                    for customer_id, assigned_zone in assignments.items()
                    if assigned_zone == zone_id
                }
                if zone_assignments:
                    metadata["customer_ids"] = list(zone_assignments.keys())
                
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




def update_zone_geometry(zone_id: str, coordinates: list[tuple[float, float]]) -> bool:
    """Update zone geometry in the database.
    
    Args:
        zone_id: Zone name/ID to update
        coordinates: List of [lat, lon] coordinate pairs for the new polygon
        
    Returns:
        True if successful, False otherwise
    """
    supabase = get_supabase_client()
    if not supabase:
        import logging
        logging.warning("Database not configured - cannot update zone geometry")
        return False
    
    if not coordinates or len(coordinates) < 3:
        import logging
        logging.warning(f"Invalid coordinates for zone '{zone_id}': need at least 3 points")
        return False
    
    try:
        # Convert coordinates to WKT format
        geometry_wkt = polygon_to_wkt(coordinates)
        
        # Update the zone's geometry
        # First, try to find the zone (get the most recent one if multiple exist)
        response = supabase.table("zones").select("id").eq("name", zone_id).order("created_at", desc=True).limit(1).execute()
        
        if not response.data or len(response.data) == 0:
            import logging
            logging.warning(f"Zone '{zone_id}' not found in database")
            return False
        
        zone_db_id = response.data[0]["id"]
        
        # Update geometry using geometry_wkt (will be converted by trigger)
        update_response = supabase.table("zones").update({
            "geometry_wkt": geometry_wkt,
        }).eq("id", zone_db_id).execute()
        
        # Also update metadata coordinates as backup
        zone_data = supabase.table("zones").select("metadata").eq("id", zone_db_id).execute()
        if zone_data.data:
            metadata = zone_data.data[0].get("metadata", {})
            if isinstance(metadata, dict):
                metadata["coordinates"] = coordinates
                metadata["geometry_updated"] = True
                supabase.table("zones").update({
                    "metadata": metadata
                }).eq("id", zone_db_id).execute()
        
        import logging
        logging.info(f"Successfully updated geometry for zone '{zone_id}'")
        return True
        
    except Exception as e:
        import logging
        logging.error(f"Failed to update zone geometry for '{zone_id}': {e}")
        return False


def unassign_customer_from_zone(customer_id: str, zone_id: str) -> bool:
    """Unassign a customer from a zone.
    
    Removes the customer_id from the zone's metadata customer_ids list.
    Updates customer_count accordingly.
    
    Args:
        customer_id: Customer ID to unassign
        zone_id: Zone ID to remove customer from
        
    Returns:
        True if successful, False otherwise
    """
    supabase = get_supabase_client()
    if not supabase:
        import logging
        logging.warning("Database not configured - cannot unassign customer from zone")
        return False
    
    try:
        # Find the zone in the database
        response = supabase.table("zones").select("*").eq("name", zone_id).order("created_at", desc=True).limit(1).execute()
        
        if not response.data or len(response.data) == 0:
            import logging
            logging.warning(f"Zone '{zone_id}' not found in database")
            return False
        
        zone = response.data[0]
        zone_db_id = zone["id"]
        metadata = zone.get("metadata", {})
        
        if not isinstance(metadata, dict):
            metadata = {}
        
        # Get current customer_ids list
        customer_ids = metadata.get("customer_ids", [])
        if not isinstance(customer_ids, list):
            customer_ids = []
        
        # Remove customer_id if present
        if customer_id in customer_ids:
            customer_ids.remove(customer_id)
            metadata["customer_ids"] = customer_ids
            
            # Update customer_count
            new_count = len(customer_ids)
            
            # Update zone in database
            supabase.table("zones").update({
                "metadata": metadata,
                "customer_count": new_count,
            }).eq("id", zone_db_id).execute()
            
            import logging
            logging.info(f"Unassigned customer '{customer_id}' from zone '{zone_id}'. New customer_count: {new_count}")
            return True
        else:
            import logging
            logging.warning(f"Customer '{customer_id}' not found in zone '{zone_id}' customer_ids")
            return False
        
    except Exception as e:
        import logging
        logging.error(f"Failed to unassign customer '{customer_id}' from zone '{zone_id}': {e}")
        return False


def assign_customer_to_zone(customer_id: str, zone_id: str) -> bool:
    """Assign/transfer a customer to a zone.
    
    Adds the customer_id to the zone's metadata customer_ids list.
    Updates customer_count accordingly.
    
    Args:
        customer_id: Customer ID to assign
        zone_id: Zone ID to assign customer to
        
    Returns:
        True if successful, False otherwise
    """
    supabase = get_supabase_client()
    if not supabase:
        import logging
        logging.warning("Database not configured - cannot assign customer to zone")
        return False
    
    try:
        # First, remove customer from any other zone they might be assigned to
        # Find all zones that contain this customer
        all_zones_response = supabase.table("zones").select("id, name, metadata").execute()
        
        if all_zones_response.data:
            for zone in all_zones_response.data:
                zone_meta = zone.get("metadata", {})
                if isinstance(zone_meta, dict):
                    zone_customer_ids = zone_meta.get("customer_ids", [])
                    if isinstance(zone_customer_ids, list) and customer_id in zone_customer_ids:
                        # Remove from this zone
                        zone_customer_ids.remove(customer_id)
                        zone_meta["customer_ids"] = zone_customer_ids
                        old_count = zone.get("customer_count", 0)
                        new_count = max(0, old_count - 1)
                        
                        supabase.table("zones").update({
                            "metadata": zone_meta,
                            "customer_count": new_count,
                        }).eq("id", zone["id"]).execute()
        
        # Now add customer to the target zone
        response = supabase.table("zones").select("*").eq("name", zone_id).order("created_at", desc=True).limit(1).execute()
        
        if not response.data or len(response.data) == 0:
            import logging
            logging.warning(f"Zone '{zone_id}' not found in database")
            return False
        
        zone = response.data[0]
        zone_db_id = zone["id"]
        metadata = zone.get("metadata", {})
        
        if not isinstance(metadata, dict):
            metadata = {}
        
        # Get current customer_ids list
        customer_ids = metadata.get("customer_ids", [])
        if not isinstance(customer_ids, list):
            customer_ids = []
        
        # Add customer_id if not already present
        if customer_id not in customer_ids:
            customer_ids.append(customer_id)
            metadata["customer_ids"] = customer_ids
            
            # Update customer_count
            new_count = len(customer_ids)
            
            # Update zone in database
            supabase.table("zones").update({
                "metadata": metadata,
                "customer_count": new_count,
            }).eq("id", zone_db_id).execute()
            
            import logging
            logging.info(f"Assigned customer '{customer_id}' to zone '{zone_id}'. New customer_count: {new_count}")
            return True
        else:
            import logging
            logging.info(f"Customer '{customer_id}' already assigned to zone '{zone_id}'")
            return True  # Already assigned, consider it success
        
    except Exception as e:
        import logging
        logging.error(f"Failed to assign customer '{customer_id}' to zone '{zone_id}': {e}")
        return False


def get_unassigned_customers(city: str | None = None) -> list[str]:
    """Get list of customer IDs that are not assigned to any zone.
    
    Args:
        city: Optional city filter
        
    Returns:
        List of unassigned customer IDs
    """
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        # Get all zones and collect all assigned customer IDs
        query = supabase.table("zones").select("metadata")
        if city:
            query = query.contains("metadata", {"city": city})
        
        response = query.execute()
        assigned_customer_ids = set()
        
        if response.data:
            for zone in response.data:
                metadata = zone.get("metadata", {})
                if isinstance(metadata, dict):
                    customer_ids = metadata.get("customer_ids", [])
                    if isinstance(customer_ids, list):
                        assigned_customer_ids.update(customer_ids)
        
        # Get all customers from database for the city (if specified)
        customer_query = supabase.table("customers").select("customer_id")
        if city:
            customer_query = customer_query.eq("city", city)
        
        customer_response = customer_query.execute()
        all_customer_ids = set()
        if customer_response.data:
            for record in customer_response.data:
                customer_id = record.get("customer_id")
                if customer_id:
                    all_customer_ids.add(str(customer_id))
        
        # Filter to get unassigned customers
        unassigned_ids = list(all_customer_ids - assigned_customer_ids)
        return unassigned_ids
        
    except Exception as e:
        import logging
        logging.error(f"Failed to get unassigned customers: {e}")
        return []


def get_customers_from_zones(zone_ids: list[str]) -> list[str]:
    """Get all customer IDs from specified zones before deletion.
    
    Args:
        zone_ids: List of zone IDs to get customers from
        
    Returns:
        List of customer IDs that were in these zones
    """
    supabase = get_supabase_client()
    if not supabase or not zone_ids:
        return []
    
    try:
        customer_ids = set()
        response = supabase.table("zones").select("metadata").in_("name", zone_ids).execute()
        
        if response.data:
            for zone in response.data:
                metadata = zone.get("metadata", {})
                if isinstance(metadata, dict):
                    zone_customer_ids = metadata.get("customer_ids", [])
                    if isinstance(zone_customer_ids, list):
                        customer_ids.update(zone_customer_ids)
        
        return list(customer_ids)
    except Exception as e:
        import logging
        logging.warning(f"Failed to get customers from zones {zone_ids}: {e}")
        return []


def delete_zones(zone_ids: list[str]) -> bool:
    """Delete zones from the database by their zone IDs.
    
    Args:
        zone_ids: List of zone IDs (zone names) to delete
        
    Returns:
        True if successful, False otherwise
    """
    supabase = get_supabase_client()
    if not supabase:
        import logging
        logging.warning("Database not configured - cannot delete zones")
        return False
    
    if not zone_ids:
        return True  # Nothing to delete
    
    try:
        # Delete zones by name (zone_id)
        response = supabase.table("zones").delete().in_("name", zone_ids).execute()
        
        import logging
        logging.info(f"Deleted {len(zone_ids)} zones from database: {zone_ids}")
        return True
        
    except Exception as e:
        import logging
        logging.error(f"Failed to delete zones {zone_ids} from database: {e}")
        return False


def get_customers_for_zone(zone_id: str) -> tuple[Customer, ...]:
    """Get customers assigned to a zone from the database.
    
    This function looks up the zone in the database, retrieves the customer_ids
    stored in the zone's metadata, and then loads those customers from the database.
    
    Args:
        zone_id: The zone ID to get customers for
        
    Returns:
        Tuple of Customer objects assigned to the zone
    """
    supabase = get_supabase_client()
    if not supabase:
        import logging
        logging.warning("Database not configured - cannot fetch customers for zone")
        return tuple()
    
    try:
        # Find the zone in the database
        response = supabase.table("zones").select("*").eq("name", zone_id).order("created_at", desc=True).limit(1).execute()
        
        if not response.data or len(response.data) == 0:
            import logging
            logging.warning(f"Zone '{zone_id}' not found in database")
            return tuple()
        
        zone = response.data[0]
        metadata = zone.get("metadata", {})
        
        # Get customer IDs from metadata
        customer_ids = None
        if isinstance(metadata, dict):
            customer_ids = metadata.get("customer_ids")
        
        if not customer_ids or not isinstance(customer_ids, list):
            import logging
            logging.warning(f"Zone '{zone_id}' has no customer_ids stored in metadata")
            return tuple()
        
        # Load customers from database by IDs
        from ..data.customers_repository import get_customers_by_ids
        return get_customers_by_ids(customer_ids)
        
    except Exception as e:
        import logging
        logging.warning(f"Failed to retrieve customers for zone {zone_id} from database: {e}")
        return tuple()

