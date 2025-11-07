from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.app.main import create_app
from src.app.models.domain import Customer, Depot
from src.app.schemas.routing import RoutingRequest
from src.app.schemas.zoning import ZoningRequest


def _customer(cid: str, lat: float, lon: float, city: str = "Jeddah", zone: str | None = None) -> Customer:
    return Customer(
        area="Area",
        region="Region",
        city=city,
        zone=zone,
        agent_id=None,
        agent_name=None,
        customer_id=cid,
        customer_name=f"Customer {cid}",
        latitude=lat,
        longitude=lon,
        status="ACTIVE",
        raw={"CusId": cid, "Latitude": lat, "Longitude": lon},
    )


class DummyOSRM:
    def table(self, coordinates):
        # square matrix sized to coordinates length
        count = len(coordinates)
        durations = [[0 if i == j else 600 for j in range(count)] for i in range(count)]
        distances = [[0 if i == j else 1000 for j in range(count)] for i in range(count)]
        return {"durations": durations, "distances": distances}


@pytest.fixture(autouse=True)
def clear_customer_cache():
    from src.app.data.customers_repository import load_customers

    load_customers.cache_clear()
    yield
    load_customers.cache_clear()


@pytest.fixture
def api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = create_app()
    client = TestClient(app)

    # ensure filesystem writes go to tmpdir for all services
    from src.app.services.zoning import service as zoning_service
    from src.app.services.routing import service as routing_service
    from src.app.persistence.filesystem import FileStorage

    monkeypatch.setattr(zoning_service, "FileStorage", lambda: FileStorage(root=tmp_path))
    monkeypatch.setattr(routing_service, "FileStorage", lambda: FileStorage(root=tmp_path))

    return client


def test_zoning_endpoint_polar(api_client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from src.app.services.zoning import service as zoning_service

    customers = [_customer("C1", 21.5, 39.2), _customer("C2", 21.55, 39.25)]
    depot = Depot(code="JEDDAH", latitude=21.5, longitude=39.2)

    monkeypatch.setattr(zoning_service, "get_customers_for_location", lambda city: customers)
    monkeypatch.setattr(zoning_service, "resolve_depot", lambda city: depot)

    request = ZoningRequest(city="Jeddah", method="polar", target_zones=2, balance=True)
    response = api_client.post("/api/zones/generate", json=request.model_dump())

    assert response.status_code == 200
    payload = response.json()
    assert payload["city"] == "Jeddah"
    assert len(payload["assignments"]) == 2
    assert "balancing" in payload["metadata"]

    output_dirs = list((tmp_path / "outputs").glob("zones_polar_*"))
    assert output_dirs
    run_dir = output_dirs[0]
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "assignments.csv").exists()


def test_routing_endpoint_optimize(api_client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from src.app.services.routing import service as routing_service
    from src.app.services.routing import osrm_client as osrm_module

    customers = [_customer("C1", 21.5, 39.2, zone="ZONE1"), _customer("C2", 21.55, 39.25, zone="ZONE1")]
    depot = Depot(code="CITY", latitude=21.5, longitude=39.2)

    monkeypatch.setattr(routing_service, "get_customers_for_location", lambda zone: customers)
    monkeypatch.setattr(routing_service, "resolve_depot", lambda city: depot)
    monkeypatch.setattr(osrm_module, "OSRMClient", lambda *args, **kwargs: DummyOSRM())
    monkeypatch.setattr(routing_service, "OSRMClient", lambda *args, **kwargs: DummyOSRM())

    request = RoutingRequest(city="City", zone_id="ZONE1")
    response = api_client.post("/api/routes/optimize", json=request.model_dump())

    assert response.status_code == 200
    payload = response.json()
    assert payload["zone_id"] == "ZONE1"
    assert payload["plans"]

    output_dirs = list((tmp_path / "outputs").glob("routes_ZONE1_*"))
    assert output_dirs
    run_dir = output_dirs[0]
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "assignments.csv").exists()


def test_customer_locations_endpoint_supports_pagination(api_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    from src.app.data import customers_repository

    sample_customers = [
        _customer(f"C{i+1}", 21.50 + (i * 0.001), 39.20 + (i * 0.001), zone="Z1" if i % 2 == 0 else "Z2")
        for i in range(105)
    ]

    def fake_loader(source=None):
        return tuple(sample_customers)

    fake_loader.cache_clear = lambda: None  # mimic lru_cache API for fixtures

    monkeypatch.setattr(customers_repository, "load_customers", fake_loader)

    from src.app.services.customers import stats as customers_stats

    monkeypatch.setattr(customers_stats, "load_customers", fake_loader)

    page_1 = api_client.get("/api/customers/locations", params={"city": "Jeddah", "page": 1, "page_size": 100})
    assert page_1.status_code == 200
    payload1 = page_1.json()
    assert payload1["page"] == 1
    assert payload1["page_size"] == 100
    assert payload1["total"] == 105
    assert payload1["has_next_page"] is True
    assert len(payload1["items"]) == 100
    assert payload1["items"][0]["customer_id"] == "C1"

    page_2 = api_client.get("/api/customers/locations", params={"city": "Jeddah", "page": 2, "page_size": 100})
    assert page_2.status_code == 200
    payload2 = page_2.json()
    assert payload2["page"] == 2
    assert len(payload2["items"]) == 5
    assert payload2["items"][0]["customer_id"] == "C101"

    zone_filter = api_client.get("/api/customers/locations", params={"city": "Jeddah", "zone": "Z2", "page": 1, "page_size": 100})
    assert zone_filter.status_code == 200
    zone_payload = zone_filter.json()
    assert zone_payload["total"] == 52
    assert zone_payload["has_next_page"] is False
    assert zone_payload["items"][0]["customer_id"] == "C2"
    assert zone_payload["items"][-1]["customer_id"] == "C104"
