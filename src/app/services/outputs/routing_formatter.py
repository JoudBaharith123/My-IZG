"""Serializers for routing outputs."""

from __future__ import annotations

import csv
import io
from dataclasses import asdict
from typing import Sequence

from ..routing.models import RoutePlan, RoutingResult


def routing_result_to_json(result: RoutingResult) -> dict:
    return {
        "zone_id": result.zone_id,
        "metadata": result.metadata,
        "plans": [
            {
                "route_id": plan.route_id,
                "day": plan.day,
                "total_distance_km": plan.total_distance_km,
                "total_duration_min": plan.total_duration_min,
                "customer_count": plan.customer_count,
                "constraint_violations": plan.constraint_violations,
                "stops": [asdict(stop) for stop in plan.stops],
            }
            for plan in result.plans
        ],
    }


def routing_result_to_csv(result: RoutingResult) -> str:
    buffer = io.StringIO()
    fieldnames = [
        "route_id",
        "day",
        "sequence",
        "customer_id",
        "arrival_min",
        "distance_from_prev_km",
        "total_distance_km",
        "total_duration_min",
        "customer_count",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for plan in result.plans:
        for stop in plan.stops:
            writer.writerow(
                {
                    "route_id": plan.route_id,
                    "day": plan.day,
                    "sequence": stop.sequence,
                    "customer_id": stop.customer_id,
                    "arrival_min": stop.arrival_min,
                    "distance_from_prev_km": stop.distance_from_prev_km,
                    "total_distance_km": plan.total_distance_km,
                    "total_duration_min": plan.total_duration_min,
                    "customer_count": plan.customer_count,
                }
            )
    return buffer.getvalue()
