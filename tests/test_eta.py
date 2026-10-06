from lib.osrm import calculate_eta_to_stop


def test_calculate_eta_to_stop_arriving():
    # Stop location very close (< 0.05 mi)
    res = calculate_eta_to_stop(
        bus_lat=41.01436,
        bus_lon=-73.85389,
        bus_speed_mph=15.0,
        stop_lat=41.01436,
        stop_lon=-73.85389,
    )
    assert res["eta_minutes"] == 0
    assert res["eta_text"] == "Bus at stop"
    assert res["distance_miles"] == 0.0


def test_calculate_eta_to_stop_moving():
    # Bus ~1 mile away moving at 30 mph -> ~2 mins
    res = calculate_eta_to_stop(
        bus_lat=41.00000,
        bus_lon=-73.85389,
        bus_speed_mph=30.0,
        stop_lat=41.01436,
        stop_lon=-73.85389,
    )
    assert res["eta_minutes"] > 0
    assert "mins" in res["eta_text"] or "Arriving" in res["eta_text"]
    assert res["distance_miles"] > 0.5


def test_calculate_eta_to_stop_missing_stop():
    res = calculate_eta_to_stop(
        bus_lat=41.00000,
        bus_lon=-73.85389,
        bus_speed_mph=20.0,
        stop_lat=None,
        stop_lon=None,
    )
    assert res["eta_minutes"] is None
    assert res["eta_text"] == "Stop location unavailable"
