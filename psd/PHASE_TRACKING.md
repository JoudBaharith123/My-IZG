# Project Phases & Task Tracking

## Phase 1: Infrastructure Setup (Week 1)

### 1.1 Environment Setup
- [ ] Provision Ubuntu 22.04 VM
- [ ] Install PostgreSQL 15 + PostGIS extension
- [ ] Install Python 3.11 + pip
- [ ] Install Node.js 20 (for build tools only)
- [ ] Install Docker + Docker Compose
- [ ] Configure firewall (ports 80, 8000, 5432, 5000)

### 1.2 OSRM Setup
- [ ] Download Saudi Arabia OSM data (geofabrik.de)
- [ ] Create OSRM Dockerfile
- [ ] Process OSM data with OSRM (extract, contract)
- [ ] Start OSRM service (docker-compose)
- [ ] Test OSRM endpoints (table, route)
- [ ] Create health check script

### 1.3 Database Setup
- [ ] Create database: `zone_generator`
- [ ] Enable PostGIS extension
- [ ] Create customers table
- [ ] Create zones table
- [ ] Create routes table
- [ ] Create config table
- [ ] Create indexes (customercode, zone_id, coordinates)
- [ ] Load sample data for testing

### 1.4 Backend Scaffolding
- [ ] Create project structure (`/app`, `/api`, `/services`, `/models`)
- [ ] Create requirements.txt (FastAPI, OR-Tools, psycopg2, scikit-learn)
- [ ] Create main.py (FastAPI app)
- [ ] Configure CORS middleware
- [ ] Create database connection pool
- [ ] Create environment config (.env)
- [ ] Test API startup

**Deliverables**: Running infrastructure, empty API, database ready

---

## Phase 2: Data Management Module (Week 1-2)

### 2.1 File Upload API
- [ ] POST /api/customers/upload endpoint
- [ ] Parse Excel files (openpyxl)
- [ ] Parse CSV files (pandas)
- [ ] Validate required columns
- [ ] Validate coordinate bounds
- [ ] Check duplicate customercodes
- [ ] Insert into database (batch insert)
- [ ] Return validation report JSON
- [ ] Add error handling

### 2.2 Customer CRUD API
- [ ] GET /api/customers (with filters: area, zone, isactive)
- [ ] GET /api/customers/{id}
- [ ] PUT /api/customers/{id}
- [ ] DELETE /api/customers/{id} (soft delete)
- [ ] Add pagination (limit, offset)
- [ ] Add sorting (by area, customercode)

### 2.3 Data Export API
- [ ] GET /api/customers/export?format=csv
- [ ] GET /api/customers/export?format=xlsx
- [ ] GET /api/customers/export?format=geojson
- [ ] Include filters in export
- [ ] Stream large files (chunked response)

### 2.4 Frontend: Upload Interface
- [ ] Create index.html (single page app)
- [ ] Add Tailwind CSS CDN
- [ ] Create file upload form (drag-drop zone)
- [ ] Show upload progress bar
- [ ] Display validation results table
- [ ] Add "Download Sample Template" button

### 2.5 Frontend: Data Grid
- [ ] Display customers in table
- [ ] Add column sorting
- [ ] Add filter inputs (area, zone, active)
- [ ] Add pagination controls
- [ ] Add export button
- [ ] Show record count

**Deliverables**: Working data import/export, basic UI

---

## Phase 3: Map Visualization (Week 2)

### 3.1 Map Setup
- [ ] Add Leaflet.js CDN
- [ ] Initialize map (centered on Saudi Arabia)
- [ ] Add OpenStreetMap base layer
- [ ] Add zoom/pan controls
- [ ] Add scale bar
- [ ] Add geocoding search box (Nominatim)

### 3.2 Customer Points Layer
- [ ] GET /api/customers?bbox=... endpoint (spatial query)
- [ ] Fetch customers in viewport
- [ ] Plot customers as circle markers
- [ ] Color by area (distinct colors)
- [ ] Add popups (customer details)
- [ ] Add clustering (Leaflet.markercluster)
- [ ] Optimize for 5,000+ points

### 3.3 Layer Controls
- [ ] Create layer panel (sidebar)
- [ ] Add layer visibility toggles
- [ ] Add opacity sliders
- [ ] Add "Fit to Layer" button
- [ ] Show layer statistics (count, extent)

### 3.4 Drawing Tools
- [ ] Add Leaflet.draw plugin
- [ ] Enable polygon drawing
- [ ] Enable circle/rectangle drawing
- [ ] Add edit mode (move vertices)
- [ ] Add delete tool
- [ ] Show coordinates while drawing

**Deliverables**: Interactive map with customer points, drawing tools

---

## Phase 4: Zone Creation - Polar Sectors (Week 2-3)

### 4.1 Backend: Polar Sector Logic
- [ ] Create services/zone_polar.py
- [ ] Function: calculate_polar_sectors(dc_coords, num_sectors, customers_df)
- [ ] Generate sector boundaries (0-360° divided by num_sectors)
- [ ] Assign customers to sectors (angle calculation)
- [ ] Create PostGIS polygon geometries
- [ ] Insert into zones table
- [ ] Return zone GeoJSON

### 4.2 API Endpoint
- [ ] POST /api/zones/polar
- [ ] Request body: {dc_coords, num_sectors, customer_filter}
- [ ] Call zone_polar service
- [ ] Update customers table (zone assignment)
- [ ] Return zone GeoJSON + stats

### 4.3 Frontend: Polar Wizard
- [ ] Create "New Zone" button → dropdown menu
- [ ] Add "Polar Sectors" modal dialog
- [ ] DC location input (lat/lon or click map)
- [ ] Number of sectors slider (4-24)
- [ ] Preview button (show sectors without saving)
- [ ] Confirm button (save zones)
- [ ] Display zone statistics

### 4.4 Frontend: Zone Visualization
- [ ] Fetch zones from API (GET /api/zones)
- [ ] Plot zone polygons (Leaflet.polygon)
- [ ] Use distinct colors per zone
- [ ] Add zone labels (center point)
- [ ] Add zone popups (stats)
- [ ] Highlight on hover

**Deliverables**: Polar sector zoning working end-to-end

---

## Phase 5: Zone Creation - Travel Time Zones (Week 3)

### 5.1 Backend: OSRM Integration
- [ ] Create services/osrm_client.py
- [ ] Function: get_distance_matrix(coordinates)
- [ ] Function: get_isochrones(dc_coords, time_thresholds)
- [ ] Handle OSRM errors gracefully
- [ ] Add connection pooling
- [ ] Add retry logic

### 5.2 Backend: Isochrone Zone Logic
- [ ] Create services/zone_isochrone.py
- [ ] Call OSRM for time-based polygons
- [ ] Convert to PostGIS geometries
- [ ] Assign customers to nearest zone (spatial join)
- [ ] Insert into zones table

### 5.3 API Endpoint
- [ ] POST /api/zones/isochrone
- [ ] Request: {dc_coords, time_thresholds, customer_filter}
- [ ] Call OSRM + zone_isochrone service
- [ ] Return zone GeoJSON

### 5.4 Frontend: Isochrone Wizard
- [ ] Add "Travel Time Zones" to dropdown
- [ ] Modal with DC input
- [ ] Time threshold checkboxes (15, 30, 45, 60 min)
- [ ] Preview button
- [ ] Save button
- [ ] Loading spinner (OSRM call)

**Deliverables**: Travel time zoning working

---

## Phase 6: Zone Creation - Geographic Clustering (Week 3-4)

### 6.1 Backend: K-Means Clustering
- [ ] Create services/zone_cluster.py
- [ ] Implement K-Means++ with scikit-learn
- [ ] Function: cluster_customers(customers_df, num_zones, constraints)
- [ ] Enforce max_customers_per_zone (split oversized clusters)
- [ ] Merge undersized clusters
- [ ] Create convex hull polygons (PostGIS ST_ConvexHull)
- [ ] Assign zone IDs

### 6.2 API Endpoint
- [ ] POST /api/zones/cluster
- [ ] Request: {num_zones, max_customers, customer_filter}
- [ ] Call zone_cluster service
- [ ] Return zone GeoJSON

### 6.3 Frontend: Clustering Wizard
- [ ] Add "Geographic Clustering" option
- [ ] Number of zones input
- [ ] Max customers per zone input
- [ ] Constraint toggles
- [ ] Preview + Save buttons
- [ ] Show cluster statistics table

**Deliverables**: K-Means clustering working

---

## Phase 7: Manual Zone Drawing (Week 4)

### 7.1 Backend: Manual Zone Save
- [ ] POST /api/zones/manual
- [ ] Request: {geometry (GeoJSON), zone_name}
- [ ] Validate geometry (valid polygon)
- [ ] Spatial query: customers within polygon
- [ ] Insert zone + assign customers
- [ ] Return zone with customer count

### 7.2 Frontend: Drawing Mode
- [ ] "Draw Zone" button activates Leaflet.draw
- [ ] User draws polygon on map
- [ ] Show customer count in drawn area (live)
- [ ] Save dialog (zone name input)
- [ ] Save polygon to backend
- [ ] Refresh zone layer

**Deliverables**: Manual drawing working

---

## Phase 8: Route Optimization (Week 4-5)

### 8.1 Backend: OR-Tools VRP Solver
- [ ] Create services/route_solver.py
- [ ] Function: optimize_zone_routes(zone_id, constraints)
- [ ] Get customers in zone + DC coords
- [ ] Call OSRM for distance matrix
- [ ] Build OR-Tools VRP model (capacity, time dimensions)
- [ ] Set first solution strategy (PATH_CHEAPEST_ARC)
- [ ] Set local search (GUIDED_LOCAL_SEARCH)
- [ ] Solve with 30s timeout
- [ ] Extract routes + sequences
- [ ] Assign route days (SUN-SAT cycle)
- [ ] Insert into routes table
- [ ] Update customers table (route_id, visit_sequence)

### 8.2 API Endpoints
- [ ] POST /api/routes/optimize
- [ ] Request: {zone_id, constraints (override)}
- [ ] Call route_solver service
- [ ] Return routes + metrics

- [ ] GET /api/routes?zone_id=...
- [ ] Return list of routes with stats

- [ ] GET /api/routes/{route_id}/sequence
- [ ] Return ordered customer list

### 8.3 Frontend: Optimization Panel
- [ ] Add "Optimize Routes" button per zone
- [ ] Modal with constraint inputs
- [ ] Progress indicator (WebSocket or polling)
- [ ] Display results table (routes with metrics)
- [ ] Highlight constraint violations
- [ ] Export route sheets button

### 8.4 Frontend: Route Visualization
- [ ] Plot routes as colored lines (zone centroid → customers → centroid)
- [ ] Number markers (visit sequence)
- [ ] Route legend (Route 1-1, Route 1-2, etc.)
- [ ] Toggle route visibility

**Deliverables**: Route optimization working

---

## Phase 9: Configuration & Constraints (Week 5)

### 9.1 Backend: Config Management
- [ ] GET /api/config (return full config JSON)
- [ ] PUT /api/config (update config)
- [ ] Load config from database at startup
- [ ] Apply area-specific overrides

### 9.2 Frontend: Settings Page
- [ ] Create settings.html (separate page)
- [ ] Load config into form fields
- [ ] Section: Zone Creation defaults
- [ ] Section: Route Optimization constraints
- [ ] Section: Area Overrides (add/edit)
- [ ] Save button (PUT /api/config)
- [ ] Reset to defaults button

**Deliverables**: Configurable system

---

## Phase 10: Reporting & Export (Week 5-6)

### 10.1 Route Reports
- [ ] GET /api/routes/export?zone_id=... (CSV)
- [ ] GET /api/routes/export?format=xlsx
- [ ] GET /api/routes/metrics (summary dashboard)
- [ ] Generate PDF route sheets (ReportLab)

### 10.2 Frontend: Reports Page
- [ ] Create reports.html
- [ ] Zone selector dropdown
- [ ] Date range picker
- [ ] Report type selector
- [ ] Generate button → download file
- [ ] Display metrics dashboard (charts.js)

### 10.3 Validation Reports
- [ ] GET /api/zones/validate (check all constraints)
- [ ] Return violations list
- [ ] Frontend: Show warnings in UI

**Deliverables**: Complete reporting system

---

## Phase 11: Testing & Refinement (Week 6)

### 11.1 Backend Tests
- [ ] Unit tests (pytest): zone_polar, zone_cluster, route_solver
- [ ] API integration tests (httpx)
- [ ] Performance test: 5,000 customers
- [ ] OSRM mock for offline testing

### 11.2 Frontend Tests
- [ ] Manual testing checklist
- [ ] Browser compatibility (Chrome, Firefox, Safari)
- [ ] Mobile responsive check
- [ ] Accessibility audit (keyboard navigation)

### 11.3 Data Validation
- [ ] Test with actual Saudi Arabia customer data
- [ ] Validate coordinate projections
- [ ] Check Arabic character support (UTF-8)

### 11.4 Bug Fixes
- [ ] Fix identified issues
- [ ] Optimize slow queries
- [ ] Improve error messages

**Deliverables**: Stable, tested system

---

## Phase 12: Deployment (Week 6)

### 12.1 Production Setup
- [ ] Create systemd service files
- [ ] Configure Nginx reverse proxy
- [ ] Set up SSL certificate (Let's Encrypt)
- [ ] Configure log rotation
- [ ] Set up database backups (pg_dump cron)

### 12.2 Deployment Script
- [ ] Create deploy.sh script
- [ ] Pull latest code from git
- [ ] Install Python dependencies
- [ ] Run database migrations
- [ ] Restart services
- [ ] Verify health checks

### 12.3 Documentation
- [ ] User guide (how to use system)
- [ ] Admin guide (deployment, maintenance)
- [ ] API documentation (auto-generated from FastAPI)
- [ ] Troubleshooting guide

### 12.4 Training
- [ ] Record demo video
- [ ] Create sample datasets
- [ ] Conduct user training session

**Deliverables**: Production deployment, documentation

---

## Status Legend
- [ ] Not started
- [~] In progress
- [x] Completed
- [!] Blocked

## Dependencies
- Phase 1 must complete before all others
- Phase 2 required for Phase 3
- Phase 3 required for Phase 4-7
- Phase 8 requires OSRM (Phase 5)
- Phase 10 requires Phase 4-8 complete

## Critical Path
1 → 2 → 3 → 4 → 5 → 8 → 12 (6 weeks minimum)

## Weekly Milestones
- Week 1: Infrastructure + Data Management
- Week 2: Map + Polar Zones
- Week 3: Isochrones + Clustering
- Week 4: Manual Drawing + Route Optimization Start
- Week 5: Route Optimization Complete + Config
- Week 6: Reports + Testing + Deployment
