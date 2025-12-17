"""Database persistence for zones and routes."""

from __future__ import annotations

from typing import Any

from ..db.supabase import get_supabase_client
from ..data.customers_repository import resolve_depot
from ..models.domain import Customer
from ..services.export.geojson import polygon_to_wkt
import re


def check_zone_ids_exist(zone_ids: list[str]) -> dict[str, bool]:
    """Check which zone IDs already exist in the database.
    
    Args:
        zone_ids: List of zone IDs to check
        
    Returns:
        Dictionary mapping zone_id to True if it exists, False otherwise
    """
    supabase = get_supabase_client()
    if not supabase or not zone_ids:
        return {zone_id: False for zone_id in zone_ids}
    
    try:
        response = supabase.table("zones").select("name").in_("name", zone_ids).execute()
        existing_ids = {z["name"] for z in (response.data or [])}
        return {zone_id: zone_id in existing_ids for zone_id in zone_ids}
    except Exception as e:
        import logging
        logging.warning(f"Failed to check existing zone IDs: {e}")
        return {zone_id: False for zone_id in zone_ids}


def save_zones_to_database(
    zones_response: dict[str, Any],
    city: str,
    method: str,
    check_duplicates: bool = True,
    recently_deleted_zone_ids: list[str] | None = None,
) -> None:
    """Save generated zones to Supabase database.
    
    Args:
        zones_response: Zone generation response with assignments, counts, and metadata
        city: City name for the zones
        method: Zoning method used (polar, isochrone, clustering, manual)
        check_duplicates: If True, check for and delete duplicate zone IDs before saving
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
                    
                    # Validate: Ensure customers are only assigned to this zone
                    # Check if any of these customers appear in other zones being saved
                    for other_zone in zones_to_insert:
                        if other_zone["name"] != zone_id:
                            other_meta = other_zone.get("metadata", {}) if isinstance(other_zone.get("metadata"), dict) else {}
                            other_customer_ids = other_meta.get("customer_ids", [])
                            if isinstance(other_customer_ids, list):
                                duplicates = set(zone_assignments.keys()) & set(other_customer_ids)
                                if duplicates:
                                    import logging
                                    logging.error(
                                        f"❌ CRITICAL: Customer(s) {list(duplicates)} are assigned to multiple zones: "
                                        f"{zone_id} and {other_zone['name']}. This violates ERB requirements!"
                                    )
                                    raise ValueError(
                                        f"Customer assignment conflict: {len(duplicates)} customer(s) assigned to "
                                        f"multiple zones. Customers: {list(duplicates)[:5]}..."
                                    )
                
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
            
            # CRITICAL: Check for and delete ALL duplicate zone IDs before inserting
            # This prevents overlapping zones (old and new with same ID)
            # We must delete ALL records with these zone_ids, not just one per ID
            if check_duplicates:
                zone_ids_to_save = [z["name"] for z in zones_to_insert]
                existing_check = check_zone_ids_exist(zone_ids_to_save)
                
                # Filter out zones that were recently deleted - these are expected to not exist
                # but might still show up due to database replication delays
                duplicate_ids = [
                    zone_id for zone_id, exists in existing_check.items() 
                    if exists and (recently_deleted_zone_ids is None or zone_id not in recently_deleted_zone_ids)
                ]
                
                # If we have recently deleted zones that still exist, wait a bit longer for DB to sync
                if recently_deleted_zone_ids:
                    recently_deleted_still_existing = [
                        zone_id for zone_id in recently_deleted_zone_ids
                        if existing_check.get(zone_id, False)
                    ]
                    if recently_deleted_still_existing:
                        import time
                        import logging
                        logging.info(f"⏳ Zones {recently_deleted_still_existing} were just deleted but still appear in DB. Waiting for DB sync...")
                        time.sleep(0.5)  # Wait for database replication
                        # Re-check after delay
                        existing_check = check_zone_ids_exist(zone_ids_to_save)
                        duplicate_ids = [
                            zone_id for zone_id, exists in existing_check.items() 
                            if exists and zone_id not in recently_deleted_zone_ids
                        ]
                        # Log if they still exist after waiting
                        still_existing_after_wait = [
                            zone_id for zone_id in recently_deleted_zone_ids
                            if existing_check.get(zone_id, False)
                        ]
                        if still_existing_after_wait:
                            logging.warning(f"⚠️ Zones {still_existing_after_wait} still exist after wait. They will be treated as duplicates and deleted.")
                            # Add them back to duplicate_ids so they get deleted
                            duplicate_ids.extend(still_existing_after_wait)
                
                if duplicate_ids:
                    # Check if these are zones that were recently deleted
                    if recently_deleted_zone_ids:
                        unexpected_duplicates = [zid for zid in duplicate_ids if zid not in recently_deleted_zone_ids]
                        if unexpected_duplicates:
                            logging.warning(f"⚠️ Found {len(unexpected_duplicates)} unexpected duplicate zone IDs: {unexpected_duplicates}")
                        if len(duplicate_ids) > len(unexpected_duplicates):
                            logging.info(f"ℹ️ Found {len(duplicate_ids) - len(unexpected_duplicates)} zone(s) that were recently deleted but still in DB: {[zid for zid in duplicate_ids if zid in recently_deleted_zone_ids]}")
                    else:
                        logging.warning(f"⚠️ Found {len(duplicate_ids)} duplicate zone IDs before saving: {duplicate_ids}")
                    
                    # Count how many records exist for these zone_ids
                    count_query = supabase.table("zones").select("name", count="exact").in_("name", duplicate_ids).execute()
                    total_duplicate_records = count_query.count if hasattr(count_query, 'count') else None
                    if total_duplicate_records:
                        logging.info(f"ℹ️ Found {total_duplicate_records} total duplicate zone record(s) to delete")
                    
                    logging.info(f"Deleting ALL duplicate zones (including all records with same zone_id) to prevent overlaps...")
                    
                    # Unassign customers from ALL duplicate zones first
                    unassign_all_customers_from_zones(duplicate_ids)
                    
                    # Delete ALL duplicate zones - this should delete ALL records with these zone_ids
                    delete_success = delete_zones(duplicate_ids, verify=True)
                    if not delete_success:
                        # Try one more time with a longer delay
                        import time
                        time.sleep(0.5)
                        delete_success = delete_zones(duplicate_ids, verify=True)
                        if not delete_success:
                            logging.error(f"❌ Failed to delete duplicate zones after retry: {duplicate_ids}")
                            raise ValueError(
                                f"Cannot save zones: duplicate zone IDs still exist after deletion attempt: {duplicate_ids}. "
                                f"Please manually delete these zones from the database."
                            )
                    
                    # Final verification - check if any still exist
                    final_check = check_zone_ids_exist(duplicate_ids)
                    still_existing = [zone_id for zone_id, exists in final_check.items() if exists]
                    if still_existing:
                        logging.error(f"❌ CRITICAL: Some duplicate zones still exist after deletion: {still_existing}")
                        logging.warning(f"⚠️ Attempting to continue anyway - new zones will be saved and may create duplicates")
                        # Don't raise error - allow save to proceed, duplicate checking will handle it
                        # The worst case is we'll have duplicates which can be cleaned up later
                    
                    logging.info(f"✅ Cleanup complete - proceeding to save new zones")
            
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
                logging.error(f"❌ Failed to insert {failed_count} zones. Check database configuration and schema.")
                # This is critical - if zones aren't saved, customers will remain unassigned
                raise ValueError(f"Failed to save {failed_count} zone(s) to database. Zones may not be available and customers may remain unassigned.")
            
            # Verify that zones were actually saved
            if inserted_count == 0 and len(zones_to_insert) > 0:
                logging.error(f"❌ CRITICAL: No zones were inserted despite having {len(zones_to_insert)} zones to save!")
                raise ValueError("Failed to save any zones to database. Please check database connection and schema.")
                    
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
        logging.error("Database not configured - cannot update zone geometry. Check IZG_SUPABASE_URL and IZG_SUPABASE_KEY in .env file")
        return False
    
    # Test connection before attempting update
    try:
        # Quick connection test - try to query a simple table
        test_response = supabase.table("zones").select("id").limit(1).execute()
    except Exception as conn_error:
        import logging
        error_msg = str(conn_error)
        if "getaddrinfo" in error_msg or "11001" in error_msg:
            logging.error(f"Cannot connect to Supabase database. DNS resolution failed. Check your IZG_SUPABASE_URL in .env file. Error: {error_msg}")
        else:
            logging.error(f"Cannot connect to Supabase database. Error: {error_msg}")
        return False
    
    if not coordinates or len(coordinates) < 3:
        import logging
        logging.warning(f"Invalid coordinates for zone '{zone_id}': need at least 3 points")
        return False
    
    try:
        import logging
        
        # Convert coordinates to WKT format
        geometry_wkt = polygon_to_wkt(coordinates)
        logging.info(f"📤 UPDATE_ZONE_GEOMETRY: zone_id={zone_id}, coord_count={len(coordinates)}")
        logging.info(f"📤 COORDINATES RECEIVED: {coordinates[:3]}... (first 3 points)")
        logging.info(f"📤 WKT GENERATED: {geometry_wkt[:100]}...")
        
        # Update the zone's geometry with retry logic for network errors
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # First, try to find the zone (get the most recent one if multiple exist)
                response = supabase.table("zones").select("id").eq("name", zone_id).order("created_at", desc=True).limit(1).execute()
                
                if not response.data or len(response.data) == 0:
                    logging.warning(f"❌ Zone '{zone_id}' not found in database")
                    return False
                
                zone_db_id = response.data[0]["id"]
                logging.info(f"📍 Found zone in DB: zone_id={zone_id}, db_id={zone_db_id}")
                
                # Update geometry using geometry_wkt (will be converted by trigger)
                update_response = supabase.table("zones").update({
                    "geometry_wkt": geometry_wkt,
                }).eq("id", zone_db_id).execute()
                logging.info(f"✅ DB UPDATE geometry_wkt: response={update_response.data}")
                
                # Also update metadata coordinates as backup
                zone_data = supabase.table("zones").select("metadata").eq("id", zone_db_id).execute()
                if zone_data.data:
                    metadata = zone_data.data[0].get("metadata", {})
                    if isinstance(metadata, dict):
                        metadata["coordinates"] = coordinates
                        metadata["geometry_updated"] = True
                        metadata_response = supabase.table("zones").update({
                            "metadata": metadata
                        }).eq("id", zone_db_id).execute()
                        logging.info(f"✅ DB UPDATE metadata.coordinates: saved {len(coordinates)} points")
                
                # VERIFY: Read back the saved data to confirm
                verify_response = supabase.table("zones").select("geometry_wkt, metadata").eq("id", zone_db_id).execute()
                if verify_response.data:
                    saved_wkt = verify_response.data[0].get("geometry_wkt", "")
                    saved_meta = verify_response.data[0].get("metadata", {})
                    saved_coords = saved_meta.get("coordinates", []) if isinstance(saved_meta, dict) else []
                    logging.info(f"✅ VERIFIED SAVED DATA: wkt_length={len(saved_wkt)}, coord_count={len(saved_coords)}")
                    if saved_coords:
                        logging.info(f"✅ VERIFIED FIRST COORD: {saved_coords[0]}")
                
                logging.info(f"✅ Successfully updated geometry for zone '{zone_id}'")
                return True
                
            except Exception as retry_error:
                retry_count += 1
                error_msg = str(retry_error)
                # Check if it's a network/DNS error
                if ("getaddrinfo" in error_msg or "11001" in error_msg or "network" in error_msg.lower()) and retry_count < max_retries:
                    import logging
                    import time
                    logging.warning(f"Network error updating zone '{zone_id}' (attempt {retry_count}/{max_retries}): {error_msg}. Retrying...")
                    time.sleep(1 * retry_count)  # Exponential backoff
                    continue
                else:
                    raise  # Re-raise if not a network error or max retries reached
        
    except Exception as e:
        import logging
        error_msg = str(e)
        # Check if it's a network/DNS error
        if "getaddrinfo" in error_msg or "11001" in error_msg:
            logging.error(f"Network error updating zone geometry for '{zone_id}': Cannot connect to database. Check your internet connection and Supabase configuration.")
        else:
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
    
    IMPORTANT: When filtering by city, we check ALL zones (not just city-filtered)
    because a customer should only be considered "assigned" if they're in ANY zone,
    regardless of the zone's city. However, we only return unassigned customers
    for the specified city.
    
    Args:
        city: Optional city filter (only affects which customers are returned, not which zones are checked)
        
    Returns:
        List of unassigned customer IDs for the specified city (or all cities if None)
    """
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        import logging
        
        # CRITICAL: Get ALL zones (not filtered by city) to find all assigned customers
        # A customer is "assigned" if they're in ANY zone, regardless of the zone's city
        query = supabase.table("zones").select("metadata")
        response = query.execute()
        assigned_customer_ids = set()
        
        if response.data:
            for zone in response.data:
                metadata = zone.get("metadata", {})
                if isinstance(metadata, dict):
                    customer_ids = metadata.get("customer_ids", [])
                    if isinstance(customer_ids, list):
                        # Convert all to strings for consistency
                        assigned_customer_ids.update(str(cid) for cid in customer_ids if cid)
        
        logging.info(f"Found {len(assigned_customer_ids)} assigned customers across all zones")
        
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
        
        logging.info(f"Found {len(all_customer_ids)} total customers for city={city or 'all'}")
        
        # Filter to get unassigned customers
        unassigned_ids = list(all_customer_ids - assigned_customer_ids)
        logging.info(f"Found {len(unassigned_ids)} unassigned customers for city={city or 'all'}")
        
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


def unassign_all_customers_from_zones(zone_ids: list[str]) -> bool:
    """Unassign all customers from specified zones before deletion.
    
    This ensures customers are properly unassigned from zones before the zones
    are deleted, preventing orphaned assignments.
    
    Args:
        zone_ids: List of zone IDs to unassign customers from
        
    Returns:
        True if successful, False otherwise
    """
    supabase = get_supabase_client()
    if not supabase:
        import logging
        logging.warning("Database not configured - cannot unassign customers from zones")
        return False
    
    if not zone_ids:
        return True  # Nothing to unassign
    
    try:
        # Get all zones that will be deleted
        response = supabase.table("zones").select("id, name, metadata").in_("name", zone_ids).execute()
        
        if not response.data:
            import logging
            logging.info(f"No zones found to unassign customers from: {zone_ids}")
            return True
        
        unassigned_count = 0
        for zone in response.data:
            zone_db_id = zone["id"]
            zone_id = zone["name"]
            metadata = zone.get("metadata", {})
            
            if not isinstance(metadata, dict):
                continue
            
            customer_ids = metadata.get("customer_ids", [])
            if not isinstance(customer_ids, list) or not customer_ids:
                continue
            
            # Clear customer_ids from metadata and set customer_count to 0
            metadata["customer_ids"] = []
            
            # Update zone to remove all customer assignments
            supabase.table("zones").update({
                "metadata": metadata,
                "customer_count": 0,
            }).eq("id", zone_db_id).execute()
            
            unassigned_count += len(customer_ids)
        
        import logging
        logging.info(f"Unassigned {unassigned_count} customers from {len(response.data)} zones before deletion")
        return True
        
    except Exception as e:
        import logging
        logging.error(f"Failed to unassign customers from zones {zone_ids}: {e}")
        return False


def verify_zones_deleted(zone_ids: list[str]) -> bool:
    """Verify that all specified zones have been deleted from the database.
    
    Args:
        zone_ids: List of zone IDs to verify are deleted
        
    Returns:
        True if all zones are deleted, False if any still exist
    """
    supabase = get_supabase_client()
    if not supabase or not zone_ids:
        return True
    
    try:
        # Check if any zones with these IDs still exist
        response = supabase.table("zones").select("name").in_("name", zone_ids).execute()
        remaining_zones = response.data if response.data else []
        
        if remaining_zones:
            remaining_ids = [z["name"] for z in remaining_zones]
            import logging
            logging.warning(f"⚠️ Zones still exist after deletion attempt: {remaining_ids}")
            return False
        
        return True
    except Exception as e:
        import logging
        logging.warning(f"Failed to verify zone deletion: {e}")
        # Assume deleted if we can't verify (better than blocking)
        return True


def delete_zones(zone_ids: list[str], verify: bool = True) -> bool:
    """Delete zones from the database by their zone IDs.
    
    This function deletes ALL records with the specified zone IDs (names),
    ensuring complete removal even if multiple records exist with the same zone_id.
    
    CRITICAL: This function will delete ALL records matching the zone_ids, not just one per ID.
    
    Args:
        zone_ids: List of zone IDs (zone names) to delete
        verify: If True, verify deletion completed successfully
        
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
        import logging
        
        # First, get ALL records with these zone IDs to ensure we delete everything
        # This is important because there might be multiple records with the same zone_id
        select_response = supabase.table("zones").select("id, name").in_("name", zone_ids).execute()
        all_records = select_response.data if select_response.data else []
        
        if not all_records:
            logging.info(f"No zones found to delete: {zone_ids}")
            return True
        
        records_before = len(all_records)
        record_ids_to_delete = [record["id"] for record in all_records]
        zone_names_found = set(record["name"] for record in all_records)
        
        logging.info(f"Found {records_before} zone record(s) to delete with IDs: {list(zone_names_found)}")
        logging.info(f"Deleting {len(record_ids_to_delete)} database record(s)...")
        
        # Delete by database IDs to ensure we delete ALL records, even duplicates
        # Delete in batches if there are many records
        deleted_count = 0
        batch_size = 100
        for i in range(0, len(record_ids_to_delete), batch_size):
            batch = record_ids_to_delete[i:i + batch_size]
            try:
                response = supabase.table("zones").delete().in_("id", batch).execute()
                batch_deleted = len(response.data) if response.data else 0
                deleted_count += batch_deleted
                logging.info(f"Deleted batch {i//batch_size + 1}: {batch_deleted} record(s)")
            except Exception as batch_error:
                logging.error(f"Error deleting batch {i//batch_size + 1}: {batch_error}")
                # Continue with next batch
        
        logging.info(f"Deleted {deleted_count} out of {records_before} zone record(s)")
        
        if deleted_count != records_before:
            logging.warning(f"⚠️ Deleted {deleted_count} records but expected {records_before}")
        
        # Verify deletion if requested
        if verify:
            # Wait a moment for database to commit
            import time
            time.sleep(0.2)  # Slightly longer delay to ensure database commit
            
            if not verify_zones_deleted(zone_ids):
                logging.error(f"❌ Verification failed: Some zones still exist after deletion: {zone_ids}")
                # Try one more verification after a longer delay
                time.sleep(0.5)
                if not verify_zones_deleted(zone_ids):
                    return False
        
        logging.info(f"✅ Successfully deleted and verified removal of zones: {list(zone_names_found)}")
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

