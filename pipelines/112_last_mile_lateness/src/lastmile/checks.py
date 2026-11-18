"""Data quality rules. ERROR stops the run before anything is written,
WARN is recorded and alerted on but lets the day through."""
from dataclasses import asdict, dataclass

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

ERROR, WARN = "error", "warn"


@dataclass
class CheckResult:
    name: str
    severity: str
    passed: bool
    observed: float
    threshold: str
    detail: str = ""

    def as_dict(self):
        return asdict(self)


def _dupes(df: DataFrame, keys: list[str]) -> int:
    return df.groupBy(*keys).count().filter("count > 1").count()


def run_checks(run_date: str, routes: DataFrame, stops: DataFrame, packages: DataFrame,
               legs: DataFrame, recent_route_counts: list[int]) -> list[CheckResult]:
    out = []

    n_routes = routes.count()
    out.append(CheckResult("routes_not_empty", ERROR, n_routes > 0, n_routes, "> 0"))

    wrong_date = routes.filter(F.col("date_YYYY_MM_DD") != run_date).count()
    out.append(CheckResult("route_date_matches_partition", ERROR, wrong_date == 0, wrong_date, "== 0"))

    d = _dupes(routes, ["route_id"])
    out.append(CheckResult("route_id_unique", ERROR, d == 0, d, "== 0"))

    # A package can show up at two stops on one route: attempted at the first,
    # delivered at the second (neighbour, locker). So the grain is package x stop.
    d = _dupes(packages, ["route_id", "package_id", "stop_id"])
    out.append(CheckResult("package_stop_unique", ERROR, d == 0, d, "== 0"))

    n_pkg = packages.select("route_id", "package_id").distinct().count()
    multi = packages.groupBy("route_id", "package_id").count().filter("count > 1").count()
    share = multi / n_pkg if n_pkg else 0.0
    out.append(CheckResult("multi_stop_package_share", WARN, share <= 0.02, round(share, 5), "<= 2%",
                           f"{multi} packages seen at more than one stop"))

    nulls = routes.filter(F.col("station_code").isNull() | F.col("departure_time_utc").isNull()).count()
    out.append(CheckResult("route_required_fields", ERROR, nulls == 0, nulls, "== 0"))

    bad_geo = stops.filter(~F.col("lat").between(-90, 90) | ~F.col("lng").between(-180, 180)
                           | F.col("lat").isNull()).count()
    out.append(CheckResult("stop_coordinates_valid", ERROR, bad_geo == 0, bad_geo, "== 0"))

    # every stop in the driven sequence has to exist on the route
    orphan = legs.join(stops, ["route_id", "stop_id"], "left_anti").count()
    out.append(CheckResult("sequence_stops_exist", ERROR, orphan == 0, orphan, "== 0"))

    n_legs = legs.filter(F.col("prev_stop_id").isNotNull()).count()
    missing = legs.filter(F.col("prev_stop_id").isNotNull() & F.col("leg_seconds").isNull()).count()
    rate = missing / n_legs if n_legs else 0.0
    out.append(CheckResult("travel_time_coverage", ERROR, rate <= 0.001, round(rate, 5), "<= 0.1% missing"))

    neg = packages.filter((F.col("planned_service_time_seconds") < 0)
                          | (F.col("depth_cm") <= 0) | (F.col("height_cm") <= 0) | (F.col("width_cm") <= 0)).count()
    out.append(CheckResult("package_measures_positive", WARN, neg == 0, neg, "== 0"))

    bad_window = packages.filter(F.col("tw_end_utc") < F.col("tw_start_utc")).count()
    out.append(CheckResult("time_window_ordered", WARN, bad_window == 0, bad_window, "== 0"))

    if len(recent_route_counts) >= 3:
        avg = sum(recent_route_counts) / len(recent_route_counts)
        ratio = n_routes / avg if avg else 0
        out.append(CheckResult("route_volume_vs_7d", WARN, 0.5 <= ratio <= 1.5, round(ratio, 3),
                               "0.5x to 1.5x of trailing avg", f"trailing avg {avg:.0f}"))
    return out


def failed(results: list[CheckResult], severity: str) -> list[CheckResult]:
    return [r for r in results if not r.passed and r.severity == severity]
