# CI/CD Overview

## Workflow
- GitHub Actions workflow: `.github/workflows/ci.yml`
- Triggers: push/pull request on `main`/`master`
- Jobs:
  1. Checkout repo
  2. Install Python 3.11 + dependencies (`requirements.txt`)
  3. Run mypy type checks on `src/`
  4. Run pytest suite
  5. Build Docker image (`Dockerfile`) as smoke check

## Secrets & Extensions
- No secrets required yet; add registry credentials later if pushing images.
- Future enhancements:
  - Cache pip packages (`actions/cache`)
  - Push image to registry (add build-push stage)
  - Deploy stage once VM pipeline defined

## Local Verification
Before pushing:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
mypy src
pytest
docker build -t izg-backend:dev .
```

> Integration tests (`tests/test_integration.py`) stub OSRM responses and redirect file outputs to tmp folders, so they run without network access or touching real data directories.

## Health Checks
- `/health`: API alive check (no external dependencies).
- `/health/osrm`: Verifies connectivity to the configured OSRM base URL; returns `{ "service": "osrm", "healthy": bool }`.
- Integrate these into Prometheus/Grafana or external uptime checks when deploying to VM1.
