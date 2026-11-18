"""Spark job, one run per route date. Same file runs as the Glue job and locally.

raw/almrrc/dt=D/*.jsonl  ->  curated/{route,stop,package_delivery}/route_date=D/

Arrival times are estimates. The source gives the order the driver actually
drove (actual_sequences), the planned service time per package and a travel
time matrix, but no GPS timestamps. So arrival at stop k is

    departure + travel time of legs 1..k + service time at stops 1..k-1

and a package is late when that estimate is past its delivery window.
"""
import argparse
import json
import logging
import os
from datetime import date, timedelta

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql import types as T

from .checks import ERROR, WARN, failed, run_checks

log = logging.getLogger(__name__)

STOP = T.StructType([
    T.StructField("stop_id", T.StringType()),
    T.StructField("lat", T.DoubleType()),
    T.StructField("lng", T.DoubleType()),
    T.StructField("type", T.StringType()),
    T.StructField("zone_id", T.StringType()),
])
ROUTES = T.StructType([
    T.StructField("route_id", T.StringType()),
    T.StructField("station_code", T.StringType()),
    T.StructField("date_YYYY_MM_DD", T.StringType()),
    T.StructField("departure_time_utc", T.StringType()),
    T.StructField("executor_capacity_cm3", T.DoubleType()),
    T.StructField("route_score", T.StringType()),
    T.StructField("stops", T.ArrayType(STOP)),
])
PACKAGES = T.StructType([
    T.StructField("route_id", T.StringType()),
    T.StructField("stop_id", T.StringType()),
    T.StructField("package_id", T.StringType()),
    T.StructField("scan_status", T.StringType()),
    T.StructField("tw_start_utc", T.StringType()),
    T.StructField("tw_end_utc", T.StringType()),
    T.StructField("planned_service_time_seconds", T.DoubleType()),
    T.StructField("depth_cm", T.DoubleType()),
    T.StructField("height_cm", T.DoubleType()),
    T.StructField("width_cm", T.DoubleType()),
])
SEQUENCES = T.StructType([
    T.StructField("route_id", T.StringType()),
    T.StructField("stop_id", T.StringType()),
    T.StructField("seq", T.IntegerType()),
])
TRAVEL = T.StructType([
    T.StructField("route_id", T.StringType()),
    T.StructField("matrix", T.MapType(T.StringType(), T.MapType(T.StringType(), T.DoubleType()))),
])


def read_raw(spark, raw_root: str, run_date: str):
    base = f"{raw_root}/almrrc/dt={run_date}"
    # FAILFAST: a malformed line should fail the run, not turn into a null row
    rd = spark.read.option("mode", "FAILFAST")
    return (
        rd.schema(ROUTES).json(f"{base}/routes.jsonl"),
        rd.schema(PACKAGES).json(f"{base}/packages.jsonl"),
        rd.schema(SEQUENCES).json(f"{base}/sequences.jsonl"),
        rd.schema(TRAVEL).json(f"{base}/travel_times.jsonl"),
    )


def explode_stops(routes: DataFrame) -> DataFrame:
    return routes.select("route_id", F.explode("stops").alias("s")).select("route_id", "s.*")


def build_legs(sequences: DataFrame, travel: DataFrame) -> DataFrame:
    """One row per stop in driven order, with the travel time of the leg into it."""
    w = Window.partitionBy("route_id").orderBy("seq")
    return (
        sequences
        .withColumn("prev_stop_id", F.lag("stop_id").over(w))
        .join(travel, "route_id")
        .withColumn("leg_seconds", F.element_at(F.element_at("matrix", F.col("prev_stop_id")), F.col("stop_id")))
        .drop("matrix")
    )


def stop_arrivals(routes, stops, packages, legs) -> DataFrame:
    service = packages.groupBy("route_id", "stop_id").agg(
        F.count("*").alias("n_packages"),
        F.sum("planned_service_time_seconds").alias("service_seconds"),
    )
    w = Window.partitionBy("route_id").orderBy("seq")
    upto_here = w.rowsBetween(Window.unboundedPreceding, Window.currentRow)
    before_here = w.rowsBetween(Window.unboundedPreceding, -1)
    departure = F.to_timestamp(F.concat_ws(" ", "date_YYYY_MM_DD", "departure_time_utc"))

    return (
        legs
        .join(service, ["route_id", "stop_id"], "left")
        .fillna({"n_packages": 0, "service_seconds": 0.0})
        .withColumn("travel_before", F.sum(F.coalesce("leg_seconds", F.lit(0.0))).over(upto_here))
        .withColumn("service_before", F.coalesce(F.sum("service_seconds").over(before_here), F.lit(0.0)))
        .join(routes.select("route_id", departure.alias("departure_utc")), "route_id")
        .withColumn("offset_seconds", F.col("travel_before") + F.col("service_before"))
        .withColumn("est_arrival_utc",
                    (F.col("departure_utc").cast("long") + F.col("offset_seconds")).cast("timestamp"))
        .withColumn("stop_position_pct", F.col("seq") / F.max("seq").over(Window.partitionBy("route_id")))
        .join(stops.select("route_id", "stop_id", "zone_id", "lat", "lng", "type"), ["route_id", "stop_id"])
    )


def package_facts(packages: DataFrame, arrivals: DataFrame) -> DataFrame:
    tw_start = F.to_timestamp("tw_start_utc")
    tw_end = F.to_timestamp("tw_end_utc")
    late_s = F.col("est_arrival_utc").cast("long") - F.col("tw_end").cast("long")
    return (
        packages
        .join(arrivals.select("route_id", "stop_id", "seq", "zone_id", "est_arrival_utc", "stop_position_pct"),
              ["route_id", "stop_id"])
        .withColumn("tw_start", tw_start)
        .withColumn("tw_end", tw_end)
        .withColumn("has_window", F.col("tw_end").isNotNull())
        .withColumn("is_late", F.col("has_window") & (late_s > 0))
        .withColumn("minutes_late", F.when(F.col("is_late"), late_s / 60.0))
        .withColumn("is_delivered", F.col("scan_status") == "DELIVERED")
        .withColumn("volume_cm3", F.col("depth_cm") * F.col("height_cm") * F.col("width_cm"))
        .drop("tw_start_utc", "tw_end_utc")
    )


def route_summary(routes: DataFrame, arrivals: DataFrame, facts: DataFrame) -> DataFrame:
    a = arrivals.groupBy("route_id").agg(
        F.count("*").alias("n_stops"),
        F.max("offset_seconds").alias("planned_route_seconds"),
    )
    p = facts.groupBy("route_id").agg(
        F.count("*").alias("n_packages"),
        F.sum(F.col("is_late").cast("int")).alias("n_late"),
        F.sum(F.col("has_window").cast("int")).alias("n_with_window"),
        F.sum((~F.col("is_delivered")).cast("int")).alias("n_not_delivered"),
        F.sum("volume_cm3").alias("load_cm3"),
    )
    return (
        routes.drop("stops")
        .withColumn("departure_utc", F.to_timestamp(F.concat_ws(" ", "date_YYYY_MM_DD", "departure_time_utc")))
        .drop("departure_time_utc", "date_YYYY_MM_DD")
        .join(a, "route_id", "left")
        .join(p, "route_id", "left")
    )


def recent_route_counts(spark, curated_root: str, run_date: str, days: int = 7) -> list[int]:
    d = date.fromisoformat(run_date)
    wanted = [(d - timedelta(days=i)).isoformat() for i in range(1, days + 1)]
    try:
        hist = spark.read.parquet(f"{curated_root}/route").filter(F.col("route_date").isin(wanted))
        return [r["n"] for r in hist.groupBy("route_date").agg(F.count("*").alias("n")).collect()]
    except Exception:  # first run, nothing curated yet
        return []


def write_partition(df: DataFrame, path: str, run_date: str):
    (df.withColumn("route_date", F.lit(run_date).cast("date"))
       .write.mode("overwrite")
       .partitionBy("route_date")
       .parquet(path))


def run(spark, run_date: str, raw_root: str, curated_root: str) -> dict:
    routes, packages, sequences, travel = read_raw(spark, raw_root, run_date)
    routes = routes.cache()
    stops = explode_stops(routes).cache()
    legs = build_legs(sequences, travel).cache()

    results = run_checks(run_date, routes, stops, packages, legs,
                         recent_route_counts(spark, curated_root, run_date))
    report = {"run_date": run_date, "checks": [r.as_dict() for r in results]}
    errors = failed(results, ERROR)
    if errors:
        report["status"] = "failed_checks"
        return report

    arrivals = stop_arrivals(routes, stops, packages, legs).cache()
    facts = package_facts(packages, arrivals).cache()
    summary = route_summary(routes, arrivals, facts)

    write_partition(summary, f"{curated_root}/route", run_date)
    write_partition(arrivals.drop("travel_before", "service_before", "departure_utc"),
                    f"{curated_root}/stop", run_date)
    write_partition(facts, f"{curated_root}/package_delivery", run_date)

    report["status"] = "warn" if failed(results, WARN) else "ok"
    report["rows"] = {"route": summary.count(), "package_delivery": facts.count()}
    return report


def spark_session(app="lastmile-transform", s3_endpoint=None):
    b = (SparkSession.builder.appName(app)
         .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
         .config("spark.sql.session.timeZone", "UTC")
         # one day is ~45k packages / ~180 routes. The default 200 shuffle partitions
         # meant 200 tiny tasks per stage; 16 plus AQE coalescing is plenty here.
         # Bump this (or let AQE do it) if you run many days in one job.
         .config("spark.sql.shuffle.partitions", os.getenv("SHUFFLE_PARTITIONS", "16"))
         .config("spark.sql.adaptive.enabled", "true"))
    if s3_endpoint:  # local MinIO; on Glue the s3:// scheme just works
        b = (b.config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4")
             .config("spark.hadoop.fs.s3a.endpoint", s3_endpoint)
             .config("spark.hadoop.fs.s3a.path.style.access", "true")
             .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
             .config("spark.hadoop.fs.s3a.aws.credentials.provider",
                     "com.amazonaws.auth.EnvironmentVariableCredentialsProvider"))
    return b.getOrCreate()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run_date", required=True)
    ap.add_argument("--raw_root", required=True)
    ap.add_argument("--curated_root", required=True)
    ap.add_argument("--report_out")
    args, _ = ap.parse_known_args()  # Glue passes its own args too
    logging.basicConfig(level=logging.INFO)
    spark = spark_session()
    report = run(spark, args.run_date, args.raw_root, args.curated_root)
    print(json.dumps(report, indent=1, default=str))
    if report["status"] == "failed_checks":
        raise SystemExit(f"data quality checks failed for {args.run_date}")


if __name__ == "__main__":
    main()
