# Routing Architecture

## Overview

The routing system supports two modes:

1. **Automatic Assignment Mode**: OR-Tools automatically assigns customers to routes and optimizes sequences
2. **Manual Assignment Mode**: Users manually assign customers to routes, OR-Tools only optimizes sequences

## Architecture

### Components

1. **OSRM Client** (`osrm_client.py`)
   - Provides distance/time matrices via OSRM API
   - Handles chunking for large coordinate sets
   - Falls back to haversine distance if OSRM unavailable

2. **OR-Tools Solver** (`solver.py`)
   - Full VRP solver for automatic assignment + sequence optimization
   - Uses OSRM distance matrix for cost calculation
   - Handles constraints (max customers, duration, distance)

3. **Sequence Solver** (`sequence_solver.py`)
   - TSP solver for sequence-only optimization
   - Used when customers are pre-assigned to routes
   - Optimizes visit order within each route to minimize distance

4. **Routing Service** (`service.py`)
   - Orchestrates the routing process
   - Chooses between automatic and manual modes
   - Handles data persistence

## Manual Assignment Workflow

1. **User selects customers per route** (e.g., 20 customers for Route 1, 20 for Route 2, etc.)
2. **OSRM provides distance matrix** for all customers (depot + customers)
3. **For each route:**
   - Extract sub-matrix (depot + route customers)
   - OR-Tools solves TSP to find optimal sequence
   - Returns optimized visit order
4. **Result**: Each route has an optimized sequence minimizing travel distance

## Example: 120 Customers, 6 Routes

```
Zone: 120 customers
Routes: 6 routes × 20 customers each

Manual Assignment:
- Route 1 (MON): [Customer IDs manually selected]
- Route 2 (TUE): [Customer IDs manually selected]
- ...
- Route 6 (SAT): [Customer IDs manually selected]

Sequence Optimization (per route):
- OSRM calculates distances between all customers
- OR-Tools finds optimal sequence: Depot → Customer A → Customer B → ... → Depot
- Minimizes total travel distance using OSRM road network data
```

## API Usage

### Automatic Mode (Current)
```json
POST /api/routes/optimize
{
  "city": "Jeddah",
  "zone_id": "JEDC01",
  "constraints": {
    "max_customers_per_route": 25,
    "max_route_duration_minutes": 600,
    "max_distance_per_route_km": 50
  }
}
```

### Manual Assignment Mode (New)
```json
POST /api/routes/optimize
{
  "city": "Jeddah",
  "zone_id": "JEDC01",
  "route_assignments": [
    {
      "route_id": "Route_1",
      "day": "MON",
      "customer_ids": ["CUST001", "CUST002", ..., "CUST020"]
    },
    {
      "route_id": "Route_2",
      "day": "TUE",
      "customer_ids": ["CUST021", "CUST022", ..., "CUST040"]
    }
    // ... up to Route_6
  ]
}
```

## Implementation Details

### OSRM Integration
- **Purpose**: Provides accurate road network distances and travel times
- **Usage**: Distance matrix for OR-Tools cost calculation
- **Fallback**: Haversine distance if OSRM unavailable

### OR-Tools Integration
- **Purpose**: Solves optimization problems (VRP for assignment, TSP for sequence)
- **Strategies**: PATH_CHEAPEST_ARC + GUIDED_LOCAL_SEARCH
- **Time Limit**: Configurable (default 30s)

### Sequence Optimization Algorithm
1. For each manually assigned route:
   - Create sub-matrix: [Depot, Route Customers]
   - Solve TSP using OR-Tools
   - Extract optimized sequence
   - Calculate total distance/duration
2. Return all routes with optimized sequences

## Benefits

1. **Flexibility**: Users can manually control route assignments
2. **Optimization**: Sequences are still optimized for minimal distance
3. **Accuracy**: Uses real road network distances (OSRM)
4. **Efficiency**: Only optimizes sequences, not assignments (faster)


