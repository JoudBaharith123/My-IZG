"""Report/export manifest helpers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...config import settings

OUTPUT_ROOT = (settings.data_root / "outputs").resolve()

_TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"


def list_runs(
    *,
    run_type: Optional[str] = None,
    city: Optional[str] = None,
    zone: Optional[str] = None,
    limit: Optional[int] = None,
    search: Optional[str] = None,
) -> List[dict]:
    if not OUTPUT_ROOT.exists():
        return []

    normalized_search = _normalize(search) if search else None
    normalized_city = _normalize(city) if city else None
    normalized_zone = _normalize(zone) if zone else None
    normalized_run_type = _normalize(run_type) if run_type else None

    runs: List[dict] = []
    for run_dir in sorted((p for p in OUTPUT_ROOT.iterdir() if p.is_dir()), key=_sort_key, reverse=True):
        run_info = _build_run_summary(run_dir)
        if not run_info:
            continue

        if normalized_run_type and _normalize(run_info.get("run_type")) != normalized_run_type:
            continue
        if normalized_city and _normalize(run_info.get("city")) != normalized_city:
            continue
        if normalized_zone and _normalize(run_info.get("zone")) != normalized_zone:
            continue
        if normalized_search and not _matches_search(
            normalized_search,
            run_info.get("id"),
            run_info.get("city"),
            run_info.get("zone"),
            run_info.get("method"),
            run_info.get("author"),
            run_info.get("run_label"),
            " ".join(run_info.get("tags") or []),
        ):
            continue

        runs.append(run_info)
        if limit and len(runs) >= limit:
            break
    return runs


def list_export_files(
    *,
    run_type: Optional[str] = None,
    city: Optional[str] = None,
    zone: Optional[str] = None,
    file_type: Optional[str] = None,
    limit: Optional[int] = None,
    search: Optional[str] = None,
) -> List[dict]:
    if not OUTPUT_ROOT.exists():
        return []

    normalized_run_type = _normalize(run_type) if run_type else None
    normalized_city = _normalize(city) if city else None
    normalized_zone = _normalize(zone) if zone else None
    normalized_file_type = _normalize(file_type) if file_type else None
    normalized_search = _normalize(search) if search else None

    exports: List[dict] = []
    for run_dir in sorted((p for p in OUTPUT_ROOT.iterdir() if p.is_dir()), key=_sort_key, reverse=True):
        run_summary = _build_run_summary(run_dir)
        if not run_summary:
            continue
        if normalized_run_type and _normalize(run_summary.get("run_type")) != normalized_run_type:
            continue
        if normalized_city and _normalize(run_summary.get("city")) != normalized_city:
            continue
        if normalized_zone and _normalize(run_summary.get("zone")) != normalized_zone:
            continue

        for file_path in sorted(run_dir.glob("*")):
            if not file_path.is_file():
                continue
            export_info = _build_file_record(file_path, run_dir, run_summary)
            if normalized_file_type and _normalize(export_info.get("file_type")) != normalized_file_type:
                continue
            if normalized_search and not _matches_search(
                normalized_search,
                export_info.get("file_name"),
                export_info.get("description"),
                export_info.get("city"),
                export_info.get("zone"),
                export_info.get("method"),
                export_info.get("author"),
                export_info.get("run_label"),
                " ".join(export_info.get("tags") or []),
            ):
                continue
            exports.append(export_info)
            if limit and len(exports) >= limit:
                return exports
    return exports


def resolve_export_file(run_id: str, filename: str) -> Path:
    candidate = (OUTPUT_ROOT / run_id / filename).resolve()
    if not candidate.is_file():
        raise FileNotFoundError(filename)
    if OUTPUT_ROOT not in candidate.parents:
        raise FileNotFoundError(filename)
    return candidate


def _build_run_summary(run_dir: Path) -> Optional[dict]:
    name_parts = run_dir.name.split("_")
    if not name_parts:
        return None
    run_type = name_parts[0]
    timestamp = _parse_timestamp(name_parts[-1])
    summary_data = _load_summary(run_dir / "summary.json") or {}
    metadata = summary_data.get("metadata") if isinstance(summary_data.get("metadata"), dict) else {}

    base_info: Dict[str, Any] = {
        "id": run_dir.name,
        "run_type": run_type,
        "created_at": timestamp if timestamp else None,
        "status": _coerce_status(metadata),
        "method": summary_data.get("method"),
        "city": summary_data.get("city") or metadata.get("city"),
        "zone": summary_data.get("zone_id") or metadata.get("zone_id"),
        "author": metadata.get("author"),
        "run_label": metadata.get("run_label"),
        "tags": list(metadata.get("tags") or []),
        "notes": metadata.get("notes"),
    }

    if run_type == "zones":
        if not base_info["method"] and len(name_parts) > 2:
            base_info["method"] = "_".join(name_parts[1:-1])
        counts = summary_data.get("counts") or []
        base_info["zone_count"] = len(counts)
        base_info["route_count"] = 0
    elif run_type == "routes":
        if not base_info["zone"] and len(name_parts) > 2:
            base_info["zone"] = "_".join(name_parts[1:-1])
        plans = summary_data.get("plans") or []
        base_info["zone_count"] = 1
        base_info["route_count"] = len(plans)
    else:
        base_info["zone_count"] = summary_data.get("zone_count") or 0
        base_info["route_count"] = summary_data.get("route_count") or 0

    return base_info


def _build_file_record(file_path: Path, run_dir: Path, run_summary: dict) -> dict:
    created_at = run_summary.get("created_at")
    if not created_at:
        timestamp = _parse_timestamp(run_dir.name.split("_")[-1])
        created_at = timestamp if timestamp else None

    file_suffix = file_path.suffix[1:].upper() if file_path.suffix else ""
    description = _describe_file(file_path.name, run_summary)
    run_id = run_dir.name

    return {
        "id": f"{run_id}:{file_path.name}",
        "run_id": run_id,
        "run_type": run_summary.get("run_type"),
        "file_name": file_path.name,
        "file_type": file_suffix or "FILE",
        "size_bytes": file_path.stat().st_size,
        "created_at": created_at,
        "city": run_summary.get("city"),
        "zone": run_summary.get("zone"),
        "method": run_summary.get("method"),
        "author": run_summary.get("author"),
        "run_label": run_summary.get("run_label"),
        "tags": list(run_summary.get("tags") or []),
        "notes": run_summary.get("notes"),
        "description": description,
        "download_path": f"/api/reports/exports/{run_id}/{file_path.name}",
    }


def _load_summary(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError:
        return None


def _parse_timestamp(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value, _TIMESTAMP_FORMAT)
    except ValueError:
        return None


def _coerce_status(metadata: Any) -> str:
    if isinstance(metadata, dict):
        status = metadata.get("status")
        if isinstance(status, str) and status.strip():
            return status
    return "complete"


def _describe_file(filename: str, run_summary: dict) -> str:
    lower = filename.lower()
    run_type = run_summary.get("run_type")
    if lower == "summary.json":
        if run_type == "zones":
            return "Zone summary output"
        if run_type == "routes":
            return "Route optimization summary"
        return "Run summary"
    if lower == "assignments.csv":
        if run_type == "zones":
            return "Customer-to-zone assignments"
        if run_type == "routes":
            return "Customer-to-route assignments"
    if lower.endswith(".csv"):
        return "CSV export"
    if lower.endswith(".json"):
        return "JSON export"
    return "Export file"


def _sort_key(path: Path) -> float:
    timestamp = _parse_timestamp(path.name.split("_")[-1])
    if timestamp:
        return timestamp.timestamp()
    return path.stat().st_mtime


def _normalize(value: Optional[str]) -> str:
    return value.lower().strip() if isinstance(value, str) else ""


def _matches_search(search: str, *values: Optional[str]) -> bool:
    for value in values:
        if isinstance(value, str) and search in value.lower():
            return True
    return False
