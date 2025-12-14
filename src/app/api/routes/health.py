"""Health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status, HTTPException

from ...services.routing.osrm_client import check_health as osrm_health_check
from ...data.dc_repository import get_depots, _load_depots_from_database, _load_depots_from_file, _sync_depots_to_database

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_root() -> dict:
    return {"status": "ok"}


@router.get("/health/osrm", status_code=status.HTTP_200_OK)
def health_osrm() -> dict:
    status_flag = osrm_health_check()
    return {"service": "osrm", "healthy": status_flag}


@router.post("/health/sync-depots", status_code=status.HTTP_200_OK)
def sync_depots() -> dict:
    """Manually sync depots from Excel file to database."""
    try:
        # Load from file
        file_depots = _load_depots_from_file()
        
        # Sync to database
        _sync_depots_to_database(file_depots)
        
        # Check database after sync
        db_depots = _load_depots_from_database()
        
        return {
            "status": "success",
            "file_depots": len(file_depots),
            "database_depots": len(db_depots) if db_depots else 0,
            "message": f"Synced {len(file_depots)} depots to database" if db_depots else "Database not configured or sync failed",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync depots: {str(exc)}"
        ) from exc


@router.get("/health/database", status_code=status.HTTP_200_OK)
def check_database() -> dict:
    """Check database connection and zone storage status."""
    from ...db.supabase import get_supabase_client
    from ...persistence.database import get_zones_from_database
    
    supabase = get_supabase_client()
    if not supabase:
        return {
            "configured": False,
            "message": "Supabase not configured. Set IZG_SUPABASE_URL and IZG_SUPABASE_KEY environment variables.",
            "zones_count": 0,
        }
    
    try:
        # Try to get zones from database
        zones = get_zones_from_database()
        
        # Try to check if zones table exists
        try:
            test_query = supabase.table("zones").select("id", count="exact").limit(1).execute()
            table_exists = True
        except Exception:
            table_exists = False
        
        return {
            "configured": True,
            "connected": True,
            "zones_table_exists": table_exists,
            "zones_count": len(zones),
            "message": f"Database connected. Found {len(zones)} zones in database." if table_exists else "Database connected but zones table may not exist.",
        }
    except Exception as exc:
        return {
            "configured": True,
            "connected": False,
            "error": str(exc),
            "message": f"Database connection error: {exc}",
        }
