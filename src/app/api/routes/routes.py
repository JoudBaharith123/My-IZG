"""Routing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...schemas.routing import RoutingRequest, RoutingResponse
from ...services.routing.service import optimize_routes
from ...persistence.database import update_route_customer, remove_customer_from_route

router = APIRouter(prefix="/routes", tags=["routes"])


class RemoveCustomerRequest(BaseModel):
    zone_id: str
    route_id: str
    customer_id: str


class TransferCustomerRequest(BaseModel):
    zone_id: str
    from_route_id: str
    to_route_id: str
    customer_id: str


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


@router.post("/remove-customer", status_code=status.HTTP_200_OK)
def remove_customer(payload: RemoveCustomerRequest) -> dict:
    """Remove a customer from a route."""
    try:
        success = remove_customer_from_route(
            zone_id=payload.zone_id,
            route_id=payload.route_id,
            customer_id=payload.customer_id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer {payload.customer_id} not found in route {payload.route_id}"
            )
        return {
            "success": True,
            "message": f"Customer {payload.customer_id} removed from route {payload.route_id}"
        }
    except HTTPException:
        raise
    except Exception as exc:
        import logging
        logging.exception(f"Error removing customer from route: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove customer from route: {str(exc)}"
        ) from exc


@router.post("/transfer-customer", status_code=status.HTTP_200_OK)
def transfer_customer(payload: TransferCustomerRequest) -> dict:
    """Transfer a customer from one route to another."""
    try:
        success = update_route_customer(
            zone_id=payload.zone_id,
            from_route_id=payload.from_route_id,
            to_route_id=payload.to_route_id,
            customer_id=payload.customer_id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed to transfer customer {payload.customer_id} from {payload.from_route_id} to {payload.to_route_id}"
            )
        return {
            "success": True,
            "message": f"Customer {payload.customer_id} transferred from {payload.from_route_id} to {payload.to_route_id}"
        }
    except HTTPException:
        raise
    except Exception as exc:
        import logging
        logging.exception(f"Error transferring customer: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transfer customer: {str(exc)}"
        ) from exc
