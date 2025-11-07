# Infrastructure Alignment Notes (2025-10-29)

## Current Environment (from `.codex/infrastructure.md`)
- **VM 1 – route-cv-ocr (149.36.0.182)** hosts existing logistics services:
  - OSRM Engine on port 5000 (with proxy on 5010).
  - Legacy Zone Calculator on 8081, Dynamic Routing on 8080, routing proxy on 8090.
  - CV/OCR GPU services on 8082/8083.
  - Prometheus on 9090 (Grafana planned).
  - Data stored under `/mnt/ephemeral/data`.
- **VM 2 – ruyah-llm-h100 (38.80.122.68)** dedicated to Ruyah LLM stack (unused for IZG v1).

## Implications for Intelligent Zone Generator
1. **OSRM Integration**
   - Reuse the existing OSRM engine (port 5000) instead of deploying a new container.
   - API configuration: set `IZG_OSRM_BASE_URL=http://149.36.0.182:5000` in production environment.
   - Ensure health checks target OSRM Proxy (5010) if required by ops runbooks.

2. **Service Placement**
   - Deploy IZG FastAPI service on VM 1 under `/opt/logistics-ai-platform/services/06-izg-backend/` to align with current structure.
   - Assign a free port (recommend 8084) to avoid clashes with existing services (8080–8083 in use).
   - Route external access via Nginx or existing proxy layer once integrated.

3. **Data & Storage**
   - Mount `/mnt/ephemeral/data` for customer inputs/outputs (`uploads/`, `outputs/izg/`).
   - Coordinate with ops to ensure nightly backup scripts include the IZG output directory.
   - Plan for Git-based deployment: clone `Intelligent_zone_generator` repo under `/opt/logistics-ai-platform/services/06-izg-backend/`.

4. **Deployment Workflow**
   - Use Docker image built from project `Dockerfile` (see `docs/ENVIRONMENT_SETUP.md`); create systemd service or container orchestrator entry to match existing practice.
   - Update `.codex/infrastructure.md` once ports and directory paths are finalized during deployment.
   - Leverage existing monitoring stack (Prometheus/Grafana) by exposing `/health`, `/health/osrm`, and future metrics endpoints.

5. **Local Developer Setup**
   - Developers using local OSRM (`\\wsl.localhost\Ubuntu\root\osrm-setup`) should start that service before running the API.
   - Dockerized OSRM remains optional via `docker-compose.yml` for teammates without local setups.

## Outstanding Items
- Confirm with ops whether legacy Zone Calculator (8081) will be retired or run alongside IZG; plan cutover strategy accordingly.
- Assign responsible owner for updating VM firewall rules if exposing new port (8084).
- Define deployment automation (CI/CD deploy job or manual script) pointing to VM 1 once GitHub repo is ready.
