# OR-Tools Routing Integration Plan (Phase 4 Kickoff)

## 1. Objective
Embed Google OR-Tools VRP solver into the Intelligent Zone Generator backend to produce route assignments per zone while respecting business constraints (max customers/duration/distance, working days, balancing priorities).

## 2. Data Requirements
- **Inputs**
  - Zone-specific customer lists with coordinates (from zoning outputs).
  - Depot coordinates (per `data/dc_locations.xlsx`).
  - Distance/time matrices from OSRM (`table` endpoint) or cached fallback.
  - Route configuration (constraints, working days, overrides) stored in JSON (extend existing config).
- **Outputs**
  - Route assignments per customer (`route_id`, `day`, `visit_sequence`).
  - Route metrics (distance, duration, constraint violations).
  - Sequence exports (CSV/JSON) aligned with spec.

## 3. Architectural Placement
```
Zoning Service → Routing Service (OR-Tools) → Output Persistence
                   ↑
                OSRM Client
```

- Create `src/app/services/routing/` with:
  - `solver.py` – OR-Tools wrapper using configuration.
  - `osrm_client.py` – reusable table/isochrone requests with retries.
  - `models.py` – dataclasses for routes, metrics.
  - `service.py` – orchestrator invoked by API.

## 4. Configuration
- Extend `settings` with:
  - Hard/soft constraint defaults (max customers/duration/distance, min customers).
  - Working days list.
  - Solver strategies (first solution, local search, time limit).
- Support per-area overrides via JSON config (mirroring spec section 6).

## 5. Algorithm Flow
1. Gather customers for a zone and compute OSRM distance/time matrix.
2. Build OR-Tools `RoutingIndexManager` and `RoutingModel`.
3. Apply constraints:
   - Vehicle capacity (customer count per route).
   - Time/distance dimensions with soft penalties.
   - Day assignment using multi-vehicle or post-processing.
4. Solve with configured strategies and time limits.
5. Extract solution, annotate violations, persist results under `data/outputs/routes_<timestamp>/`.

## 6. Testing Strategy
- Unit tests for solver configuration using small synthetic datasets.
- Integration test that stubs OSRM responses and verifies output structure.
- Manual validation case (per company policy) using real customer subset.

## 7. Next Steps
1. Implement OSRM client with retry/backoff.
2. Scaffold routing module and configuration.
3. Build solver integration with sample dataset.
4. Add persistence/export similar to zoning outputs.
5. Update FastAPI endpoints (`POST /api/routes/optimize`) with new service.
