"""GeoJSON/EasyTerritory format export utilities."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List


def generate_zone_color(index: int) -> str:
    """Generate distinct colors for zones."""
    colors = [
        "#02d8e0", "#e0003e", "#38e000", "#0000c1", "#e0e005",
        "#611cc7", "#e0af00", "#13aae0", "#a4d819", "#00e0bb",
        "#e000a2", "#e000e0", "#09e0e0", "#e0002f", "#22e000",
        "#15dde0", "#e00017", "#08e000", "#3100e0", "#e0bb0b",
    ]
    return colors[index % len(colors)]


def polygon_to_wkt(coordinates: List[List[float]]) -> str:
    """Convert polygon coordinates to WKT format.

    Args:
        coordinates: List of [lat, lon] pairs

    Returns:
        WKT POLYGON string (in lon lat order as per WKT spec)
    """
    if not coordinates or len(coordinates) < 3:
        raise ValueError("Polygon must have at least 3 coordinates")

    # Ensure polygon is closed
    if coordinates[0] != coordinates[-1]:
        coordinates = coordinates + [coordinates[0]]

    # WKT uses lon,lat order (x,y)
    coord_pairs = [f"{lon} {lat}" for lat, lon in coordinates]
    return f"POLYGON(({','.join(coord_pairs)}))"


def linestring_to_wkt(coordinates: List[List[float]]) -> str:
    """Convert linestring coordinates to WKT format.

    Args:
        coordinates: List of [lat, lon] pairs

    Returns:
        WKT LINESTRING string
    """
    if not coordinates or len(coordinates) < 2:
        raise ValueError("LineString must have at least 2 coordinates")

    # WKT uses lon,lat order (x,y)
    coord_pairs = [f"{lon} {lat}" for lat, lon in coordinates]
    return f"LINESTRING({','.join(coord_pairs)})"


def export_zones_to_easyterritory(
    zones_response: Dict[str, Any],
    city: str,
    method: str,
) -> List[Dict[str, Any]]:
    """Convert zone generation response to EasyTerritory JSON format.

    Args:
        zones_response: Response from zone generation
        city: City name
        method: Zoning method used

    Returns:
        List of feature objects in EasyTerritory format
    """
    features: List[Dict[str, Any]] = []

    # Get map overlays (polygons)
    map_overlays = zones_response.get("metadata", {}).get("map_overlays", {})
    polygons = map_overlays.get("polygons", [])

    for idx, polygon in enumerate(polygons):
        zone_id = polygon.get("zone_id", f"ZONE_{idx + 1}")
        coordinates = polygon.get("coordinates", [])

        if len(coordinates) < 3:
            continue

        # Convert to WKT
        try:
            wkt = polygon_to_wkt(coordinates)
        except ValueError:
            continue

        # Calculate centroid
        centroid = polygon.get("centroid")
        if not centroid:
            # Simple centroid calculation
            avg_lat = sum(c[0] for c in coordinates) / len(coordinates)
            avg_lon = sum(c[1] for c in coordinates) / len(coordinates)
            centroid = [avg_lat, avg_lon]

        feature = {
            "id": str(uuid.uuid4()),
            "name": zone_id,
            "group": city.upper(),
            "featureClass": "2",
            "wkt": wkt,
            "json": json.dumps({
                "type": method,
                "subType": None,
                "labelPoint": {"_x": centroid[1], "_y": centroid[0]}
            }),
            "visible": True,
            "symbology": {
                "fillColor": generate_zone_color(idx),
                "fillOpacity": 0.33,
                "lineColor": "black",
                "lineWidth": 2,
                "lineOpacity": 0.5,
                "scale": None
            },
            "styledGeom": None,
            "notes": f"tag : {city.upper()}|{zone_id}\ngroup : {city.upper()}\nname : {zone_id}\nmethod : {method}\n",
            "nodeTags": [],
            "nameTagPlacementPoint": None,
            "simplificationMeters": 0,
            "modifiedTimestamp": 0,
            "managerId": None,
            "collapsed": True,
            "locked": None
        }
        features.append(feature)

    return features


def export_routes_to_easyterritory(
    routes_response: Dict[str, Any],
    city: str,
    zone: str,
) -> List[Dict[str, Any]]:
    """Convert route optimization response to EasyTerritory JSON format.

    Args:
        routes_response: Response from route optimization
        city: City name
        zone: Zone identifier

    Returns:
        List of feature objects in EasyTerritory format
    """
    features: List[Dict[str, Any]] = []

    plans = routes_response.get("plans", [])

    for idx, plan in enumerate(plans):
        route_name = f"Route {idx + 1}"
        route_id = f"{zone}_{route_name.replace(' ', '_')}"

        # Get route coordinates from stops
        coordinates = []
        for stop in plan.get("stops", []):
            customer = stop.get("customer", {})
            lat = customer.get("latitude")
            lon = customer.get("longitude")
            if lat is not None and lon is not None:
                coordinates.append([lat, lon])

        if len(coordinates) < 2:
            continue

        # Create WKT LineString for route
        try:
            wkt = linestring_to_wkt(coordinates)
        except ValueError:
            continue

        # Calculate midpoint for label
        mid_idx = len(coordinates) // 2
        label_point = coordinates[mid_idx]

        feature = {
            "id": str(uuid.uuid4()),
            "name": route_name,
            "group": zone.upper(),
            "featureClass": "1",  # Route/line feature
            "wkt": wkt,
            "json": json.dumps({
                "type": "optimized",
                "subType": "vehicle_route",
                "labelPoint": {"_x": label_point[1], "_y": label_point[0]},
                "metrics": {
                    "totalDistance": plan.get("total_distance_km"),
                    "totalDuration": plan.get("total_duration_minutes"),
                    "stopCount": len(plan.get("stops", [])),
                }
            }),
            "visible": True,
            "symbology": {
                "fillColor": generate_zone_color(idx),
                "fillOpacity": 0.5,
                "lineColor": generate_zone_color(idx),
                "lineWidth": 3,
                "lineOpacity": 0.8,
                "scale": None
            },
            "styledGeom": None,
            "notes": f"tag : {zone.upper()}|{route_name}\ngroup : {zone.upper()}\nname : {route_name}\nstops : {len(plan.get('stops', []))}\ndistance : {plan.get('total_distance_km', 0):.2f} km\n",
            "nodeTags": [],
            "nameTagPlacementPoint": None,
            "simplificationMeters": 0,
            "modifiedTimestamp": 0,
            "managerId": None,
            "collapsed": True,
            "locked": None
        }
        features.append(feature)

    return features


def save_easyterritory_json(features: List[Dict[str, Any]], output_path: Path) -> None:
    """Save features to EasyTerritory JSON format.

    Args:
        features: List of feature objects
        output_path: Path to save JSON file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(features, f, indent=2, ensure_ascii=False)
