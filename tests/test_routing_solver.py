from src.app.models.domain import Customer
from src.app.services.routing.solver import SolverConstraints, solve_vrp


def _customer(cid: str, lat: float, lon: float) -> Customer:
    return Customer(
        area=None,
        region=None,
        city="TestCity",
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


def test_solve_vrp_simple():
    customers = [_customer("C1", 21.5, 39.2), _customer("C2", 21.55, 39.25)]
    osrm_table = {
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
    result = solve_vrp(zone_id="ZONE1", customers=customers, osrm_table=osrm_table, working_days=("SUN",))

    assert result.zone_id == "ZONE1"
    assert len(result.plans) >= 1
    first_plan = result.plans[0]
    assert first_plan.customer_count == 2
    assert first_plan.total_distance_km > 0
    assert first_plan.total_duration_min > 0
