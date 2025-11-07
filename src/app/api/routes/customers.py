"""Customer dataset endpoints."""

from __future__ import annotations

from typing import List
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO
import csv

from fastapi import APIRouter, Query, status, UploadFile, File, HTTPException
from openpyxl import load_workbook

from ...schemas.customers import (
    CitySummaryModel,
    CustomerLocationModel,
    CustomerLocationsResponse,
    CustomerStatsResponse,
    CustomerValidationResponse,
    ZoneSummaryModel,
)
from ...services.customers import (
    analyze_customer_issues,
    compute_customer_stats,
    compute_zone_summaries,
    list_customer_cities,
    list_customer_locations,
)
from ...data.customers_repository import set_active_customer_file
from ...config import settings

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/stats", response_model=CustomerStatsResponse, status_code=status.HTTP_200_OK)
def get_customer_stats() -> CustomerStatsResponse:
    return CustomerStatsResponse(**compute_customer_stats())


@router.get("/cities", response_model=List[CitySummaryModel], status_code=status.HTTP_200_OK)
def list_cities(limit: int | None = Query(default=None, ge=1, le=500)) -> List[CitySummaryModel]:
    city_list = list_customer_cities(limit=limit)
    return [CitySummaryModel(**entry) for entry in city_list]


@router.get("/zones", response_model=List[ZoneSummaryModel], status_code=status.HTTP_200_OK)
def list_customer_zones(city: str | None = Query(default=None, description="Optional city filter")) -> List[ZoneSummaryModel]:
    return [ZoneSummaryModel(**entry) for entry in compute_zone_summaries(city)]


@router.get("/locations", response_model=CustomerLocationsResponse, status_code=status.HTTP_200_OK)
def get_customer_locations(
    city: str | None = Query(default=None, description="Optional city or area filter"),
    zone: str | None = Query(default=None, description="Optional zone filter"),
    page: int = Query(default=1, ge=1, description="1-based page index for pagination"),
    page_size: int = Query(default=1000, ge=100, le=5000, description="Maximum number of records per page"),
    limit: int | None = Query(
        default=None,
        ge=1,
        le=10_000,
        description="Optional hard cap on returned records (overrides page_size when smaller).",
    ),
) -> CustomerLocationsResponse:
    effective_page_size = min(page_size, limit) if limit else page_size
    offset = (page - 1) * effective_page_size
    items, total = list_customer_locations(city=city, zone=zone, offset=offset, limit=effective_page_size)
    has_next_page = (offset + len(items)) < total
    return CustomerLocationsResponse(
        items=[CustomerLocationModel(**record) for record in items],
        page=page,
        page_size=effective_page_size,
        total=total,
        has_next_page=has_next_page,
    )


@router.get("/validation", response_model=CustomerValidationResponse, status_code=status.HTTP_200_OK)
def validate_customer_dataset() -> CustomerValidationResponse:
    return CustomerValidationResponse.model_validate(analyze_customer_issues())


@router.post("/upload", response_model=CustomerStatsResponse, status_code=status.HTTP_201_CREATED)
async def upload_customer_dataset(file: UploadFile = File(...)) -> CustomerStatsResponse:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only .csv and .xlsx files are supported.")

    uploads_dir = settings.data_root / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    destination = uploads_dir / f"customers_{timestamp}.csv"

    if suffix == ".csv":
        contents = await file.read()
        destination.write_bytes(contents)
    else:
        workbook = load_workbook(filename=BytesIO(await file.read()), read_only=True, data_only=True)
        worksheet = workbook.active
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            for row in worksheet.iter_rows(values_only=True):
                writer.writerow(["" if cell is None else cell for cell in row])

    set_active_customer_file(destination.resolve())
    stats = compute_customer_stats()
    return CustomerStatsResponse(**stats)
