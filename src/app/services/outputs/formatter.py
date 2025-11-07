"""Utilities to serialize zoning results into JSON/CSV artifacts."""

from __future__ import annotations

import csv
import io
from dataclasses import asdict
from typing import Sequence

from ...models.domain import Customer
from ...schemas.zoning import ZoningResponse


def zoning_response_to_json(response: ZoningResponse) -> dict:
    return response.model_dump()


def zoning_response_to_csv(response: ZoningResponse, customers: Sequence[Customer]) -> str:
    buffer = io.StringIO()
    fieldnames = ["customer_id", "customer_name", "zone_id"] + sorted(
        set(customers[0].raw.keys()) if customers else []
    )
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    response_map = response.assignments
    for customer in customers:
        writer.writerow(
            {
                "customer_id": customer.customer_id,
                "customer_name": customer.customer_name,
                "zone_id": response_map.get(customer.customer_id, ""),
                **customer.raw,
            }
        )
    return buffer.getvalue()
