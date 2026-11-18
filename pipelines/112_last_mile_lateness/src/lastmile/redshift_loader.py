"""Second Lambda. EventBridge calls it when the Glue job for a date SUCCEEDS.

Reads the run_date back from the Glue run's arguments and runs
sql/redshift/load_partition.sql through the Redshift Data API.
`make package` copies that SQL file next to this module in the Lambda zip.
"""
import logging
import os
import time
from pathlib import Path

import boto3

log = logging.getLogger()
log.setLevel(logging.INFO)

_here = Path(__file__).parent
# in the Lambda zip the file sits next to this module, in the repo it lives under sql/redshift
_sql_file = _here / "load_partition.sql"
if not _sql_file.exists():
    _sql_file = _here.parents[1] / "sql/redshift/load_partition.sql"
SQL = _sql_file.read_text()


def split_sql(sql: str) -> list[str]:
    body = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    return [s.strip() for s in body.split(";") if s.strip()]


def lambda_handler(event, context):
    detail = event["detail"]
    run = boto3.client("glue").get_job_run(JobName=detail["jobName"], RunId=detail["jobRunId"])["JobRun"]
    run_date = run["Arguments"]["--run_date"]

    sql = SQL.format(run_date=run_date, date_key=run_date.replace("-", ""),
                     curated=f"s3://{os.environ['CURATED_BUCKET']}", iam_role=os.environ["REDSHIFT_COPY_ROLE"])
    rs = boto3.client("redshift-data")
    statements = split_sql(sql)
    # batch_execute_statement runs the list as one transaction
    stmt = rs.batch_execute_statement(WorkgroupName=os.environ["REDSHIFT_WORKGROUP"],
                                      Database=os.environ.get("REDSHIFT_DB", "dev"), Sqls=statements)
    # Data API is async. Poll so a failed load fails this Lambda (and its alarm).
    while True:
        d = rs.describe_statement(Id=stmt["Id"])
        if d["Status"] in ("FINISHED", "FAILED", "ABORTED"):
            break
        time.sleep(2)
    if d["Status"] != "FINISHED":
        raise RuntimeError(f"redshift load for {run_date} {d['Status']}: {d.get('Error')}")
    log.info("loaded %s into redshift", run_date)
    return {"run_date": run_date}
