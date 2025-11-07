# Data & Constraints Audit (2025-10-29)

## 1. Dataset Inventory

| Dataset | Location | Format | Notes |
| --- | --- | --- | --- |
| Customer Master | `data/Easyterrritory_26831_29_oct_2025.CSV` | CSV (UTF-8, quoted) | 26,831 records, 45 distinct zone codes, 4,351 customers without zone assignment (`Zone = ""`). 17,139 records lack city name (stored as `UNSPECIFIED`). |
| Depot Locations | `data/dc_locations.xlsx` | Excel (XLSX) | 13 distribution centers with latitude/longitude. Codes include spaced names (e.g., `KHAMES MUSHAIT`)—lookup normalizes compact/3-char aliases. |
| Legacy Zone Extracts | `data/zones/zone_<CODE>.csv` | CSV | Generated during discovery; mirrors customer master schema filtered per zone. Includes `zone_UNASSIGNED.csv` for customers without legacy zone. |

> Outstanding: confirm availability of historical route assignments, manual polygon shapefiles, or any ancillary operational datasets (e.g., revenue, visit duration) referenced in spec.

## 2. Coordinate Quality Assessment

- No missing lat/long values detected in customer master (`missing_coords = 0`).
- 170 customer records fall outside Saudi Arabia bounds (16–32°N, 34–56°E). Sample anomalies include:
  - `CS000001`: (11.0, -55.0) with blank zone
  - Multiple entries at (0.0, 0.0) across Jeddah customers
  - Various lat/lon pairs with obvious typos (`1.23`, `1.24`, etc.)
- `Geocode Quality` column is mostly empty (`UNSPECIFIED` for 26,830 rows, `failed` for 1 row) → no reliable precision indicator.

> Actions: flag out-of-bounds records for correction or exclusion prior to zoning. Determine whether geocode quality can be sourced from upstream system.

## 3. File Format Requirements

- **Inputs (current):** Customer CSV, Depot XLSX. Manual polygon import not available yet; expect GeoJSON or drawing tool output.
- **Inputs (future / to confirm):** Excel/CSV templates for bulk uploads, GeoJSON for existing polygon zones, optional OSRM table cache.
- **Outputs (from spec):** `customers_with_routes.csv`, `route_metrics.csv`, `route_sequences.csv`, GeoJSON exports, PDF reports.

> Need template definitions and column contracts for planned exports and reports; align with reporting team.

## 4. OSRM Coverage & Configuration

- Backend currently uses haversine fallback because `IZG_OSRM_BASE_URL` is unset.
- Depot list spans major Saudi regions; ensure OSRM extract covers national road network (likely driving profile).
- Pending details:
  - OSRM hosting environment (local Docker vs shared service)
  - Update cadence for map data
  - SLA/health monitoring expectations
  - Any need for custom profiles (e.g., truck restrictions)

## 5. Business Rules & Constraints (from spec – awaiting confirmation)

| Category | Parameter | Value / Status |
| --- | --- | --- |
| Zone creation | Min customers per zone | 10 (warning if below) |
| Zone creation | Max customers per zone | 1000 (enforced) |
| Polar sectors | Sector count | 4–24; default 12 |
| Isochrones | Time bands | 15/30/45/60 minutes (OSRM-driven) |
| Clustering | Balance tolerance | 20% variance target |
| Route constraints (hard) | Max customers per route | 25 |
| Route constraints (hard) | Max duration | 600 minutes |
| Route constraints (soft) | Max distance | 50 km (60 km Riyadh override) |
| Route constraints (soft) | Min customers per route | 10 |
| Solver strategy | OR-Tools | First solution `PATH_CHEAPEST_ARC`, metaheuristic `GUIDED_LOCAL_SEARCH`, 30s time limit |
| Working days | Active days | SUN–THU, SAT (FRI off) |

> Needs confirmation with operations:
> - Whether min/max customer caps per zone/route remain valid for all areas.
> - Any additional balancing metrics (revenue, time) thresholds.
> - Override policies for constraint violations and approval workflow.

## 6. Open Questions / Next Steps

1. Gather supplementary datasets (routes history, performance metrics, revenue) if required for balancing.
2. Decide how to cleanse or exclude geospatial anomalies prior to solver runs.
3. Confirm OSRM deployment plan and whether to preload travel-time matrices.
4. Validate business rules with stakeholders; capture in PRD acceptance criteria.
5. Produce manual validation test cases for each zoning method once data quality issues are addressed.
