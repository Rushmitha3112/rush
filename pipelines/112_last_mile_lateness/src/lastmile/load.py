"""Load one curated partition into the warehouse.

Delete-then-insert for the date inside one transaction, so a rerun or backfill
of a day replaces it cleanly and readers never see a half-loaded day.
In AWS the same idea is COPY into a staging table + MERGE (sql/redshift/).
"""
import logging
from datetime import date

import pandas as pd
import psycopg
import pyarrow.dataset as ds
from pyarrow import fs

from .settings import Settings

log = logging.getLogger(__name__)


def curated_fs(cfg: Settings):
    if cfg.s3_endpoint:
        return fs.S3FileSystem(endpoint_override=cfg.s3_endpoint, region=cfg.region,
                               scheme="http" if cfg.s3_endpoint.startswith("http:") else "https")
    return fs.S3FileSystem(region=cfg.region)


def read_partition(cfg: Settings, table: str, run_date: str) -> pd.DataFrame:
    path = f"{cfg.curated_bucket}/{table}/route_date={run_date}"
    return ds.dataset(path, format="parquet", filesystem=curated_fs(cfg)).to_table().to_pandas()


def date_key(d: str) -> int:
    return int(d.replace("-", ""))


def _copy(cur, table: str, df: pd.DataFrame):
    cols = list(df.columns)
    with cur.copy(f"copy {table} ({', '.join(cols)}) from stdin") as cp:
        for row in df.itertuples(index=False, name=None):
            cp.write_row([None if pd.isna(v) else v for v in row])


def load_day(conn, run_date: str, routes: pd.DataFrame, packages: pd.DataFrame) -> dict:
    dk = date_key(run_date)
    d = date.fromisoformat(run_date)
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            """insert into lastmile.dim_date values (%s, %s, %s, %s, %s, %s)
               on conflict (date_key) do nothing""",
            (dk, d, d.isoweekday(), d.isocalendar().week, d.month, d.isoweekday() >= 6),
        )
        for code in sorted(routes["station_code"].unique()):
            cur.execute("""insert into lastmile.dim_station (station_code) values (%s)
                           on conflict (station_code) do nothing""", (code,))

        zones = packages.merge(routes[["route_id", "station_code"]], on="route_id")[["station_code", "zone_id"]]
        zones = zones.dropna().drop_duplicates()
        cur.execute("create temp table stage_zone (station_code text, zone_id text) on commit drop")
        _copy(cur, "stage_zone", zones)
        cur.execute("""insert into lastmile.dim_zone (station_key, zone_id)
                       select s.station_key, z.zone_id from stage_zone z
                       join lastmile.dim_station s using (station_code)
                       on conflict (station_key, zone_id) do nothing""")

        cur.execute("delete from lastmile.fact_package_delivery where date_key = %s", (dk,))
        cur.execute("delete from lastmile.fact_route where date_key = %s", (dk,))

        r = routes.rename(columns={"executor_capacity_cm3": "capacity_cm3"})[[
            "route_id", "station_code", "departure_utc", "route_score", "capacity_cm3", "load_cm3",
            "n_stops", "n_packages", "n_with_window", "n_late", "n_not_delivered", "planned_route_seconds"]]
        cur.execute("""create temp table stage_route (route_id text, station_code text, departure_utc timestamp,
                       route_score text, capacity_cm3 float8, load_cm3 float8, n_stops int, n_packages int,
                       n_with_window int, n_late int, n_not_delivered int, planned_route_seconds float8)
                       on commit drop""")
        _copy(cur, "stage_route", r)
        cur.execute("""insert into lastmile.fact_route (route_id, date_key, station_key, departure_utc, route_score,
                         capacity_cm3, load_cm3, n_stops, n_packages, n_with_window, n_late, n_not_delivered,
                         planned_route_seconds)
                       select r.route_id, %s, s.station_key, r.departure_utc, r.route_score, r.capacity_cm3,
                              r.load_cm3, r.n_stops, r.n_packages, r.n_with_window, r.n_late, r.n_not_delivered,
                              r.planned_route_seconds
                       from stage_route r join lastmile.dim_station s using (station_code)""", (dk,))

        p = packages[["route_id", "package_id", "zone_id", "stop_id", "seq", "stop_position_pct", "scan_status",
                      "is_delivered", "has_window", "tw_start", "tw_end", "est_arrival_utc", "is_late",
                      "minutes_late", "planned_service_time_seconds", "volume_cm3"]]
        p = p.rename(columns={"planned_service_time_seconds": "planned_service_s"})
        cur.execute("""create temp table stage_pkg (route_id text, package_id text, zone_id text, stop_id text,
                       seq int, stop_position_pct float8, scan_status text, is_delivered bool, has_window bool,
                       tw_start timestamp, tw_end timestamp, est_arrival_utc timestamp, is_late bool,
                       minutes_late float8, planned_service_s float8, volume_cm3 float8) on commit drop""")
        _copy(cur, "stage_pkg", p)
        cur.execute("""insert into lastmile.fact_package_delivery
                       select p.route_id, p.package_id, %s, f.station_key, z.zone_key, p.stop_id, p.seq,
                              p.stop_position_pct, p.scan_status, p.is_delivered, p.has_window, p.tw_start,
                              p.tw_end, p.est_arrival_utc, p.is_late, p.minutes_late, p.planned_service_s,
                              p.volume_cm3
                       from stage_pkg p
                       join lastmile.fact_route f using (route_id)
                       left join lastmile.dim_zone z on z.station_key = f.station_key and z.zone_id = p.zone_id""",
                    (dk,))
        n_pkg = cur.rowcount
    log.info("loaded %s: %d routes, %d packages", run_date, len(r), n_pkg)
    return {"routes": len(r), "packages": n_pkg}


def load_partition(cfg: Settings, run_date: str) -> dict:
    routes = read_partition(cfg, "route", run_date)
    packages = read_partition(cfg, "package_delivery", run_date)
    with psycopg.connect(cfg.pg_dsn) as conn:
        return load_day(conn, run_date, routes, packages)
