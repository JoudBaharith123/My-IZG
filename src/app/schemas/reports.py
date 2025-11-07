"""Report manifest API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ReportExportModel(BaseModel):
  id: str
  run_id: str = Field(..., alias='runId')
  run_type: str = Field(..., alias='runType')
  file_name: str = Field(..., alias='fileName')
  file_type: str = Field(..., alias='fileType')
  size_bytes: int = Field(..., alias='sizeBytes')
  created_at: Optional[datetime] = Field(None, alias='createdAt')
  city: Optional[str] = None
  zone: Optional[str] = None
  method: Optional[str] = None
  author: Optional[str] = None
  run_label: Optional[str] = Field(None, alias='runLabel')
  tags: Optional[List[str]] = None
  notes: Optional[str] = None
  description: Optional[str] = None
  download_path: str = Field(..., alias='downloadPath')

  class Config:
    populate_by_name = True
    json_encoders = {datetime: lambda dt: dt.isoformat()}


class ReportRunModel(BaseModel):
  id: str
  run_type: str = Field(..., alias='runType')
  created_at: Optional[datetime] = Field(None, alias='createdAt')
  city: Optional[str] = None
  zone: Optional[str] = None
  method: Optional[str] = None
  author: Optional[str] = None
  run_label: Optional[str] = Field(None, alias='runLabel')
  tags: Optional[List[str]] = None
  notes: Optional[str] = None
  zone_count: int = Field(0, alias='zoneCount')
  route_count: int = Field(0, alias='routeCount')
  status: str

  class Config:
    populate_by_name = True
    json_encoders = {datetime: lambda dt: dt.isoformat()}
