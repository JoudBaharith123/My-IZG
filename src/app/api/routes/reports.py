"""Report manifest endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import FileResponse

from ...schemas.reports import ReportExportModel, ReportRunModel
from ...services.reports import list_export_files, list_runs, resolve_export_file

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/exports", response_model=list[ReportExportModel])
def get_report_exports(
  run_type: str | None = Query(default=None, description="Filter by run type (e.g. zones, routes)"),
  city: str | None = Query(default=None, description="Filter by city"),
  zone: str | None = Query(default=None, description="Filter by zone"),
  file_type: str | None = Query(default=None, description="Filter by file type (CSV, JSON, etc.)"),
  search: str | None = Query(default=None, description="Case-insensitive search across name/description/meta"),
  limit: int | None = Query(default=None, gt=0, description="Maximum number of exports to return"),
) -> list[ReportExportModel]:
  exports = list_export_files(
    run_type=run_type,
    city=city,
    zone=zone,
    file_type=file_type,
    search=search,
    limit=limit,
  )
  return [ReportExportModel.model_validate(item) for item in exports]


@router.get("/runs", response_model=list[ReportRunModel])
def get_report_runs(
  run_type: str | None = Query(default=None, description="Filter by run type"),
  city: str | None = Query(default=None, description="Filter by city"),
  zone: str | None = Query(default=None, description="Filter by zone"),
  search: str | None = Query(default=None, description="Search by run metadata"),
  limit: int | None = Query(default=None, gt=0, description="Maximum number of runs to return"),
) -> list[ReportRunModel]:
  runs = list_runs(run_type=run_type, city=city, zone=zone, limit=limit, search=search)
  return [ReportRunModel.model_validate(item) for item in runs]


@router.get(
  "/exports/{run_id}/{file_name:path}",
  response_class=FileResponse,
  status_code=status.HTTP_200_OK,
)
def download_export_file(
  run_id: str = Path(..., description="Run directory identifier"),
  file_name: str = Path(..., description="File name within the run directory"),
) -> FileResponse:
  try:
    file_path = resolve_export_file(run_id, file_name)
  except FileNotFoundError as exc:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

  # Determine media type based on file extension
  media_type = _get_media_type(file_path)

  return FileResponse(
    path=file_path,
    filename=file_path.name,
    media_type=media_type,
    headers={"Content-Disposition": f'attachment; filename="{file_path.name}"'},
  )


def _get_media_type(file_path) -> str:
  """Determine MIME type based on file extension."""
  suffix = file_path.suffix.lower()
  mime_types = {
    ".csv": "text/csv",
    ".json": "application/json",
    ".geojson": "application/geo+json",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".zip": "application/zip",
  }
  return mime_types.get(suffix, "application/octet-stream")
