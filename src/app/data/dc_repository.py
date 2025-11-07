"""Depot data loader backed by the dc_locations.xlsx spreadsheet."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator

from openpyxl import load_workbook

from ..config import settings
from ..models.domain import Depot


def _normalize_dc_name(name: str) -> str:
    return name.strip()


def get_depots(source: Path | None = None) -> tuple[Depot, ...]:
    workbook_path = (source or settings.dc_locations_file)
    if not workbook_path.exists():
        raise FileNotFoundError(f"Depot workbook not found: {workbook_path}")

    wb = load_workbook(workbook_path, data_only=True, read_only=True)
    sheet = wb.active
    rows = sheet.iter_rows(min_row=1, values_only=True)
    header = next(rows, None)
    if header is None:
        raise ValueError(f"Depot workbook '{workbook_path}' is empty.")

    header_map = {name: idx for idx, name in enumerate(header)}
    missing_columns = {"DC", "Latitude", "Longitude"} - set(header_map)
    if missing_columns:
        raise ValueError(f"Depot workbook missing columns: {', '.join(sorted(missing_columns))}")

    depots: list[Depot] = []
    for row in rows:
        dc_value = row[header_map["DC"]]
        lat_value = row[header_map["Latitude"]]
        lon_value = row[header_map["Longitude"]]
        if not dc_value:
            continue
        depots.append(
            Depot(
                code=_normalize_dc_name(str(dc_value)),
                latitude=float(lat_value),
                longitude=float(lon_value),
            )
        )
    return tuple(depots)
