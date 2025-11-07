from typing import Dict, Tuple

import pytest

from src.app.models.domain import Customer, Depot
from src.app.schemas.zoning import ZoningRequest
from src.app.persistence.filesystem import FileStorage
from src.app.services.zoning import service as zoning_service


def _sample_customer(customer_id: str, lat: float, lon: float) -> Customer:
    raw = {
        "CusId": customer_id,
        "CusName": f"Customer {customer_id}",
        "Latitude": f"{lat}",
        "Longitude": f"{lon}",
    }
    return Customer(
        area="Area",
        region="Region",
        city="Jeddah",
        zone=None,
        agent_id=None,
        agent_name=None,
        customer_id=customer_id,
        customer_name=f"Customer {customer_id}",
        latitude=lat,
        longitude=lon,
        status="ACTIVE",
        raw=raw,
    )


@pytest.fixture(autouse=True)
def clear_customer_cache():
    from src.app.data.customers_repository import load_customers

    load_customers.cache_clear()
    yield
    load_customers.cache_clear()


def test_process_zoning_request_persists_outputs(tmp_path, monkeypatch):
    customers = (
        _sample_customer("C001", 21.5, 39.2),
        _sample_customer("C002", 21.6, 39.3),
    )
    depot = Depot(code="JEDDAH", latitude=21.5, longitude=39.2)

    monkeypatch.setattr(
        zoning_service, "get_customers_for_location", lambda city: customers
    )
    monkeypatch.setattr(zoning_service, "resolve_depot", lambda city: depot)
    monkeypatch.setattr(zoning_service, "FileStorage", lambda: FileStorage(root=tmp_path))

    request = ZoningRequest(city="Jeddah", method="polar", target_zones=2)
    response = zoning_service.process_zoning_request(request, persist=True)

    assert response.city == "Jeddah"
    assert response.method == "polar"
    assert len(response.assignments) == len(customers)

    outputs_dir = tmp_path / "outputs"
    subdirs = list(outputs_dir.iterdir())
    assert len(subdirs) == 1
    run_dir = subdirs[0]

    summary = (run_dir / "summary.json").read_text(encoding="utf-8")
    assignments = (run_dir / "assignments.csv").read_text(encoding="utf-8")

    assert '"city": "Jeddah"' in summary
    assert assignments.startswith("customer_id")
    assert "C001" in assignments and "C002" in assignments


def test_process_zoning_request_manual_polygons_include_overlay(monkeypatch):
    customers = (
        _sample_customer("C001", 21.50, 39.20),
        _sample_customer("C002", 21.55, 39.22),
        _sample_customer("C003", 21.52, 39.24),
    )
    depot = Depot(code="JEDDAH", latitude=21.5, longitude=39.2)

    monkeypatch.setattr(zoning_service, "get_customers_for_location", lambda city: customers)
    monkeypatch.setattr(zoning_service, "resolve_depot", lambda city: depot)

    request = ZoningRequest(
        city="Jeddah",
        method="manual",
        polygons=[
            {
                "zone_id": "MANUAL_01",
                "coordinates": [
                    (21.45, 39.15),
                    (21.65, 39.15),
                    (21.55, 39.30),
                ],
            }
        ],
    )

    response = zoning_service.process_zoning_request(request, persist=False)

    overlays = response.metadata.get("map_overlays", {}).get("polygons", [])
    assert overlays, "Expected manual polygon overlays in metadata"
    overlay = overlays[0]
    assert overlay["zone_id"] == "MANUAL_01"
    assert overlay["source"] == "manual"
    assert len(overlay["coordinates"]) >= 4  # polygon should be closed


def test_process_zoning_request_generates_convex_hull_overlay(monkeypatch):
    customers = (
        _sample_customer("C001", 21.50, 39.20),
        _sample_customer("C002", 21.60, 39.30),
        _sample_customer("C003", 21.55, 39.25),
        _sample_customer("C004", 21.58, 39.28),
    )
    depot = Depot(code="JEDDAH", latitude=21.5, longitude=39.2)

    monkeypatch.setattr(zoning_service, "get_customers_for_location", lambda city: customers)
    monkeypatch.setattr(zoning_service, "resolve_depot", lambda city: depot)

    request = ZoningRequest(city="Jeddah", method="clustering", target_zones=1)
    response = zoning_service.process_zoning_request(request, persist=False)

    overlays = response.metadata.get("map_overlays", {}).get("polygons", [])
    assert overlays, "Expected convex hull overlays in metadata"
    hull = overlays[0]
    assert hull["source"] == "convex_hull"
    assert len(hull["coordinates"]) >= 4
