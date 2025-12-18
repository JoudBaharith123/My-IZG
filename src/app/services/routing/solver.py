"""OR-Tools VRP solver integration."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

try:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False
    pywrapcp = None
    routing_enums_pb2 = None

from ...config import settings
from ...models.domain import Customer
from .models import RoutePlan, RouteStop, RoutingResult


@dataclass(slots=True)
class SolverConstraints:
    max_customers_per_route: int = settings.max_customers_per_route
    min_customers_per_route: int = settings.min_customers_per_route
    max_route_duration_minutes: int = settings.max_route_duration_minutes
    max_distance_per_route_km: float = settings.max_distance_per_route_km


def _build_manager(distance_matrix: list[list[float]], constraints: SolverConstraints) -> pywrapcp.RoutingIndexManager:
    node_count = len(distance_matrix)
    vehicle_count = max(1, math.ceil((node_count - 1) / constraints.max_customers_per_route))
    return pywrapcp.RoutingIndexManager(node_count, vehicle_count, 0)


def _seconds_from_minutes(minutes: float) -> int:
    return int(minutes * 60)


def _prepare_matrices(osrm_result: dict) -> tuple[list[list[int]], list[list[int]]]:
    """Prepare distance and duration matrices from OSRM result.
    
    Handles None values by using a large penalty value instead of 0,
    which prevents solver issues when routes are unreachable.
    """
    durations = osrm_result.get("durations")
    distances = osrm_result.get("distances")
    if durations is None or distances is None:
        raise ValueError("OSRM table response missing durations or distances.")
    
    # Use large penalty for None values (unreachable routes) instead of 0
    # This prevents the solver from thinking all distances are 0
    LARGE_PENALTY = 999999999  # ~277 hours or ~1M km - effectively unreachable
    
    duration_matrix = [
        [int(value) if value is not None else LARGE_PENALTY for value in row]
        for row in durations
    ]
    distance_matrix = [
        [int(value) if value is not None else LARGE_PENALTY for value in row]
        for row in distances
    ]
    
    # Ensure depot-to-depot is 0
    if duration_matrix and len(duration_matrix) > 0:
        duration_matrix[0][0] = 0
    if distance_matrix and len(distance_matrix) > 0:
        distance_matrix[0][0] = 0
    
    return duration_matrix, distance_matrix


def solve_vrp(
    *,
    zone_id: str,
    customers: Sequence[Customer],
    osrm_table: dict,
    working_days: Sequence[str] | None = None,
    constraints: SolverConstraints | None = None,
) -> RoutingResult:
    if not ORTOOLS_AVAILABLE:
        raise ImportError(
            "OR-Tools is not installed. Routing optimization requires OR-Tools. "
            "Install Python 3.11 or 3.12 to use routing features, or install OR-Tools for Python 3.14 when available."
        )
    constraints = constraints or SolverConstraints()
    working_days = tuple(working_days or settings.working_days)

    duration_matrix, distance_matrix = _prepare_matrices(osrm_table)
    
    # Validate matrices
    if not duration_matrix or not distance_matrix:
        raise ValueError("Empty duration or distance matrix from OSRM.")
    if len(duration_matrix) != len(distance_matrix):
        raise ValueError(f"Matrix size mismatch: durations={len(duration_matrix)}, distances={len(distance_matrix)}")
    if len(duration_matrix) < 2:
        raise ValueError(f"Insufficient locations for routing: {len(duration_matrix)} (need at least 2: depot + 1 customer)")
    
    # Check if we have any valid (non-penalty) routes from depot
    LARGE_PENALTY = 999999999
    valid_routes_from_depot = sum(
        1 for i in range(1, len(distance_matrix[0]))
        if distance_matrix[0][i] < LARGE_PENALTY and duration_matrix[0][i] < LARGE_PENALTY
    )
    unreachable_count = len(customers) - valid_routes_from_depot
    
    if valid_routes_from_depot == 0:
        # Check if this might be a network/connectivity issue
        import logging
        logging.error(
            f"No reachable customers from depot for zone {zone_id}. "
            f"This could indicate: (1) OSRM service connectivity issues, "
            f"(2) Network/DNS failures, (3) Invalid customer coordinates, "
            f"or (4) All customers are genuinely unreachable from depot."
        )
        raise ValueError(
            "No reachable customers from depot. All routes returned unreachable. "
            "Possible causes: OSRM service connectivity issues, network failures, "
            "or invalid coordinates. The system should automatically fall back to haversine distance "
            "if OSRM is unavailable - check backend logs for fallback status."
        )
    
    if unreachable_count > 0:
        import logging
        logging.warning(
            f"{unreachable_count} out of {len(customers)} customers are unreachable from depot. "
            f"These will be excluded from routing."
        )
    
    manager = _build_manager(distance_matrix, constraints)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    demand_evaluator = lambda index: 0 if manager.IndexToNode(index) == 0 else 1
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_evaluator)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,
        [constraints.max_customers_per_route] * routing.vehicles(),
        True,
        "Capacity",
    )

    def duration_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return duration_matrix[from_node][to_node]

    duration_callback_index = routing.RegisterTransitCallback(duration_callback)
    routing.AddDimension(
        duration_callback_index,
        0,
        _seconds_from_minutes(constraints.max_route_duration_minutes),
        True,
        "Time",
    )

    time_dimension = routing.GetDimensionOrDie("Time")

    routing.AddDimension(
        transit_callback_index,
        0,
        int(constraints.max_distance_per_route_km * 1000),
        True,
        "Distance",
    )

    distance_dimension = routing.GetDimensionOrDie("Distance")

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = getattr(
        routing_enums_pb2.FirstSolutionStrategy, settings.solver_first_solution_strategy
    )
    search_parameters.local_search_metaheuristic = getattr(
        routing_enums_pb2.LocalSearchMetaheuristic, settings.solver_local_search_metaheuristic
    )
    search_parameters.time_limit.FromSeconds(settings.solver_time_limit_seconds)

    assignment = routing.SolveWithParameters(search_parameters)
    
    # Track if we used relaxed constraints
    used_relaxed_constraints = False
    relaxed_distance_limit = None
    relaxed_duration_limit = None
    
    # If infeasible, try with relaxed constraints
    if not assignment:
        import logging
        logging.warning(
            f"Routing problem infeasible for zone {zone_id} with strict constraints. "
            f"Attempting automatic constraint relaxation..."
        )
        
        # Calculate actual max distances/durations from depot to customers
        max_depot_distance_km = max(
            (distance_matrix[0][i] / 1000.0 for i in range(1, len(distance_matrix[0])) 
             if distance_matrix[0][i] < LARGE_PENALTY),
            default=0
        )
        max_depot_duration_min = max(
            (duration_matrix[0][i] / 60.0 for i in range(1, len(duration_matrix[0])) 
             if duration_matrix[0][i] < LARGE_PENALTY),
            default=0
        )
        
        # Relax constraints: use at least 2x the max depot-to-customer distance/duration
        # or 1.5x the original constraint, whichever is larger
        relaxed_distance = max(
            constraints.max_distance_per_route_km * 1.5,
            max_depot_distance_km * 2.5,
            100.0  # Minimum 100km
        )
        relaxed_duration = max(
            constraints.max_route_duration_minutes * 1.5,
            max_depot_duration_min * 2.5,
            900.0  # Minimum 900 minutes (15 hours)
        )
        
        logging.info(
            f"Relaxed constraints: distance={relaxed_distance:.1f}km (was {constraints.max_distance_per_route_km}km), "
            f"duration={relaxed_duration:.1f}min (was {constraints.max_route_duration_minutes}min)"
        )
        
        # Rebuild routing model with relaxed constraints
        routing = pywrapcp.RoutingModel(manager)
        
        def distance_callback_relaxed(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return distance_matrix[from_node][to_node]
        
        def duration_callback_relaxed(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return duration_matrix[from_node][to_node]
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback_relaxed)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        demand_evaluator = lambda index: 0 if manager.IndexToNode(index) == 0 else 1
        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_evaluator)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,
            [constraints.max_customers_per_route] * routing.vehicles(),
            True,
            "Capacity",
        )
        
        duration_callback_index = routing.RegisterTransitCallback(duration_callback_relaxed)
        routing.AddDimension(
            duration_callback_index,
            0,
            _seconds_from_minutes(relaxed_duration),
            True,
            "Time",
        )
        
        time_dimension = routing.GetDimensionOrDie("Time")
        
        routing.AddDimension(
            transit_callback_index,
            0,
            int(relaxed_distance * 1000),
            True,
            "Distance",
        )
        
        distance_dimension = routing.GetDimensionOrDie("Distance")
        
        # Try solving again with relaxed constraints
        assignment = routing.SolveWithParameters(search_parameters)
        
        if not assignment:
            # Still infeasible even with relaxed constraints
            logging.error(
                f"Routing problem still infeasible for zone {zone_id} even with relaxed constraints. "
                f"Customers: {len(customers)}, "
                f"Max per route: {constraints.max_customers_per_route}, "
                f"Relaxed duration: {relaxed_duration:.1f}min, "
                f"Relaxed distance: {relaxed_distance:.1f}km"
            )
            return RoutingResult(
                zone_id=zone_id,
                plans=[],
                metadata={
                    "status": "infeasible",
                    "reason": "Solver could not find a feasible solution even with relaxed constraints. "
                              "The problem may require more vehicles or have unreachable customers.",
                    "customers": len(customers),
                    "original_constraints": {
                        "max_customers_per_route": constraints.max_customers_per_route,
                        "max_route_duration_minutes": constraints.max_route_duration_minutes,
                        "max_distance_per_route_km": constraints.max_distance_per_route_km,
                    },
                    "relaxed_constraints": {
                        "max_route_duration_minutes": relaxed_duration,
                        "max_distance_per_route_km": relaxed_distance,
                    },
                    "max_depot_distance_km": max_depot_distance_km,
                    "max_depot_duration_min": max_depot_duration_min,
                }
            )
        else:
            logging.info(f"Successfully found solution with relaxed constraints for zone {zone_id}")
            # Store relaxed constraint info for metadata
            used_relaxed_constraints = True
            relaxed_distance_limit = relaxed_distance
            relaxed_duration_limit = relaxed_duration

    plans: list[RoutePlan] = []
    total_routes = routing.vehicles()
    routes_with_customers = 0
    
    for vehicle_id in range(total_routes):
        index = routing.Start(vehicle_id)
        stops: list[RouteStop] = []
        sequence = 1

        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            previous_index = index
            index = assignment.Value(routing.NextVar(index))
            next_node = manager.IndexToNode(index)
            step_distance = distance_matrix[node_index][next_node] / 1000.0
            step_duration = duration_matrix[node_index][next_node] / 60.0

            # Only add customer stops (skip depot node 0)
            if node_index != 0 and node_index - 1 < len(customers):
                customer = customers[node_index - 1]
                stops.append(
                    RouteStop(
                        customer_id=customer.customer_id,
                        sequence=sequence,
                        arrival_min=assignment.Value(time_dimension.CumulVar(previous_index)) / 60.0,
                        distance_from_prev_km=step_distance,
                    )
                )
                sequence += 1

        # Only create route plan if it has customers
        if stops:
            routes_with_customers += 1
            day = working_days[len(plans) % len(working_days)]
            route_distance = assignment.Value(distance_dimension.CumulVar(routing.End(vehicle_id))) / 1000.0
            route_duration = assignment.Value(time_dimension.CumulVar(routing.End(vehicle_id))) / 60.0
            violations: dict[str, float] = {}
            if route_distance > constraints.max_distance_per_route_km:
                violations["distance_km"] = route_distance - constraints.max_distance_per_route_km
            if route_duration > constraints.max_route_duration_minutes:
                violations["duration_min"] = route_duration - constraints.max_route_duration_minutes
            if len(stops) < constraints.min_customers_per_route:
                violations["min_customers"] = constraints.min_customers_per_route - len(stops)
            plan = RoutePlan(
                route_id=f"{zone_id}_R{vehicle_id + 1:02d}",
                day=day,
                total_distance_km=route_distance,
                total_duration_min=route_duration,
                customer_count=len(stops),
                stops=stops,
                constraint_violations=violations,
            )
            plans.append(plan)
    
    # If solver found a solution but no routes have customers, it's still a problem
    if not plans and routes_with_customers == 0:
        import logging
        logging.warning(
            f"Solver found solution but no routes contain customers. "
            f"Zone: {zone_id}, Customers: {len(customers)}, Vehicles: {total_routes}"
        )

    metadata = {
        "status": "optimal",
        "vehicles": total_routes,
    }
    
    # Add relaxed constraint info if used
    if used_relaxed_constraints:
        metadata["constraints_relaxed"] = True
        metadata["original_constraints"] = {
            "max_route_duration_minutes": constraints.max_route_duration_minutes,
            "max_distance_per_route_km": constraints.max_distance_per_route_km,
        }
        metadata["relaxed_constraints"] = {
            "max_route_duration_minutes": relaxed_duration_limit,
            "max_distance_per_route_km": relaxed_distance_limit,
        }
    else:
        metadata["constraints_relaxed"] = False
    
    return RoutingResult(zone_id=zone_id, plans=plans, metadata=metadata)
