"""API routes for zone generation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ...schemas.zoning import ZoningRequest, ZoningResponse
from ...services.zoning.service import process_zoning_request

router = APIRouter(prefix="/zones", tags=["zones"])


@router.post("/generate", response_model=ZoningResponse, status_code=status.HTTP_200_OK)
def generate_zones(payload: ZoningRequest) -> ZoningResponse:
    try:
        return process_zoning_request(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
