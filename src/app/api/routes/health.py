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
