"""Routing request/response schemas."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RoutingConstraints(BaseModel):
    max_customers_per_route: Optional[int] = Field(None, ge=1)
    min_customers_per_route: Optional[int] = Field(None, ge=0)
    max_route_duration_minutes: Optional[int] = Field(None, ge=1)
    max_distance_per_route_km: Optional[float] = Field(None, ge=0)


class RouteAssignment(BaseModel):
    """Manual assignment of customers to a specific route."""
    route_id: str = Field(..., description="Route identifier (e.g., 'Route_1', 'Route_2')")
    day: str = Field(..., description="Day of week for this route (e.g., 'MON', 'TUE')")
    customer_ids: List[str] = Field(..., description="List of customer IDs assigned to this route")


class RoutingRequest(BaseModel):
    city: str
    zone_id: str
    customer_ids: Optional[List[str]] = None
    constraints: Optional[RoutingConstraints] = None
    route_assignments: Optional[List[RouteAssignment]] = Field(
        default=None,
        description="Pre-assigned routes with customers. If provided, only sequence will be optimized, not assignment."
    )
    start_from_depot: bool = Field(
        default=True,
        description="If True, routes start from DC/depot. If False, routes start from the first customer."
    )
    persist: bool = True
    requested_by: Optional[str] = Field(default=None, description="Person or system requesting the run.")
    run_label: Optional[str] = Field(default=None, description="Friendly name for persisted outputs.")
    tags: Optional[List[str]] = Field(default=None, description="Tags to associate with the run.")
    notes: Optional[str] = Field(default=None, description="Free-form notes captured with the run.")


class RouteStopModel(BaseModel):
    customer_id: str
    sequence: int
    arrival_min: float
    distance_from_prev_km: float


class RoutePlanModel(BaseModel):
    route_id: str
    day: str
    total_distance_km: float
    total_duration_min: float
    customer_count: int
    constraint_violations: Dict[str, float]
    stops: List[RouteStopModel]


class RoutingResponse(BaseModel):
    zone_id: str
    metadata: dict
    plans: List[RoutePlanModel]
