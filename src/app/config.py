"""Application configuration and settings management."""

from pathlib import Path
from typing import Any, Literal, Optional

import json
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or defaults."""
    
    model_config = SettingsConfigDict(
        env_prefix="IZG_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    app_name: str = "Intelligent Zone Generator API"
    api_prefix: str = "/api"
    data_root: Path = Field(default=Path("data"), description="Root directory for static data files.")
    customer_file: Path = Field(
        default=Path("data/Easyterrritory_26831_29_oct_2025.CSV"),
        description="Master customer dataset.",
    )
    dc_locations_file: Path = Field(
        default=Path("data/dc_locations.xlsx"),
        description="Depot locations with latitude/longitude coordinates.",
    )
    osrm_base_url: Optional[str] = Field(
        default=None,
        description="Base URL for the OSRM routing service (e.g., http://localhost:5000).",
    )
    osrm_profile: Literal["driving", "driving-hgv"] = Field(
        default="driving",
        description="OSRM profile to use when computing travel times.",
    )
    osrm_max_retries: int = Field(default=3, ge=0)
    osrm_backoff_seconds: float = Field(default=1.0, ge=0.0)
    default_isochrones: tuple[int, ...] = Field(
        default=(15, 30, 45, 60),
        description="Default time thresholds (minutes) when generating isochrone zones.",
    )
    max_polar_sectors: int = Field(default=24, ge=1)
    min_polar_sectors: int = Field(default=4, ge=1)
    max_customers_per_route: int = Field(default=25, ge=1)
    min_customers_per_route: int = Field(default=10, ge=1)
    max_route_duration_minutes: int = Field(default=600, ge=1)
    max_distance_per_route_km: float = Field(default=50.0, ge=0.0)
    working_days: tuple[str, ...] = Field(default=("SUN", "MON", "TUE", "WED", "THU", "SAT"))
    solver_first_solution_strategy: str = Field(default="PATH_CHEAPEST_ARC")
    solver_local_search_metaheuristic: str = Field(default="GUIDED_LOCAL_SEARCH")
    solver_time_limit_seconds: int = Field(default=30, ge=0)
    frontend_allowed_origins: tuple[str, ...] = Field(
        default=(
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "https://f3b20235.intelligent-zone-generator.pages.dev",
            "https://zone.binder-tech.io"
        ),
        description="Permitted web origins for browser clients (CORS).",
    )

    # Supabase configuration
    supabase_url: Optional[str] = Field(
        default=None,
        description="Supabase project URL (e.g., https://xxx.supabase.co).",
    )
    supabase_key: Optional[str] = Field(
        default=None,
        description="Supabase service role key for backend operations.",
    )


    @field_validator("data_root", "customer_file", "dc_locations_file", mode="before")
    @classmethod
    def _expand_path(cls, value: Any) -> Path:
        path_value = value if isinstance(value, Path) else Path(str(value))
        return path_value.expanduser().resolve()
    
    @field_validator("frontend_allowed_origins", "working_days", mode="before")
    @classmethod
    def _parse_str_tuple_from_env(cls, value: Any) -> tuple[str, ...]:
        """Parse string tuple from environment variable (comma-separated or JSON array)."""
        if isinstance(value, tuple):
            return value
        if isinstance(value, list):
            return tuple(str(item) for item in value)
        if isinstance(value, str):
            # Try JSON first
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return tuple(str(item) for item in parsed)
            except (json.JSONDecodeError, TypeError):
                pass
            # Try comma-separated
            if "," in value:
                return tuple(item.strip() for item in value.split(",") if item.strip())
            # Single value
            if value.strip():
                return (value.strip(),)
        # Return empty tuple if value is None or empty
        return tuple()
    
    @field_validator("default_isochrones", mode="before")
    @classmethod
    def _parse_int_tuple_from_env(cls, value: Any) -> tuple[int, ...]:
        """Parse integer tuple from environment variable (comma-separated or JSON array)."""
        if isinstance(value, tuple):
            return value
        if isinstance(value, list):
            return tuple(int(item) for item in value)
        if isinstance(value, str):
            # Try JSON first
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return tuple(int(item) for item in parsed)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
            # Try comma-separated
            if "," in value:
                return tuple(int(item.strip()) for item in value.split(",") if item.strip())
            # Single value
            if value.strip():
                try:
                    return (int(value.strip()),)
                except ValueError:
                    return tuple()
        # Return empty tuple if value is None or empty
        return tuple()


settings = Settings()
