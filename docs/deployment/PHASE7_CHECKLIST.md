# Phase 7 – Deployment & Operations Checklist

This document outlines the tasks required to promote the Intelligent Zone Generator (IZG) from the QA environment to production.

## 1. Deployment Artifacts
- [ ] Build backend Docker image (`izg-api`) from the root `Dockerfile`.
- [ ] Push image to Binder's container registry (e.g., `registry.binderservices.com/logistics/izg-api:<tag>`).
- [ ] Archive compiled frontend assets (optional) if a static deployment is required.

## 2. Server Preparation (VM1 – route-cv-ocr)
- [ ] SSH to `149.36.0.182` with deployment credentials.
- [ ] Create `/opt/logistics-ai-platform/services/06-izg-backend/` if it does not exist.
- [ ] Clone `Intelligent_zone_generator` GitHub repo or pull latest changes.
- [ ] Ensure OSRM extract resides under `/mnt/ephemeral/data/osrm/saudi-latest.osrm` (reuse existing OSRM instance).

## 3. Environment Configuration
- [ ] Copy `.env.production` (see template below) to `/opt/logistics-ai-platform/services/06-izg-backend/.env`.
- [ ] Set proper file permissions (`chmod 600 .env`).
- [ ] Confirm system user used by systemd has read access to `/mnt/ephemeral/data`.

Template (`.env.production`):
```
IZG_APP_NAME="Intelligent Zone Generator"
IZG_API_PREFIX=/api
IZG_DATA_ROOT=/opt/logistics-ai-platform/services/06-izg-backend/data
IZG_CUSTOMER_FILE=/opt/logistics-ai-platform/services/06-izg-backend/data/Easyterrritory_26831_29_oct_2025.CSV
IZG_DC_LOCATIONS_FILE=/opt/logistics-ai-platform/services/06-izg-backend/data/dc_locations.xlsx
IZG_OSRM_BASE_URL=http://149.36.0.182:5000
IZG_OSRM_PROFILE=driving
IZG_OSRM_MAX_RETRIES=3
IZG_OSRM_BACKOFF_SECONDS=1.0
```

## 4. Systemd Service (Backend)
- [ ] Copy `docs/deployment/izg-api.service` into `/etc/systemd/system/`.
- [ ] Run `sudo systemctl daemon-reload`.
- [ ] Enable service: `sudo systemctl enable izg-api`.
- [ ] Start service: `sudo systemctl start izg-api`.
- [ ] Validate status: `systemctl status izg-api`.

## 5. Nginx/Reverse Proxy
- [ ] Create `/etc/nginx/sites-available/izg.conf` using the provided template.
- [ ] Symlink to `sites-enabled`.
- [ ] Test configuration: `sudo nginx -t`.
- [ ] Reload Nginx: `sudo systemctl reload nginx`.
- [ ] Confirm external access via `https://binderlogistics.com/izg/` (or assigned route).

Template (`docs/deployment/nginx_izg.conf`):
```
server {
    listen 80;
    server_name binderlogistics.com;

    location /izg/ {
        proxy_pass http://127.0.0.1:8084/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 6. Monitoring & Logging
- [ ] Expose `/api/health` and `/api/health/osrm` endpoints to Prometheus.
- [ ] Ship application logs (`/var/log/izg-api.log`) to central log aggregator.
- [ ] Define alerts for:
  - OSRM health check failures.
  - API response time > 2s.
  - Solver queue backlog.

## 7. Backups
- [ ] Ensure outputs under `/mnt/ephemeral/data/izg/` are part of the nightly backup job.
- [ ] Retain at least 30 days of zone/route exports.

## 8. UAT & Launch
- [ ] Coordinate UAT session with territory managers & logistics ops.
- [ ] Provide access credentials and usage guide (`docs/README.md`).
- [ ] Collect sign-off from Finance regarding clearance workflows.
- [ ] Schedule go-live window and fallback plan.

---

### Supporting Files
- `docs/deployment/izg-api.service` – systemd unit file.
- `docs/deployment/nginx_izg.conf` – example Nginx configuration.
- `docs/deployment/deploy.sh` – helper for manual deployments.
