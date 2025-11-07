# Phase 6 Manual Validation Checklist

The steps below extend the existing manual scenarios to cover the recent backend/frontend changes. Run them whenever a new build is prepared for QA or before promoting to Phase 7.

## Map Overlay Verification
- Launch the Zoning Workspace UI and submit a clustering run for **Jeddah** with `target_zones = 1`. Confirm markers render for all returned customers and that the map captures a shaded polygon enclosing the points (convex hull overlay).
- Switch to **Manual** method, add a polygon enclosing at least three customers, generate zones, and verify the polygon border matches the coordinates entered. Download `assignments.csv` and confirm all enclosed customers are assigned to the polygon’s zone.
- Navigate to the Routing Workspace, pick a populated zone, run route optimization, and ensure the map draws colored polylines for each route (looping depot → customers → depot). Cross-check the sequence tab to confirm line colors match route IDs.

## Paginated Customer Locations
- Upload a dataset (or mock data via `sandbox_subset.csv`) with more than 2,000 customers and open the Zoning Workspace. Confirm the “Load more” control appears below the map after the first batch. Click it twice and ensure the count of plotted markers increases and no duplicate customers appear.
- Repeat the test under Routing Workspace with a zone that has >1,500 customers. Verify the “Load more” control increments the totals and that route markers update to reflect the additional pages.
- Exercise the `/api/customers/locations` endpoint directly (e.g., with `curl` or Postman) using different `page` / `page_size` combinations, confirming `has_next_page` toggles appropriately.

## Performance Spot Checks
- Capture baseline timings for `/api/zones/generate` (polar & clustering) and `/api/routes/optimize` using the 5k-customer dataset. Record duration, memory footprint, and the size of generated overlays. Compare against previous benchmarks before approving release.
- Stress-test `/api/customers/locations` by requesting sequential pages until termination. Ensure latency stays <500 ms and memory use remains stable.

## Security & Hardening Notes
- Confirm all new endpoints (`/customers/locations`) honour query validation (no SQL/string injection vectors) and that unexpected parameters return 422 responses.
- Run the FastAPI app with `uvicorn --reload` behind the configured reverse proxy and verify response headers conform to our security baseline (`Strict-Transport-Security`, `X-Content-Type-Options`, etc.).
- Validate that temporary run directories inherit correct file permissions (read/write for service user only) under both local and containerised environments.

Record findings and anomalies in `manual_testing/test_run_log.md` (create if not present) for traceability ahead of Phase 7 activities.
