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
    durations = osrm_result.get("durations")
    distances = osrm_result.get("distances")
    if durations is None or distances is None:
        raise ValueError("OSRM table response missing durations or distances.")
    duration_matrix = [[int(value) if value is not None else 0 for value in row] for row in durations]
    distance_matrix = [[int(value) if value is not None else 0 for value in row] for row in distances]
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
    if not assignment:
        return RoutingResult(zone_id=zone_id, plans=[], metadata={"status": "infeasible"})

    plans: list[RoutePlan] = []
    total_routes = routing.vehicles()
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

        if stops:
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

    metadata = {
        "status": "optimal",
        "vehicles": total_routes,
    }
    return RoutingResult(zone_id=zone_id, plans=plans, metadata=metadata)
