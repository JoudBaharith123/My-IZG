# User Acceptance Testing Plan – Intelligent Zone Generator

## Objectives
- Verify IZG workflows with real customer data (upload, zoning, routing).
- Confirm finance “clearness” procedures align with operational requirements.
- Collect feedback from key stakeholders prior to production release.

## Participants
| Role | Name | Responsibilities |
|------|------|------------------|
| Territory Manager (Jeddah) | TBD | Validate zoning outputs and agent assignments |
| Logistics Planner | TBD | Review routing proposals, constraints, map overlays |
| Finance Liaison | TBD | Confirm finance clearance steps |
| IT/OSRM Owner | TBD | Monitor OSRM performance |
| Product Owner | TBD | Track issues and sign-off |

## Pre-UAT Checklist
- [ ] Refresh staging dataset with latest customer CSV.
- [ ] Ensure OSRM service is running with the Saudi extract.
- [ ] Deploy latest IZG build (backend + frontend) to UAT environment.
- [ ] Seed UAT accounts and credentials:
  - tm.jeddah@binder.com (Territory Manager)
  - planner.ops@binder.com (Logistics Planner)
  - finance.clearance@binder.com (Finance)
- [ ] Share UAT access instructions & checklist with participants.

## Dataset Upload Workflow
1. Start the FastAPI backend (`uvicorn src.app.main:app --reload --port 8000`) and confirm it serves `http://localhost:8000/api/health`.
2. Start the Vite frontend (`npm run dev`) and open `http://localhost:5173/upload` in a browser session on the same machine.
3. Click **Upload New Dataset**, choose the target CSV/XLSX file, and wait for the success banner.
4. Verify the **Last Upload** panel reflects the new filename, size, and timestamp. Stats tiles and validation cards should refresh automatically.
5. Switch to the Zoning or Routing workspaces to confirm the city dropdown now lists the uploaded dataset's cities and the map plots customer points.

## Test Scenarios
1. **Upload & Validate** – Territory Manager
   - Upload latest customer CSV.
   - Review validation cards, download issue reports.
   - Confirm stats match Excel reference sheet.

2. **Zoning Workspace** – Territory Manager & Planner
   - Run clustering (target 12 zones) with balancing.
   - Inspect map overlays, transfer list, download assignments CSV.
   - Run manual polygon scenario to adjust a problematic zone.

3. **Routing Workspace** – Logistics Planner
   - Select zone `JED001` and generate routes with default constraints.
   - Verify route polylines, metrics, downloads.
   - Persist output to disk and confirm presence under `/data/outputs`.

4. **Finance Clearance Review** – Finance Liaison
   - Check transfer list for finance-clearing reminders.
   - Cross-check sample customers with finance system.

5. **Reports Page** – All Participants
   - Search, filter, and download recent exports.
   - Confirm metadata (city, method, author) displays correctly.

## Acceptance Criteria
- All scenarios executed without critical errors.
- Data outputs match expected totals (±1 tolerance).
- Finance clearance workflow acknowledged by Finance liaison.
- All defects logged in Jira and triaged.
- Product owner provides final go/no-go decision.

## Schedule
- UAT window: 3 business days (TBD).
- Daily stand-up to review issues and retest fixes.

## Deliverables
- UAT sign-off document.
- Jira tickets for any defects.
- Updated runbook if procedural changes arise.
