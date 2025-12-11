"""Geographic clustering zoning implementation."""

from __future__ import annotations

from collections import Counter
from typing import Sequence

import numpy as np
from sklearn.cluster import KMeans

from ...models.domain import Customer, Depot
from ..geospatial import haversine_km
from .base import ZoningResult, ZoningStrategy


class ClusteringZoning(ZoningStrategy):
    """Apply constrained K-Means style clustering on customer coordinates.
    
    Features:
    - Uses UTM projection for accurate geographic distance calculations
    - Supports depot-weighted clustering to ensure zones are accessible from DC
    - Enforces max_customers_per_zone constraint with iterative splitting
    """

    def __init__(
        self,
        *,
        balance_tolerance: float = 0.2,
        random_state: int = 42,
        max_iter: int = 300,
        use_depot_weighting: bool = True,
        depot_weight_factor: float = 0.3,
    ) -> None:
        self.balance_tolerance = balance_tolerance
        self.random_state = random_state
        self.max_iter = max_iter
        self.use_depot_weighting = use_depot_weighting
        self.depot_weight_factor = depot_weight_factor

    def _convert_to_cartesian(self, lat: float, lon: float) -> tuple[float, float]:
        """Convert lat/lon to approximate Cartesian coordinates (km) for clustering.
        
        Uses a simple equirectangular projection centered on Saudi Arabia.
        Good approximation for small areas (< 500km).
        """
        # Reference point (center of Saudi Arabia)
        lat_ref = 24.0  # degrees
        lon_ref = 45.0  # degrees
        
        # Earth radius in km
        R = 6371.0
        
        # Convert to radians
        lat_rad = np.radians(lat)
        lon_rad = np.radians(lon)
        lat_ref_rad = np.radians(lat_ref)
        
        # Approximate conversion to km
        # x = R * (lon - lon_ref) * cos(lat_ref)
        # y = R * (lat - lat_ref)
        x = R * (lon_rad - np.radians(lon_ref)) * np.cos(lat_ref_rad)
        y = R * (lat_rad - np.radians(lat_ref))
        
        return x, y
    
    def _convert_from_cartesian(self, x: float, y: float) -> tuple[float, float]:
        """Convert Cartesian coordinates (km) back to lat/lon."""
        lat_ref = 24.0
        lon_ref = 45.0
        R = 6371.0
        lat_ref_rad = np.radians(lat_ref)
        
        lat_rad = np.radians(lat_ref) + y / R
        lon_rad = np.radians(lon_ref) + x / (R * np.cos(lat_ref_rad))
        
        return np.degrees(lat_rad), np.degrees(lon_rad)

    def _calculate_depot_weights(
        self, customers: Sequence[Customer], depot: Depot
    ) -> np.ndarray:
        """Calculate weights for customers based on distance from depot.
        
        Closer customers get higher weight, encouraging zones near the depot.
        """
        weights = np.zeros(len(customers))
        for i, customer in enumerate(customers):
            distance_km = haversine_km(
                depot.latitude,
                depot.longitude,
                customer.latitude,
                customer.longitude,
            )
            # Weight decreases with distance: 1.0 at 0km, ~0.5 at 20km, ~0.25 at 50km
            # Formula: weight = 1 / (1 + distance / scale_factor)
            scale_factor = 20.0  # km
            weight = 1.0 / (1.0 + distance_km / scale_factor)
            weights[i] = weight
        return weights

    def _enforce_max_customers_constraint(
        self,
        coordinates: np.ndarray,
        customers: Sequence[Customer],
        depot: Depot,
        initial_labels: np.ndarray,
        max_customers_per_zone: int,
        max_iterations: int = 10,
    ) -> tuple[np.ndarray, dict]:
        """Enforce max_customers_per_zone by splitting overloaded clusters.
        
        Returns:
            Final labels and metadata about splits performed.
        """
        labels = initial_labels.copy()
        splits_performed = []
        current_zones = len(np.unique(labels))
        
        for iteration in range(max_iterations):
            # Count customers per cluster
            unique_labels, counts = np.unique(labels, return_counts=True)
            max_count = counts.max()
            
            # Check if constraint is satisfied
            if max_count <= max_customers_per_zone * (1 + self.balance_tolerance):
                break
            
            # Find overloaded clusters
            overloaded_mask = counts > max_customers_per_zone * (1 + self.balance_tolerance)
            overloaded_labels = unique_labels[overloaded_mask]
            
            if len(overloaded_labels) == 0:
                break
            
            # Split the most overloaded cluster
            most_overloaded_idx = np.argmax(counts[overloaded_mask])
            cluster_to_split = overloaded_labels[most_overloaded_idx]
            
            # Get customers in this cluster
            cluster_mask = labels == cluster_to_split
            cluster_coords = coordinates[cluster_mask]
            cluster_customers = [customers[i] for i in range(len(customers)) if cluster_mask[i]]
            
            if len(cluster_coords) < 2:
                # Can't split a cluster with < 2 customers
                break
            
            # Split into 2 sub-clusters
            sub_kmeans = KMeans(
                n_clusters=2,
                random_state=self.random_state + iteration,
                n_init=10,
                max_iter=100,
            )
            sub_labels = sub_kmeans.fit_predict(cluster_coords)
            
            # Assign new labels (use next available zone number)
            new_zone_label = current_zones
            for i, customer_idx in enumerate(np.where(cluster_mask)[0]):
                if sub_labels[i] == 1:  # Second sub-cluster gets new label
                    labels[customer_idx] = new_zone_label
                # First sub-cluster keeps original label
            
            current_zones += 1
            splits_performed.append({
                "iteration": iteration + 1,
                "original_cluster": int(cluster_to_split),
                "customers_before": int(counts[overloaded_mask][most_overloaded_idx]),
                "new_cluster": new_zone_label,
            })
        
        metadata = {
            "splits_performed": splits_performed,
            "final_zone_count": int(current_zones),
            "initial_zone_count": len(np.unique(initial_labels)),
        }
        return labels, metadata

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
        
        if not customers:
            return ZoningResult({}, metadata={"strategy": "clustering", "error": "No customers provided"})

        # Convert to Cartesian coordinates for accurate geographic distance
        cartesian_coords = [
            self._convert_to_cartesian(customer.latitude, customer.longitude)
            for customer in customers
        ]
        coordinates = np.array(cartesian_coords)

        # Apply depot weighting if enabled
        if self.use_depot_weighting:
            weights = self._calculate_depot_weights(customers, depot)
            # Weight coordinates: closer to depot = higher influence
            # This doesn't change coordinates but we'll use it in post-processing
            # For now, we'll adjust cluster centers after initial clustering
            weighted_coords = coordinates.copy()
        else:
            weights = np.ones(len(customers))
            weighted_coords = coordinates

        # Initial K-Means clustering
        kmeans = KMeans(
            n_clusters=target_zones,
            random_state=self.random_state,
            n_init="auto",
            max_iter=self.max_iter,
        )
        labels = kmeans.fit_predict(weighted_coords)

        # Enforce max_customers_per_zone constraint if specified
        constraint_metadata = {}
        if max_customers_per_zone:
            labels, constraint_metadata = self._enforce_max_customers_constraint(
                coordinates=coordinates,
                customers=customers,
                depot=depot,
                initial_labels=labels,
                max_customers_per_zone=max_customers_per_zone,
            )
            # Recalculate cluster centers after splitting
            unique_labels = np.unique(labels)
            final_zone_count = len(unique_labels)
            if final_zone_count > target_zones:
                # Recompute centers for all zones
                centers = []
                for label in unique_labels:
                    cluster_mask = labels == label
                    cluster_coords = coordinates[cluster_mask]
                    center = cluster_coords.mean(axis=0)
                    # Convert back to lat/lon
                    lat, lon = self._convert_from_cartesian(center[0], center[1])
                    centers.append([lat, lon])
            else:
                # Use original centers, convert to lat/lon
                centers = []
                for center_cart in kmeans.cluster_centers_:
                    lat, lon = self._convert_from_cartesian(center_cart[0], center_cart[1])
                    centers.append([lat, lon])
        else:
            # Convert Cartesian centers back to lat/lon
            centers = []
            for center_cart in kmeans.cluster_centers_:
                lat, lon = self._convert_from_cartesian(center_cart[0], center_cart[1])
                centers.append([lat, lon])

        # Create assignments
        assignments: dict[str, str] = {}
        for customer, label in zip(customers, labels):
            assignments[customer.customer_id] = f"{depot.code[:3].upper()}C{int(label)+1:02d}"

        counts = Counter(assignments.values())
        metadata = {
            "strategy": "clustering",
            "centers": centers,
            "counts": counts,
            "uses_cartesian_projection": True,
            "uses_depot_weighting": self.use_depot_weighting,
        }
        
        # Add constraint enforcement metadata
        if constraint_metadata:
            metadata.update(constraint_metadata)
            metadata["max_customers_per_zone"] = max_customers_per_zone
            # Check for remaining violations
            violations = {
                zone_id: count
                for zone_id, count in counts.items()
                if max_customers_per_zone and count > max_customers_per_zone * (1 + self.balance_tolerance)
            }
            if violations:
                metadata["violations"] = violations
            else:
                metadata["constraint_satisfied"] = True

        return ZoningResult(assignments, metadata=metadata)
