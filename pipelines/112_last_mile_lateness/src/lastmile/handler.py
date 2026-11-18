"""Lambda entry point. Fires on s3:ObjectCreated for */_manifest.json.

Checks that every file listed in the manifest actually landed with the right
size, then starts the Glue job for that date. A bad drop is rejected here so
Glue never spends DPU time on it.
"""
import json
import logging
import os
import re
import urllib.parse

import boto3

from .alerts import send_alert
from .settings import Settings
from .storage import s3_client

log = logging.getLogger()
log.setLevel(logging.INFO)

DT_RE = re.compile(r"dt=(\d{4}-\d{2}-\d{2})/_manifest\.json$")


class DropRejected(Exception):
    pass


def validate_drop(s3, bucket: str, manifest_key: str) -> dict:
    m = DT_RE.search(manifest_key)
    if not m:
        raise DropRejected(f"unexpected key {manifest_key}")
    run_date = m.group(1)

    manifest = json.loads(s3.get_object(Bucket=bucket, Key=manifest_key)["Body"].read())
    if manifest.get("run_date") != run_date:
        raise DropRejected(f"manifest says {manifest.get('run_date')}, path says {run_date}")

    prefix = manifest_key.rsplit("/", 1)[0]
    problems = []
    for f in manifest["files"]:
        try:
            head = s3.head_object(Bucket=bucket, Key=f"{prefix}/{f['key']}")
        except s3.exceptions.ClientError:
            problems.append(f"{f['key']} missing")
            continue
        if head["ContentLength"] != f["bytes"]:
            problems.append(f"{f['key']} is {head['ContentLength']} bytes, manifest says {f['bytes']}")
        if f["rows"] == 0:
            problems.append(f"{f['key']} has no rows")
    if problems:
        raise DropRejected("; ".join(problems))
    return manifest


def lambda_handler(event, context):
    cfg = Settings.from_env()
    s3 = s3_client(cfg)
    glue = boto3.client("glue")
    started = []
    for rec in event.get("Records", []):
        bucket = rec["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(rec["s3"]["object"]["key"])
        try:
            manifest = validate_drop(s3, bucket, key)
        except DropRejected as e:
            send_alert(cfg, f"Drop rejected: {key}", str(e))
            raise
        run = glue.start_job_run(
            JobName=os.environ["GLUE_JOB_NAME"],
            Arguments={"--run_date": manifest["run_date"]},
        )
        log.info("started glue run %s for %s", run["JobRunId"], manifest["run_date"])
        started.append(run["JobRunId"])
    return {"started": started}
