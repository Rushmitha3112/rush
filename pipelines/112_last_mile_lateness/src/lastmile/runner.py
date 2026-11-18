"""Local orchestration. Mirrors what happens in AWS:

    land drop -> (S3 event) Lambda validates manifest -> Glue transform
    -> (EventBridge on SUCCEEDED) loader -> Redshift

Here it's one process: land, validate, transform with local Spark, load to Postgres.
Every attempt is logged to ops.pipeline_runs so reruns and backfills are traceable.

    python -m lastmile.runner run 2018-07-27
    python -m lastmile.runner backfill 2018-07-19 2018-08-26
    python -m lastmile.runner freshness --expect 2018-08-26
"""
import argparse
import logging
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import psycopg

from . import transform
from .alerts import send_alert
from .handler import DropRejected, validate_drop
from .landing import land, raw_prefix
from .load import load_partition
from .settings import Settings
from .storage import s3_client

log = logging.getLogger("lastmile")


def start_run(conn, run_date, trigger) -> int:
    with conn.cursor() as cur:
        cur.execute("insert into ops.pipeline_runs (run_date, trigger, status) values (%s, %s, 'running') "
                    "returning run_id", (run_date, trigger))
        return cur.fetchone()[0]


def finish_run(conn, run_id, status, rows=None, error=None):
    rows = rows or {}
    with conn.cursor() as cur:
        cur.execute("""update ops.pipeline_runs set status=%s, finished_at=now(), routes=%s, packages=%s, error=%s
                       where run_id=%s""", (status, rows.get("routes"), rows.get("packages"), error, run_id))


def save_checks(conn, run_id, run_date, checks):
    with conn.cursor() as cur:
        cur.executemany(
            """insert into ops.dq_results (run_id, run_date, check_name, severity, passed, observed, threshold,
               detail) values (%s, %s, %s, %s, %s, %s, %s, %s)""",
            [(run_id, run_date, c["name"], c["severity"], c["passed"], c["observed"], c["threshold"], c["detail"])
             for c in checks])


def run_day(spark, cfg: Settings, run_date: str, drops: Path, trigger: str) -> str:
    t0 = time.time()
    with psycopg.connect(cfg.pg_dsn, autocommit=True) as conn:
        run_id = start_run(conn, run_date, trigger)
        try:
            land(run_date, drops, cfg)
            validate_drop(s3_client(cfg), cfg.raw_bucket, f"{raw_prefix(run_date)}/_manifest.json")

            report = transform.run(spark, run_date, f"s3a://{cfg.raw_bucket}", f"s3a://{cfg.curated_bucket}")
            save_checks(conn, run_id, run_date, report["checks"])
            if report["status"] == "failed_checks":
                bad = [c["name"] for c in report["checks"] if not c["passed"] and c["severity"] == "error"]
                finish_run(conn, run_id, "failed_checks", error=", ".join(bad))
                send_alert(cfg, f"lastmile {run_date} blocked by data checks", ", ".join(bad))
                return "failed_checks"

            rows = load_partition(cfg, run_date)
            finish_run(conn, run_id, report["status"], rows)
            if report["status"] == "warn":
                warns = [c["name"] for c in report["checks"] if not c["passed"]]
                send_alert(cfg, f"lastmile {run_date} loaded with warnings", ", ".join(warns))
            log.info("%s %s in %.0fs", run_date, report["status"], time.time() - t0)
            return report["status"]
        except DropRejected as e:
            finish_run(conn, run_id, "error", error=f"drop rejected: {e}")
            send_alert(cfg, f"lastmile {run_date} drop rejected", str(e))
            return "error"
        except Exception as e:
            finish_run(conn, run_id, "error", error=repr(e)[:2000])
            send_alert(cfg, f"lastmile {run_date} failed", repr(e)[:2000])
            raise


def daterange(start: str, end: str):
    d, last = date.fromisoformat(start), date.fromisoformat(end)
    while d <= last:
        yield d.isoformat()
        d += timedelta(days=1)


def freshness(cfg: Settings, expect: str) -> bool:
    with psycopg.connect(cfg.pg_dsn) as conn, conn.cursor() as cur:
        cur.execute("select status from ops.latest_runs where run_date = %s", (expect,))
        row = cur.fetchone()
    ok = row is not None and row[0] in ("ok", "warn")
    if not ok:
        send_alert(cfg, f"lastmile SLA miss for {expect}", f"latest status: {row[0] if row else 'no run'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("run_date")
    b = sub.add_parser("backfill")
    b.add_argument("start")
    b.add_argument("end")
    b.add_argument("--keep-going", action="store_true", help="don't stop at the first failed day")
    f = sub.add_parser("freshness")
    f.add_argument("--expect", required=True, help="route date that should be loaded by now")
    for p in (r, b):
        p.add_argument("--drops", default="data/drops")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("py4j").setLevel(logging.WARNING)
    cfg = Settings.from_env()

    if args.cmd == "freshness":
        sys.exit(0 if freshness(cfg, args.expect) else 1)

    spark = transform.spark_session(s3_endpoint=cfg.s3_endpoint)
    spark.sparkContext.setLogLevel("WARN")
    if args.cmd == "run":
        status = run_day(spark, cfg, args.run_date, Path(args.drops), "manual")
        sys.exit(0 if status in ("ok", "warn") else 1)

    drops = Path(args.drops)
    results = {}
    for d in daterange(args.start, args.end):
        if not (drops / f"dt={d}").exists():
            log.info("%s no drop, skipping (no routes that day)", d)
            continue
        results[d] = run_day(spark, cfg, d, drops, "backfill")
        if results[d] not in ("ok", "warn") and not args.keep_going:
            break
    bad = {d: s for d, s in results.items() if s not in ("ok", "warn")}
    log.info("backfill done: %d days, %d not ok %s", len(results), len(bad), bad or "")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
