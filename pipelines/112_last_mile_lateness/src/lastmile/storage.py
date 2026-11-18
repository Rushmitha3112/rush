import boto3
from botocore.config import Config

from .settings import Settings


def s3_client(cfg: Settings):
    return boto3.client(
        "s3",
        endpoint_url=cfg.s3_endpoint,
        region_name=cfg.region,
        config=Config(retries={"max_attempts": 5, "mode": "standard"}),
    )
