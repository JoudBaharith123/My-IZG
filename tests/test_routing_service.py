from pathlib import Path

import pytest

from src.app.models.domain import Customer, Depot
from src.app.schemas.routing import RoutingRequest
from src.app.services.routing import service as routing_service


def _customer(cid: str, lat: float, lon: float) -> Customer:
    return Customer(
        area="Area",
        region="Region",
        city="City",
        zone="ZONE1",
        agent_id=None,
        agent_name=None,
        customer_id=cid,
        customer_name=f"Customer {cid}",
        latitude=lat,
        longitude=lon,
        status="ACTIVE",
        raw={"CusId": cid, "Latitude": lat, "Longitude": lon},
    )


@pytest.fixture(autouse=True)
def clear_customer_cache():
    from src.app.data.customers_repository import load_customers

    load_customers.cache_clear()
    yield
    load_customers.cache_clear()


def test_optimize_routes_persists_outputs(monkeypatch, tmp_path: Path):
    customers = [_customer("C1", 21.5, 39.2), _customer("C2", 21.55, 39.25)]
    depot = Depot(code="CITY", latitude=21.5, longitude=39.2)

    monkeypatch.setattr(routing_service, "get_customers_for_location", lambda zone: customers)
    monkeypatch.setattr(routing_service, "resolve_depot", lambda city: depot)

    class DummyOSRM:
        def table(self, coordinates):
            return {
                "durations": [
                    [0, 600, 900],
                    [600, 0, 300],
                    [900, 300, 0],
                ],
                "distances": [
                    [0, 1000, 1500],
                    [1000, 0, 500],
                    [1500, 500, 0],
                ],
            }

    monkeypatch.setattr(routing_service, "OSRMClient", lambda: DummyOSRM())
    original_storage = routing_service.FileStorage
    monkeypatch.setattr(routing_service, "FileStorage", lambda: original_storage(root=tmp_path))

    request = RoutingRequest(city="City", zone_id="ZONE1")
    response = routing_service.optimize_routes(request)

    assert response.zone_id == "ZONE1"
    assert response.plans
    overlays = response.metadata.get("map_overlays", {}).get("routes", [])
    assert overlays, "Expected route overlays in metadata"
    route_overlay = overlays[0]
    assert route_overlay["route_id"].startswith("ZONE1_R")
    assert len(route_overlay["coordinates"]) >= 3

    outputs_dir = tmp_path / "outputs"
    run_dirs = list(outputs_dir.iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "assignments.csv").exists()
