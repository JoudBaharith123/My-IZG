"""Pydantic request/response models for zoning endpoints."""

from __future__ import annotations

from typing import Literal, Optional, Sequence

from pydantic import BaseModel, Field, field_validator


class ManualPolygon(BaseModel):
    zone_id: str
    coordinates: Sequence[tuple[float, float]]


class ZoningRequest(BaseModel):
    city: str = Field(..., description="City to generate zones for.")
    method: Literal["polar", "isochrone", "clustering", "manual"]
    target_zones: Optional[int] = Field(None, description="Desired number of zones (where applicable).")
    rotation_offset: float = Field(0.0, description="Rotation offset for polar sector zoning.")
    thresholds: Optional[Sequence[int]] = Field(
        default=None,
        description="Time thresholds (minutes) for isochrone zoning.",
    )
    max_customers_per_zone: Optional[int] = Field(
        default=None, description="Upper bound for customers per zone (clustering)."
    )
    polygons: Optional[Sequence[ManualPolygon]] = Field(default=None, description="Manual zoning polygons.")
    balance: bool = Field(default=False, description="Apply workload balancing across zones after generation.")
    balance_tolerance: float = Field(default=0.2, ge=0.0, description="Allowed variance when balancing zones.")
    persist: bool = Field(default=True, description="Whether to persist outputs to files.")
    requested_by: Optional[str] = Field(default=None, description="Person or system requesting the run.")
    run_label: Optional[str] = Field(default=None, description="Friendly name for persisted outputs.")
    tags: Optional[Sequence[str]] = Field(default=None, description="Tags to associate with the run.")
    notes: Optional[str] = Field(default=None, description="Free-form notes captured with the run.")

    @field_validator("target_zones")
    @classmethod
    def validate_target_zones(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 1:
            raise ValueError("target_zones must be >= 1")
        return value


class ZoneCount(BaseModel):
    zone_id: str
    customer_count: int


class ZoningResponse(BaseModel):
    city: str
    method: str
    assignments: dict[str, str]
    counts: list[ZoneCount]
    metadata: dict
