# Intelligent Zone Generator Backend

## Overview

This backend exposes a FastAPI service that ingests customer master data and generates zone assignments using multiple strategies:

- **Polar sectors** â€“ divides the plane around a depot into angular sectors.
- **Isochrones** â€“ buckets customers by travel-time rings from the depot (OSRM-backed with a haversine fallback).
- **Clustering** â€“ applies K-Means on customer coordinates with workload metadata.
- **Manual polygons** â€“ accepts user drawn polygons and assigns customers inside each shape.

## Key Modules

- `src/app/main.py`: FastAPI application factory.
- `src/app/api/routes/zoning.py`: `POST /api/zones/generate` endpoint.
- `src/app/api/routes/customers.py`: `GET /api/customers/stats` endpoint.
- `src/app/services/zoning/`: strategy implementations and dispatcher.
- `src/app/services/customers/stats.py`: dataset statistics helpers.
- `src/app/data/`: loaders for the customer CSV and depot workbook.
- `src/app/schemas/zoning.py`: Pydantic request/response contracts.

## Endpoint Contract

`POST /api/zones/generate`

Request body (example for Jeddah polar zoning):

```json
{
  "city": "Jeddah",
  "method": "polar",
  "target_zones": 6,
  "rotation_offset": 10.0,
  "balance": true,
  "balance_tolerance": 0.2
}
```

Manual polygon request:

```json
{
  "city": "Jeddah",
  "method": "manual",
  "polygons": [
    {"zone_id": "JED_A", "coordinates": [[21.5, 39.1], [21.6, 39.2], [21.55, 39.3]]}
  ]
}
```

Response body:

```json
{
  "city": "Jeddah",
  "method": "polar",
  "assignments": {"CS000001": "JED001", "...": "..."},
  "counts": [{"zone_id": "JED001", "customer_count": 120}],
  "metadata": {"strategy": "polar", "sector_size_degrees": 60.0}
}
```

`GET /api/customers/stats`

Sample response:

```json
{
  "totalCustomers": 26831,
  "unassignedPercentage": 16.2,
  "zonesDetected": 44,
  "topZones": [
    {"code": "JED002", "ratio": 0.08, "customers": 1886},
    {"code": "QAS001", "ratio": 0.06, "customers": 1374},
    {"code": "JED001", "ratio": 0.05, "customers": 1163}
  ]
}
```

`GET /api/customers/zones?city=Jeddah`

```json
[
  {"zone": "JED001", "city": "Jeddah", "customers": 1163},
  {"zone": "JED002", "city": "Jeddah", "customers": 1886},
  {"zone": "JED003", "city": "Jeddah", "customers": 942}
]
```

`GET /api/customers/validation`

Returns dataset issue summary (missing coordinates, duplicate IDs, finance clearance) for the Upload & Validate workflow.


`GET /api/reports/exports`

Returns manifest of export files located under `data/outputs/*`.

`GET /api/reports/runs`

Returns aggregated metadata for each run directory (type, city, zone counts, status, author if present).

`GET /api/reports/exports/{run_id}/{file_name}`

Streams a specific export file for download (supports CSV/JSON artifacts produced by zoning/routing runs).

## Running Locally

```bash
poetry install
poetry run uvicorn src.app.main:app --reload
```

Environment variables (prefix `IZG_`) let you override file paths and OSRM settings; see `src/app/config.py`.

## Notes & Next Steps

`POST /api/routes/optimize`

Request body (example):

```json
{
  "city": "Jeddah",
  "zone_id": "JED001",
  "customer_ids": ["CS000001", "CS000010"],
  "constraints": {
    "max_customers_per_route": 25,
    "max_route_duration_minutes": 600
  }
}
```

Response body:

```json
{
  "zone_id": "JED001",
  "metadata": {"status": "optimal", "vehicles": 2},
  "plans": [
    {
      "route_id": "JED001_R01",
      "day": "SUN",
      "total_distance_km": 42.1,
      "total_duration_min": 320.5,
      "customer_count": 20,
      "constraint_violations": {},
      "stops": [
        {"customer_id": "CS000001", "sequence": 1, "arrival_min": 60, "distance_from_prev_km": 5.2}
      ]
    }
  ]
}
```

- Isochrone strategy will call `IZG_OSRM_BASE_URL` if provided; otherwise it estimates travel time using haversine distance and 40â€¯km/h speed.
- Clustering strategy reports zone counts and highlights workloads breaching the configured tolerance.
- Manual strategy returns customer IDs left unassigned for follow-up adjustments.
- Route optimization persists JSON/CSV outputs under `data/outputs/routes_<zone>_<timestamp>/` and requires a reachable OSRM base URL.
- Hook these services into the forthcoming UI by wiring the same endpoint and supplying the user-chosen parameters.
- Health endpoints: `/health` (API), `/health/osrm` (OSRM connectivity check returning `{ "service": "osrm", "healthy": bool }`).

