# Development Environment Setup

## Prerequisites
- Docker Desktop or Docker Engine 20.10+
- Docker Compose v2+
- Optional: Python 3.11 with `uvicorn` for running the API locally without containers.

## Quick Start

1. **Prepare OSRM data**  
   Download the Saudi Arabia extract (or your target region) from [Geofabrik](https://download.geofabrik.de/asia/saudi-arabia-latest.osm.pbf) and preprocess it:
   ```bash
   mkdir -p osrm
   docker run --rm -t -v "${PWD}/osrm:/data" ghcr.io/project-osrm/osrm-backend:latest \
     osrm-extract -p /opt/car.lua /data/saudi-arabia-latest.osm.pbf
   docker run --rm -t -v "${PWD}/osrm:/data" ghcr.io/project-osrm/osrm-backend:latest \
     osrm-partition /data/saudi-arabia-latest.osrm
   docker run --rm -t -v "${PWD}/osrm:/data" ghcr.io/project-osrm/osrm-backend:latest \
     osrm-customize /data/saudi-arabia-latest.osrm
   ```

2. **Launch services**
   ```bash
   docker compose up --build
   ```
   - API: http://localhost:8000
   - FastAPI docs: http://localhost:8000/docs
   - OSRM: http://localhost:5000

3. **Environment variables**  
   Copy `.env.example` to `.env` to override defaults. Values are automatically picked up by the FastAPI container when provided.

## Local Python Workflow (optional)

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run the API:
   ```bash
   uvicorn src.app.main:app --reload
   ```
   Ensure `IZG_OSRM_BASE_URL` is set (or leave unset to use haversine fallback).

## Data & Outputs
- Customer master and depot files reside in `data/`.
- Solver outputs are expected under `outputs/<run-id>/` (create as needed).
- When using Docker, the repository folder is mounted into the container, so edits reflect immediately.

## Troubleshooting
- **OSRM healthcheck fails**: confirm `.osrm` files exist in the `osrm/` directory and match the command arguments.
- **Port conflicts**: adjust `docker-compose.yml` port mappings.
- **Dependency issues**: rebuild the API image (`docker compose build api`) after updating `requirements.txt`.
