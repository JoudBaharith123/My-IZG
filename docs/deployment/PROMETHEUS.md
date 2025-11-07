# Monitoring Integration – Prometheus & Logging

## Prometheus Scrape Config
Add the API service to the existing Prometheus target list:

```
  - job_name: izg-api
    metrics_path: /api/health
    static_configs:
      - targets: ['149.36.0.182:8084']
```

Optionally, expose a richer metrics endpoint later (`/metrics`). For OSRM, retain existing job:

```
  - job_name: osrm
    metrics_path: /health
    static_configs:
      - targets: ['149.36.0.182:5000']
```

## Log Shipping
- Create `/var/log/izg-api.log` and `/var/log/izg-api.err.log` (owned by `izg:izg`).
- Configure Fluent Bit / Filebeat to ship these logs to the central aggregator (topic: `logistics.izg`).
- Ensure JSON logging can be parsed by updating FastAPI logging config if required.

## Alerting Suggestions
- `izg_api_up == 0` for 5 minutes.
- 95th percentile response time over 1 minute > 2 seconds.
- `/api/health/osrm` returning non-200 responses.
