"""Main AWS Lambda entry point for Amazon Connect Service Quota Monitor."""

import json
import logging
import os
import sys
from typing import Any, Dict

import boto3
from botocore.config import Config

# Ensure local module directory is in sys.path for both Lambda root and package imports
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

try:
    from discovery import ConnectDiscovery
    from collector import QuotaCollector
    from publisher import MetricsAndAlertPublisher
except ImportError:
    from src.discovery import ConnectDiscovery
    from src.collector import QuotaCollector
    from src.publisher import MetricsAndAlertPublisher

# Configure structured logging
logger = logging.getLogger("connect-quota-monitor")
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)

# Load quota catalog definitions
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_CATALOG_PATH = os.path.join(_CURRENT_DIR, "quota_definitions.json")

try:
    with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
        QUOTA_DEFINITIONS = json.load(f)
    logger.info("Loaded %d quota definitions from catalog", len(QUOTA_DEFINITIONS))
except Exception as e:
    logger.error("Failed to load quota definitions from %s: %s", _CATALOG_PATH, str(e))
    QUOTA_DEFINITIONS = {}


def _get_boto3_clients():
    """Create standard boto3 clients with retry configuration."""
    retry_config = Config(
        retries={"max_attempts": 3, "mode": "standard"},
        connect_timeout=10,
        read_timeout=30
    )
    session = boto3.Session()
    return {
        "connect": session.client("connect", config=retry_config),
        "service_quotas": session.client("service-quotas", config=retry_config),
        "cloudwatch": session.client("cloudwatch", config=retry_config),
        "sns": session.client("sns", config=retry_config)
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entry point triggered by EventBridge or manual invocation.
    """
    logger.info("Starting Amazon Connect Service Quota Monitor execution...")

    # Load runtime configuration
    threshold_pct = float(os.environ.get("THRESHOLD_PERCENTAGE", "80.0"))
    sns_topic_arn = os.environ.get("SNS_TOPIC_ARN", "")
    target_instance_id = os.environ.get("CONNECT_INSTANCE_ID", "").strip() or None

    clients = _get_boto3_clients()

    # 1. Discovery
    discovery = ConnectDiscovery(
        connect_client=clients["connect"],
        service_quotas_client=clients["service_quotas"]
    )
    instances = discovery.discover_instances(target_instance_id=target_instance_id)
    if not instances:
        logger.warning("No Amazon Connect instances found in this region.")
        return {
            "statusCode": 200,
            "message": "No Connect instances found to monitor.",
            "instances_monitored": 0
        }

    quota_catalog = discovery.fetch_all_service_quotas()

    # 2. Collection
    collector = QuotaCollector(
        connect_client=clients["connect"],
        cloudwatch_client=clients["cloudwatch"],
        quota_definitions=QUOTA_DEFINITIONS
    )
    records = collector.collect_all_quotas(
        instances=instances,
        quota_catalog=quota_catalog,
        threshold_percentage=threshold_pct
    )

    # 3. Publishing to CloudWatch and SNS
    publisher = MetricsAndAlertPublisher(
        cloudwatch_client=clients["cloudwatch"],
        sns_client=clients["sns"],
        sns_topic_arn=sns_topic_arn
    )
    metrics_pushed = publisher.publish_metrics_to_cloudwatch(records)
    alert_sent = publisher.publish_alerts_if_needed(records)

    warnings = [r for r in records if r.get("is_warning")]
    breaches = [r for r in records if r.get("is_breached")]

    summary = {
        "statusCode": 200,
        "instances_monitored": len(instances),
        "quotas_evaluated": len(records),
        "metrics_pushed_to_cloudwatch": metrics_pushed,
        "warnings_count": len(warnings),
        "breaches_count": len(breaches),
        "alert_dispatched": alert_sent
    }

    logger.info("Execution complete: %s", json.dumps(summary))
    return summary


if __name__ == "__main__":
    # Local CLI testing harness
    print(lambda_handler({}, None))
