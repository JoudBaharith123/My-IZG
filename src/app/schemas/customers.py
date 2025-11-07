"""Customer-facing API schemas."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel


class TopZoneModel(BaseModel):
    code: str
    ratio: float
    customers: int


class LastUploadModel(BaseModel):
    fileName: str
    sizeBytes: int | None = None
    modifiedAt: str | None = None


class CustomerStatsResponse(BaseModel):
    totalCustomers: int
    unassignedPercentage: float
    zonesDetected: int
    topZones: list[TopZoneModel]
    lastUpload: LastUploadModel


class CitySummaryModel(BaseModel):
    name: str
    customers: int


class ZoneSummaryModel(BaseModel):
    zone: str
    city: str | None = None
    customers: int


class CustomerLocationModel(BaseModel):
    customer_id: str
    customer_name: str | None = None
    city: str | None = None
    zone: str | None = None
    latitude: float
    longitude: float


class CustomerLocationsResponse(BaseModel):
    items: List[CustomerLocationModel]
    page: int
    page_size: int
    total: int
    has_next_page: bool


class IssueGroup(BaseModel):
    count: int
    sample: List[dict] | None = None
    duplicates: List[dict] | None = None


class CustomerValidationResponse(BaseModel):
    totalRecords: int
    issues: dict[str, IssueGroup]
