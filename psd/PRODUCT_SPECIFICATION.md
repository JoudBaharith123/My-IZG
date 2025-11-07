# Intelligent Zone Generator - Product Specification

## 1. Executive Summary

**Product**: Intelligent Zone Generator (IZG)
**Purpose**: Automate territory zoning and route optimization for distribution networks
**Target Users**: Territory managers, logistics planners, operations analysts
**Key Metric**: Process 5,000+ customers into optimized zones/routes in <5 minutes

## 2. System Architecture

```
Frontend (Browser) → Backend API (FastAPI) → OSRM Service
                   ↓
              PostgreSQL/PostGIS
                   ↓
         OR-Tools Solver (Python)
```

**Stack**:
- Frontend: Vanilla JS + Leaflet + Tailwind CSS
- Backend: FastAPI (Python 3.11+)
- Database: PostgreSQL 15 + PostGIS
- Optimization: OR-Tools, scikit-learn
- Routing: OSRM (Docker)

## 3. Core Features

### 3.1 Data Management
- Import: Excel (.xlsx), CSV, GeoJSON
- Export: CSV, Excel, GeoJSON, PDF reports
- Validation: Coordinates, duplicates, required fields
- Storage: Customer master, zone definitions, route assignments

### 3.2 Zone Creation Methods

**Method 1: Polar Sectors**
- Input: DC coordinates, number of sectors (4-24)
- Output: Radial zones from DC
- Constraints: Min/max customers per sector

**Method 2: Travel Time Zones (Isochrones)**
- Input: DC coordinates, time thresholds (15, 30, 45, 60 min)
- Source: OSRM routing engine
- Output: Concentric time-based zones

**Method 3: Geographic Clustering**
- Algorithm: K-Means++ with constraints
- Input: Number of zones, max customers per zone
- Constraints: Customer count, geographic spread
- Balancing: Iterative splitting/merging

**Method 4: Manual Polygon Drawing**
- Tools: Draw, edit, delete polygons
- Snap: To grid, to points
- Assignment: Auto-assign customers within boundaries

### 3.3 Route Optimization

**Solver**: OR-Tools VRP (Vehicle Routing Problem)

**Constraints**:
- Hard: max_customers_per_route (25), max_duration (600 min)
- Soft: max_distance_km (50), min_customers_per_route (10)
- Priority: Customer count > Distance

**Strategies**:
- Seeding: PATH_CHEAPEST_ARC (greedy nearest neighbor)
- Local Search: GUIDED_LOCAL_SEARCH
- Time Limit: 30 seconds per zone

**Input**:
- Zone customers with coordinates
- DC location
- Distance matrix (OSRM)
- Constraints from config

**Output**:
- Route assignments (route_id per customer)
- Visit sequences (1, 2, 3...)
- Day assignments (SUN-SAT)
- Metrics (distance, time, customer count)

### 3.4 Workload Balancing
- Metric: Customer count, revenue, visit time
- Tolerance: ±20% variance
- Method: Post-optimization redistribution

### 3.5 Visualization
- Base Maps: OpenStreetMap, Satellite (MapTiler)
- Layers: Customers (points), Zones (polygons), Routes (lines), DCs (markers)
- Styling: Zone colors (distinct palette), route colors, heat maps
- Controls: Zoom, pan, search, filter, measure

## 4. Data Schema

### 4.1 Customers Table
```sql
customercode (PK), cus_latitude, cus_longitude, isactive,
area, zone, route_id, route_day, visit_sequence,
dc, salesagentcode, cusname, totalamount, 
totaldeliveredorders, averageorderamount
```

### 4.2 Zones Table
```sql
zone_id (PK), area, dc, zone_type (polar|isochrone|cluster|manual),
geometry (PostGIS), customer_count, total_revenue,
created_date, agent_assigned
```

### 4.3 Routes Table
```sql
route_id (PK), zone_id (FK), route_day, customer_count,
total_distance_km, total_time_min, route_sequence (JSON),
constraint_violations (JSON), feasibility_status
```

### 4.4 Config Table
```sql
config_key (PK), config_value (JSON), area_override
```

## 5. API Endpoints

### Data Management
- `POST /api/customers/upload` - Upload customer file
- `GET /api/customers` - List/filter customers
- `PUT /api/customers/{id}` - Update customer
- `GET /api/customers/export` - Export data

### Zone Operations
- `POST /api/zones/polar` - Create polar sectors
- `POST /api/zones/isochrone` - Create travel time zones
- `POST /api/zones/cluster` - K-Means clustering
- `POST /api/zones/manual` - Save manual polygon
- `GET /api/zones` - List zones
- `PUT /api/zones/{id}` - Update zone
- `DELETE /api/zones/{id}` - Delete zone

### Route Optimization
- `POST /api/routes/optimize` - Run OR-Tools VRP solver
- `GET /api/routes` - List routes
- `GET /api/routes/{id}/sequence` - Get visit sequence
- `PUT /api/routes/{id}/assign-day` - Change route day

### Configuration
- `GET /api/config` - Get system config
- `PUT /api/config` - Update config
- `GET /api/config/constraints` - Get route constraints

### OSRM Integration
- `POST /api/osrm/table` - Distance matrix
- `POST /api/osrm/isochrone` - Generate isochrones
- `GET /api/osrm/status` - Check OSRM availability

## 6. Configuration Structure

```json
{
  "zone_creation": {
    "polar_sectors": {
      "default_sectors": 12,
      "min_sectors": 4,
      "max_sectors": 24
    },
    "isochrones": {
      "time_thresholds": [15, 30, 45, 60],
      "method": "osrm"
    },
    "clustering": {
      "algorithm": "kmeans_plusplus",
      "max_iterations": 300,
      "balance_tolerance": 0.2
    }
  },
  "route_optimization": {
    "enabled": true,
    "solver": {
      "first_solution_strategy": "PATH_CHEAPEST_ARC",
      "local_search_metaheuristic": "GUIDED_LOCAL_SEARCH",
      "time_limit_seconds": 30
    },
    "constraints": {
      "max_customers_per_route": 25,
      "min_customers_per_route": 10,
      "max_distance_per_route_km": 50,
      "max_route_duration_minutes": 600
    },
    "working_days": ["SUN", "MON", "TUE", "WED", "THU", "SAT"]
  },
  "area_overrides": {
    "RIYADH": {
      "max_customers_per_route": 25,
      "max_distance_per_route_km": 60
    }
  }
}
```

## 7. Outputs

### 7.1 customers_with_routes.csv
```
customercode, area, zone, route_id, route_day, visit_sequence,
cus_latitude, cus_longitude, [all original columns]
```

### 7.2 route_metrics.csv
```
route_id, zone, area, route_day, customer_count,
total_distance_km, total_travel_time_min, constraint_violations,
feasibility_status
```

### 7.3 route_sequences.csv
```
route_id, visit_sequence, customercode, customer_name,
latitude, longitude, distance_from_previous_km,
estimated_arrival_time
```

### 7.4 GeoJSON Export
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {"type": "Polygon", "coordinates": [...]},
      "properties": {"zone_id": "RIY001", "customer_count": 120}
    }
  ]
}
```

## 8. Performance Requirements

- Zone creation: <2 seconds for 1,000 customers
- Route optimization: <40 seconds per zone (500 customers)
- Full area processing: <6 minutes (5,000 customers, 10 zones)
- Map rendering: <1 second for 5,000 points
- File upload: Support 50MB Excel files
- Concurrent users: 10 simultaneous sessions

## 9. Validation Rules

### Data Import
- Required fields: customercode, cus_latitude, cus_longitude
- Coordinate bounds: Saudi Arabia (16-32°N, 34-56°E)
- Duplicate detection: customercode uniqueness
- Active filter: isactive = 1

### Zone Creation
- Min customers per zone: 10
- Max customers per zone: 1000
- Zone overlap: Warning only (allow multi-assignment)

### Route Optimization
- OSRM availability: Fail fast if unreachable
- Constraint violations: Log warnings, allow override
- Infeasible solutions: Return best effort + violation report

## 10. Error Handling

- File upload errors: Detailed validation report
- OSRM failures: Clear error message, no fallback
- Solver timeouts: Return partial solution + warning
- Constraint violations: Warning flags, allow save
- Database errors: Transaction rollback + user notification

## 11. Security

- Authentication: Not required (internal tool)
- File upload: Virus scan, size limits (50MB)
- SQL injection: Parameterized queries only
- XSS: Content Security Policy headers
- CORS: Whitelist frontend domain

## 12. Deployment Requirements

- OS: Ubuntu 22.04 LTS
- CPU: 4 cores minimum
- RAM: 16GB minimum
- Storage: 100GB SSD
- Network: OSRM localhost:5000, Frontend port 80, API port 8000
- Services: PostgreSQL, OSRM, FastAPI (systemd), Nginx
