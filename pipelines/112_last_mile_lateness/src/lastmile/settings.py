import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    s3_endpoint: str | None
    raw_bucket: str
    curated_bucket: str
    pg_dsn: str
    alert_webhook: str | None
    region: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            # unset in AWS so boto3 uses the real endpoint
            s3_endpoint=os.getenv("S3_ENDPOINT_URL") or None,
            raw_bucket=os.getenv("RAW_BUCKET", "lastmile-raw"),
            curated_bucket=os.getenv("CURATED_BUCKET", "lastmile-curated"),
            pg_dsn=os.getenv("PG_DSN", "postgresql://lastmile:lastmile@localhost:5433/lastmile"),
            alert_webhook=os.getenv("ALERT_WEBHOOK_URL") or None,
            region=os.getenv("AWS_REGION", "us-east-1"),
        )
