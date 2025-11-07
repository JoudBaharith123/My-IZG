"""File-based persistence helpers for zone and route outputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import settings


class FileStorage:
    """Thin wrapper around the data root for storing JSON and CSV outputs."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or settings.data_root).resolve()
        self.output_root = self.root / "outputs"
        self.output_root.mkdir(parents=True, exist_ok=True)

    def make_run_directory(self, prefix: str = "zone") -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = self.output_root / f"{prefix}_{timestamp}"
        path.mkdir(parents=True, exist_ok=False)
        return path

    def write_json(self, path: Path, data: Any, *, indent: int = 2) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=indent)

    def write_csv(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            handle.write(content)

    def write_bytes(self, path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            handle.write(payload)
