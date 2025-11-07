"""Geographic clustering zoning implementation."""

from __future__ import annotations

from collections import Counter
from typing import Sequence

import numpy as np
from sklearn.cluster import KMeans

from ...models.domain import Customer, Depot
from .base import ZoningResult, ZoningStrategy


class ClusteringZoning(ZoningStrategy):
    """Apply constrained K-Means style clustering on customer coordinates."""

    def __init__(
        self,
        *,
        balance_tolerance: float = 0.2,
        random_state: int = 42,
        max_iter: int = 300,
    ) -> None:
        self.balance_tolerance = balance_tolerance
        self.random_state = random_state
        self.max_iter = max_iter

    def generate(
        self,
        *,
        depot: Depot,
        customers: Sequence[Customer],
        target_zones: int,
        max_customers_per_zone: int | None = None,
    ) -> ZoningResult:
        if target_zones < 1:
            raise ValueError("target_zones must be >= 1")

        coordinates = np.array([[customer.latitude, customer.longitude] for customer in customers])
        kmeans = KMeans(
            n_clusters=target_zones,
            random_state=self.random_state,
            n_init="auto",
            max_iter=self.max_iter,
        )
        labels = kmeans.fit_predict(coordinates)

        assignments: dict[str, str] = {}
        for customer, label in zip(customers, labels):
            assignments[customer.customer_id] = f"{depot.code[:3].upper()}C{label+1:02d}"

        counts = Counter(assignments.values())
        metadata = {
            "strategy": "clustering",
            "centers": kmeans.cluster_centers_.tolist(),
            "counts": counts,
        }

        if max_customers_per_zone:
            metadata["max_customers_per_zone"] = max_customers_per_zone
            metadata["violations"] = {
                zone_id: count
                for zone_id, count in counts.items()
                if count > max_customers_per_zone * (1 + self.balance_tolerance)
            }
        return ZoningResult(assignments, metadata=metadata)
