"""Routing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ...schemas.routing import RoutingRequest, RoutingResponse
from ...services.routing.service import optimize_routes

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("/optimize", response_model=RoutingResponse, status_code=status.HTTP_200_OK)
def optimize(payload: RoutingRequest) -> RoutingResponse:
    try:
        return optimize_routes(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        # Log the full error for debugging
        import logging
        logging.exception(f"Error optimizing routes: {exc}")
        # Return a user-friendly error message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize routes: {str(exc)}"
        ) from exc
