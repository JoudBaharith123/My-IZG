from src.app.models.domain import Customer
from src.app.services.balancing.service import balance_assignments


def _customer(cid: str, zone: str, lat: float, lon: float) -> Customer:
    return Customer(
        area="Area",
        region="Region",
        city="City",
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


def test_balance_assignments_with_tolerance():
    customers = [
        _customer("C1", "Z1", 21.5, 39.2),
        _customer("C2", "Z1", 21.51, 39.21),
        _customer("C3", "Z1", 21.52, 39.22),
        _customer("C4", "Z2", 21.6, 39.3),
    ]
    assignments = {customer.customer_id: customer.zone or "" for customer in customers}

    result = balance_assignments(assignments, customers, tolerance=0.2)

    assert result.transfers  # expect at least one transfer
    assert result.counts_after["Z1"] <= result.counts_after["Z2"] + 1
