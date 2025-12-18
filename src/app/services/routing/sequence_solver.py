"""OR-Tools sequence optimization for pre-assigned routes.

This module handles the case where customers are manually assigned to routes,
and we only need to optimize the visit sequence within each route using OSRM distances.
"""

from __future__ import annotations

import math
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


def solve_sequence_only(
    *,
    zone_id: str,
    route_assignments: dict[str, tuple[str, list[Customer]]],  # route_id -> (day, customers)
    customer_to_index: dict[str, int],  # Maps customer_id to index in OSRM matrix (0=depot, 1+=customers)
    osrm_table: dict,
    working_days: Sequence[str] | None = None,
) -> RoutingResult:
    """Optimize visit sequence for pre-assigned routes using OR-Tools TSP solver.
    
    This function takes customers that are already assigned to routes and
    only optimizes the visit sequence within each route to minimize travel distance.
    OSRM provides the distance matrix, OR-Tools solves the TSP.
    
    Args:
        zone_id: Zone identifier
        route_assignments: Dictionary mapping route_id to (day, list of customers)
        customer_to_index: Maps customer_id to its index in the OSRM matrix
        osrm_table: OSRM distance/duration matrix (depot at index 0, customers at 1+)
        working_days: List of working days (defaults to settings)
        
    Returns:
        RoutingResult with optimized sequences for each route
    """
    if not ORTOOLS_AVAILABLE:
        raise ImportError(
            "OR-Tools is not installed. Routing optimization requires OR-Tools. "
            "Install Python 3.11 or 3.12 to use routing features."
        )
    
    from .solver import _prepare_matrices, _seconds_from_minutes
    
    working_days = tuple(working_days or settings.working_days)
    
    # Prepare matrices from OSRM
    duration_matrix, distance_matrix = _prepare_matrices(osrm_table)
    
    # Validate matrices
    if not duration_matrix or not distance_matrix:
        raise ValueError("Empty duration or distance matrix from OSRM.")
    if len(duration_matrix) != len(distance_matrix):
        raise ValueError(f"Matrix size mismatch: durations={len(duration_matrix)}, distances={len(distance_matrix)}")
    
    plans: list[RoutePlan] = []
    
    # Process each route separately (each route is a separate TSP problem)
    for route_idx, (route_id, (day, route_customers)) in enumerate(route_assignments.items()):
        if not route_customers:
            continue
        
        # Get matrix indices for this route's customers
        # Map: route_matrix_index -> (customer, full_matrix_index)
        route_index_map: list[tuple[Customer, int]] = [(None, 0)]  # Depot at route index 0, full index 0
        for customer in route_customers:
            if customer.customer_id in customer_to_index:
                full_idx = customer_to_index[customer.customer_id]
                route_index_map.append((customer, full_idx))
            else:
                import logging
                logging.warning(f"Customer {customer.customer_id} not found in OSRM matrix, skipping")
                continue
        
        if len(route_index_map) < 2:  # Need at least depot + 1 customer
            continue
        
        # Create sub-matrix for this route (depot + route customers)
        n_route = len(route_index_map)
        route_distance_matrix = [[0] * n_route for _ in range(n_route)]
        route_duration_matrix = [[0] * n_route for _ in range(n_route)]
        
        for i, (_, full_idx_i) in enumerate(route_index_map):
            for j, (_, full_idx_j) in enumerate(route_index_map):
                route_distance_matrix[i][j] = distance_matrix[full_idx_i][full_idx_j]
                route_duration_matrix[i][j] = duration_matrix[full_idx_i][full_idx_j]
        
        # Solve TSP for this route using OR-Tools
        # Single vehicle, depot at 0, optimize sequence
        manager = pywrapcp.RoutingIndexManager(n_route, 1, 0)
        routing = pywrapcp.RoutingModel(manager)
        
        def distance_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return route_distance_matrix[from_node][to_node]
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Add time dimension for tracking
        def duration_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return route_duration_matrix[from_node][to_node]
        
        duration_callback_index = routing.RegisterTransitCallback(duration_callback)
        routing.AddDimension(
            duration_callback_index,
            0,  # No slack
            999999999,  # Very large upper bound (no time constraint for sequence-only)
            True,  # Start cumul to zero
            "Time",
        )
        
        time_dimension = routing.GetDimensionOrDie("Time")
        
        # Solve with OR-Tools
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.FromSeconds(settings.solver_time_limit_seconds)
        
        assignment = routing.SolveWithParameters(search_parameters)
        
        if not assignment:
            import logging
            logging.warning(f"Could not solve sequence for route {route_id}, using default order")
            # Fallback: use original order
            stops = []
            total_distance = 0.0
            total_duration = 0.0
            prev_idx = 0  # Depot
            
            for seq, customer in enumerate(route_customers, start=1):
                if customer.customer_id not in customer_to_index:
                    continue
                customer_idx = customer_to_index[customer.customer_id]
                dist_km = distance_matrix[prev_idx][customer_idx] / 1000.0
                dur_min = duration_matrix[prev_idx][customer_idx] / 60.0
                total_distance += dist_km
                total_duration += dur_min
                
                stops.append(
                    RouteStop(
                        customer_id=customer.customer_id,
                        sequence=seq,
                        arrival_min=total_duration,
                        distance_from_prev_km=dist_km,
                    )
                )
                prev_idx = customer_idx
            
            plans.append(
                RoutePlan(
                    route_id=route_id,
                    day=day,
                    total_distance_km=total_distance,
                    total_duration_min=total_duration,
                    customer_count=len(stops),
                    stops=stops,
                    constraint_violations={},
                )
            )
            continue
        
        # Extract optimized sequence
        stops: list[RouteStop] = []
        index = routing.Start(0)
        sequence = 1
        total_distance = 0.0
        total_duration = 0.0
        last_route_idx = 0  # Track last route index for return to depot
        
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            previous_index = index
            index = assignment.Value(routing.NextVar(index))
            next_node = manager.IndexToNode(index)
            
            # Skip depot (node 0 in route matrix)
            if node_index != 0:
                # Get customer from route_index_map
                customer, _ = route_index_map[node_index]
                if customer:
                    # Calculate distance and duration from previous stop
                    prev_route_idx = manager.IndexToNode(previous_index)
                    step_distance = route_distance_matrix[prev_route_idx][node_index] / 1000.0
                    step_duration = route_duration_matrix[prev_route_idx][node_index] / 60.0
                    total_distance += step_distance
                    total_duration += step_duration
                    
                    stops.append(
                        RouteStop(
                            customer_id=customer.customer_id,
                            sequence=sequence,
                            arrival_min=assignment.Value(time_dimension.CumulVar(previous_index)) / 60.0,
                            distance_from_prev_km=step_distance,
                        )
                    )
                    sequence += 1
                    last_route_idx = node_index
        
        # Add return to depot distance
        if stops and last_route_idx > 0:
            _, last_full_idx = route_index_map[last_route_idx]
            return_distance = distance_matrix[last_full_idx][0] / 1000.0
            return_duration = duration_matrix[last_full_idx][0] / 60.0
            total_distance += return_distance
            total_duration += return_duration
        
        plans.append(
            RoutePlan(
                route_id=route_id,
                day=day,
                total_distance_km=total_distance,
                total_duration_min=total_duration,
                customer_count=len(stops),
                stops=stops,
                constraint_violations={},
            )
        )
    
    metadata = {
        "status": "optimal",
        "vehicles": len(plans),
        "optimization_mode": "sequence_only",
        "description": "Sequence optimized using OR-Tools with OSRM distance matrix",
    }
    
    return RoutingResult(zone_id=zone_id, plans=plans, metadata=metadata)
