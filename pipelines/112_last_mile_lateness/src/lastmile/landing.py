"""Upload one day's drop to the raw bucket.

The manifest goes up last. The Lambda only listens for _manifest.json, so a
half-uploaded day never triggers a run.
"""
import argparse
import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from .settings import Settings
from .storage import s3_client

log = logging.getLogger(__name__)

TABLES = ("routes", "packages", "sequences", "travel_times")


def raw_prefix(run_date: str) -> str:
    return f"almrrc/dt={run_date}"


def build_manifest(folder: Path, run_date: str) -> dict:
    files = []
    for table in TABLES:
        p = folder / f"{table}.jsonl"
        if not p.exists():
            raise FileNotFoundError(f"{p} missing, drop is incomplete")
        md5 = hashlib.md5()
        rows = 0
        with open(p, "rb") as f:
            for line in f:
                md5.update(line)
                rows += 1
        files.append({"table": table, "key": f"{table}.jsonl", "rows": rows,
                      "bytes": p.stat().st_size, "md5": md5.hexdigest()})
    return {"run_date": run_date, "source": "almrrc2021",
            "created_at": datetime.now(UTC).isoformat(), "files": files}


def land(run_date: str, drops_dir: Path, cfg: Settings) -> dict:
    folder = drops_dir / f"dt={run_date}"
    manifest = build_manifest(folder, run_date)
    s3 = s3_client(cfg)
    prefix = raw_prefix(run_date)
    for f in manifest["files"]:
        s3.upload_file(str(folder / f["key"]), cfg.raw_bucket, f"{prefix}/{f['key']}")
    s3.put_object(Bucket=cfg.raw_bucket, Key=f"{prefix}/_manifest.json",
                  Body=json.dumps(manifest, indent=1).encode())
    log.info("landed %s (%s)", run_date, ", ".join(f"{f['table']}={f['rows']}" for f in manifest["files"]))
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_date")
    ap.add_argument("--drops", default="data/drops")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    land(args.run_date, Path(args.drops), Settings.from_env())


if __name__ == "__main__":
    main()
