from datetime import datetime

from lastmile import transform as t
from lastmile.checks import run_checks

DAY = "2018-07-27"


def tiny(spark, travel=None):
    """One route: station ST then stops A, B. Departs 16:00:00 UTC."""
    routes = spark.createDataFrame([{
        "route_id": "R1", "station_code": "DXX1", "date_YYYY_MM_DD": DAY, "departure_time_utc": "16:00:00",
        "executor_capacity_cm3": 1e6, "route_score": "High",
        "stops": [
            {"stop_id": "ST", "lat": 34.0, "lng": -118.0, "type": "Station", "zone_id": None},
            {"stop_id": "A", "lat": 34.1, "lng": -118.1, "type": "Dropoff", "zone_id": "Z-1"},
            {"stop_id": "B", "lat": 34.2, "lng": -118.2, "type": "Dropoff", "zone_id": "Z-2"},
        ]}], t.ROUTES)
    pk = [
        # A: two packages, 60s + 40s of service
        ("R1", "A", "p1", "DELIVERED", None, None, 60.0, 10.0, 10.0, 10.0),
        ("R1", "A", "p2", "DELIVERED", "2018-07-27 16:00:00", "2018-07-27 16:15:00", 40.0, 10.0, 10.0, 10.0),
        # B: window closes 16:30, estimated arrival is 16:31:40, so late by 1m40s
        ("R1", "B", "p3", "DELIVERED", "2018-07-27 16:00:00", "2018-07-27 16:30:00", 30.0, 20.0, 10.0, 10.0),
        ("R1", "B", "p4", "DELIVERY_ATTEMPTED", None, None, 30.0, 5.0, 5.0, 5.0),
    ]
    packages = spark.createDataFrame(pk, t.PACKAGES)
    sequences = spark.createDataFrame([("R1", "ST", 0), ("R1", "A", 1), ("R1", "B", 2)], t.SEQUENCES)
    matrix = travel or {"ST": {"ST": 0.0, "A": 600.0, "B": 900.0},
                        "A": {"ST": 600.0, "A": 0.0, "B": 1000.0},
                        "B": {"ST": 900.0, "A": 1000.0, "B": 0.0}}
    travel_df = spark.createDataFrame([("R1", matrix)], t.TRAVEL)
    return routes, packages, sequences, travel_df


def test_arrival_estimate(spark):
    routes, packages, sequences, travel = tiny(spark)
    stops = t.explode_stops(routes)
    legs = t.build_legs(sequences, travel)
    arr = {r["stop_id"]: r for r in t.stop_arrivals(routes, stops, packages, legs).collect()}

    assert arr["ST"]["est_arrival_utc"] == datetime(2018, 7, 27, 16, 0, 0)
    # 600s drive, nothing served before A
    assert arr["A"]["est_arrival_utc"] == datetime(2018, 7, 27, 16, 10, 0)
    # 600 + 1000 drive + 100s service at A = 1700s
    assert arr["B"]["est_arrival_utc"] == datetime(2018, 7, 27, 16, 28, 20)


def test_late_flag_and_minutes(spark):
    routes, packages, sequences, travel = tiny(spark, {
        "ST": {"A": 600.0, "B": 900.0}, "A": {"B": 1100.0}, "B": {}})
    stops = t.explode_stops(routes)
    legs = t.build_legs(sequences, travel)
    facts = {r["package_id"]: r for r in
             t.package_facts(packages, t.stop_arrivals(routes, stops, packages, legs)).collect()}
    # B arrival = 600 + 1100 + 100 = 1800s -> 16:30:00, exactly on the window end, not late
    assert facts["p3"]["is_late"] is False
    assert facts["p1"]["has_window"] is False and facts["p1"]["is_late"] is False
    assert facts["p4"]["is_delivered"] is False


def test_late_when_past_window(spark):
    routes, packages, sequences, travel = tiny(spark, {
        "ST": {"A": 600.0}, "A": {"B": 1200.0}, "B": {}})
    stops = t.explode_stops(routes)
    legs = t.build_legs(sequences, travel)
    p3 = [r for r in t.package_facts(packages, t.stop_arrivals(routes, stops, packages, legs)).collect()
          if r["package_id"] == "p3"][0]
    assert p3["is_late"] is True
    assert round(p3["minutes_late"], 2) == round(100 / 60, 2)


def test_missing_travel_leg_blocks_the_run(spark):
    routes, packages, sequences, travel = tiny(spark, {"ST": {"A": 600.0}, "A": {}, "B": {}})
    stops = t.explode_stops(routes)
    legs = t.build_legs(sequences, travel)
    results = {r.name: r for r in run_checks(DAY, routes, stops, packages, legs, [])}
    assert results["travel_time_coverage"].passed is False
    assert results["travel_time_coverage"].severity == "error"


def test_wrong_partition_date_is_caught(spark):
    routes, packages, sequences, travel = tiny(spark)
    stops = t.explode_stops(routes)
    legs = t.build_legs(sequences, travel)
    results = {r.name: r for r in run_checks("2018-07-28", routes, stops, packages, legs, [])}
    assert results["route_date_matches_partition"].passed is False


def test_volume_check_needs_history(spark):
    routes, packages, sequences, travel = tiny(spark)
    stops = t.explode_stops(routes)
    legs = t.build_legs(sequences, travel)
    names = [r.name for r in run_checks(DAY, routes, stops, packages, legs, [200, 190])]
    assert "route_volume_vs_7d" not in names  # fewer than 3 days of history, skip
    vol = [r for r in run_checks(DAY, routes, stops, packages, legs, [200, 190, 210]) if r.name == "route_volume_vs_7d"]
    assert vol[0].passed is False  # 1 route vs ~200 normally
