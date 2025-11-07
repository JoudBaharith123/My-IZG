"""Health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from ...services.routing.osrm_client import check_health as osrm_health_check

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_root() -> dict:
    return {"status": "ok"}


@router.get("/health/osrm", status_code=status.HTTP_200_OK)
def health_osrm() -> dict:
    status_flag = osrm_health_check()
    return {"service": "osrm", "healthy": status_flag}
