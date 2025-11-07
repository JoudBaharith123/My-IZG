# IZG Production Launch Runbook

## 1. Pre-Launch Checklist
- [ ] UAT sign-off collected (Territory Manager, Logistics Planner, Finance, Product Owner).
- [ ] Deployment checklist completed (Docker image pushed, systemd service configured, Nginx proxy live).
- [ ] Monitoring dashboards verified (Prometheus scrape, alert rules).
- [ ] Backup job validated for `/mnt/ephemeral/data/izg/`.
- [ ] Communication plan circulated (email to ops + finance about go-live window and contact points).

## 2. Launch Window
- Recommended off-peak time: 20:00–22:00 KSA.
- Participants on call: Product Owner, DevOps, OSRM owner, Finance liaison.
- Bridge channel: Teams room “IZG Go-Live” (or equivalent).

## 3. Cutover Steps
1. Stop legacy zone calculator if being replaced: run `sudo systemctl stop legacy-zone-calculator`.
2. Deploy IZG using `./docs/deployment/deploy.sh <tag>`.
3. Verify health:
   - `curl http://127.0.0.1:8084/api/health`
   - `curl http://127.0.0.1:8084/api/health/osrm`
4. Confirm UI reachable at `https://binderlogistics.com/izg/`.
5. Run smoke tests:
   - `curl http://127.0.0.1:8084/api/customers/stats`
   - Execute a small `/api/zones/generate` request.
   - Load Reports page in browser.
6. Announce IZG go-live in finance and ops channels.

## 4. Post-Launch Monitoring
- Observe Prometheus dashboard for 60 minutes post cutover.
- Confirm logs flowing to central aggregator.
- Validate new exports under `/mnt/ephemeral/data/izg/`.

## 5. Rollback Plan
- If critical issue occurs:
  1. Notify stakeholders.
  2. `sudo systemctl stop izg-api`.
  3. `sudo systemctl start legacy-zone-calculator`.
  4. Restore DNS/proxy to legacy endpoint if necessary.
  5. Collect logs for root-cause analysis.

## 6. Post-Go-Live
- Schedule retrospective with stakeholders.
- Document lessons learned and update runbook.
- Plan phased rollout to additional cities if needed.
