import json
import logging
import os
import urllib.request

log = logging.getLogger(__name__)


def send_alert(cfg, subject: str, body: str) -> None:
    """SNS when running in AWS, a webhook locally, and always the log."""
    log.error("ALERT %s | %s", subject, body)
    topic = os.getenv("ALERT_TOPIC_ARN")
    if topic:
        import boto3
        boto3.client("sns").publish(TopicArn=topic, Subject=subject[:100], Message=body)
    if cfg.alert_webhook:
        req = urllib.request.Request(
            cfg.alert_webhook,
            data=json.dumps({"text": f"*{subject}*\n{body}"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=5)
        except OSError as e:
            # an alert failing shouldn't hide the original failure
            log.warning("webhook alert failed: %s", e)
