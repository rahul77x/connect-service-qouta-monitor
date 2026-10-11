"""Publisher module for pushing CloudWatch custom metrics and SNS threshold alerts."""

import json
import logging
from typing import Any, Dict, List
from botocore.exceptions import ClientError

logger = logging.getLogger("connect-quota-monitor.publisher")

CLOUDWATCH_METRIC_NAMESPACE = "AmazonConnect/ServiceQuotas"
MAX_METRIC_BATCH_SIZE = 20  # CloudWatch PutMetricData limit per call is 1000 in newer APIs, 20 is safe across all regions


class MetricsAndAlertPublisher:
    """Handles publishing custom CloudWatch metrics and consolidated SNS alert notifications."""

    def __init__(self, cloudwatch_client, sns_client, sns_topic_arn: str = ""):
        self.cloudwatch = cloudwatch_client
        self.sns = sns_client
        self.sns_topic_arn = sns_topic_arn

    def publish_metrics_to_cloudwatch(self, records: List[Dict[str, Any]]) -> int:
        """
        Publish quota utilization, usage, and limits to CloudWatch.
        Batches metrics to avoid exceeding API limits.
        """
        metric_data: List[Dict[str, Any]] = []

        for rec in records:
            dimensions = [
                {"Name": "InstanceId", "Value": str(rec.get("instance_id"))},
                {"Name": "QuotaCode", "Value": str(rec.get("quota_code"))},
                {"Name": "QuotaName", "Value": str(rec.get("quota_name"))},
                {"Name": "Category", "Value": str(rec.get("category"))}
            ]

            # 1. Utilization Percent
            metric_data.append({
                "MetricName": "QuotaUtilizationPercent",
                "Dimensions": dimensions,
                "Value": float(rec.get("utilization_percent", 0.0)),
                "Unit": "Percent"
            })

            # 2. Quota Usage
            metric_data.append({
                "MetricName": "QuotaUsage",
                "Dimensions": dimensions,
                "Value": float(rec.get("usage", 0.0)),
                "Unit": "None"
            })

            # 3. Quota Limit
            metric_data.append({
                "MetricName": "QuotaLimit",
                "Dimensions": dimensions,
                "Value": float(rec.get("limit", 0.0)),
                "Unit": "None"
            })

        # Batch push to CloudWatch
        total_pushed = 0
        for i in range(0, len(metric_data), MAX_METRIC_BATCH_SIZE):
            batch = metric_data[i:i + MAX_METRIC_BATCH_SIZE]
            try:
                self.cloudwatch.put_metric_data(
                    Namespace=CLOUDWATCH_METRIC_NAMESPACE,
                    MetricData=batch
                )
                total_pushed += len(batch)
            except ClientError as e:
                logger.error("Failed to put metric data batch to CloudWatch: %s", str(e))

        logger.info("Published %d metrics to CloudWatch namespace '%s'", total_pushed, CLOUDWATCH_METRIC_NAMESPACE)
        return total_pushed

    def publish_alerts_if_needed(self, records: List[Dict[str, Any]]) -> bool:
        """
        Evaluate records for warnings or breaches and dispatch consolidated SNS alert.
        """
        warnings = [r for r in records if r.get("is_warning")]
        if not warnings:
            logger.info("No quota thresholds breached (all quotas healthy).")
            return False

        if not self.sns_topic_arn:
            logger.warning("Quota threshold warnings detected, but SNS_TOPIC_ARN is not configured.")
            return False

        # Group warnings by instance
        grouped_by_instance: Dict[str, List[Dict[str, Any]]] = {}
        for w in warnings:
            inst = w.get("instance_alias") or w.get("instance_id")
            if inst not in grouped_by_instance:
                grouped_by_instance[inst] = []
            grouped_by_instance[inst].append(w)

        subject = f"[ALERT] Amazon Connect Service Quota Warning ({len(warnings)} quota(s) nearing limit)"
        lines = [
            "============================================================",
            "  AMAZON CONNECT SERVICE QUOTA MONITOR - ALERT NOTIFICATION  ",
            "============================================================",
            f"Total Quotas in Warning/Breach State: {len(warnings)}",
            ""
        ]

        for inst_name, items in grouped_by_instance.items():
            lines.append(f"Instance: {inst_name}")
            lines.append("-" * 50)
            for item in items:
                status = "BREACH [CRITICAL]" if item.get("is_breached") else "WARNING"
                lines.append(
                    f" - [{status}] {item.get('quota_name')} ({item.get('quota_code')}): "
                    f"{item.get('usage')} / {item.get('limit')} {item.get('unit')} "
                    f"({item.get('utilization_percent')}%, threshold {item.get('threshold_percent')}%)"
                )
            lines.append("")

        lines.extend([
            "Action Recommended:",
            " 1. Inspect the CloudWatch Dashboard in the AWS Management Console.",
            " 2. If usage is legitimate, request an AWS Service Quota increase before production traffic drops.",
            "============================================================"
        ])

        message = "\n".join(lines)

        try:
            response = self.sns.publish(
                TopicArn=self.sns_topic_arn,
                Subject=subject[:100],  # SNS Subject limit is 100 characters
                Message=message
            )
            logger.info("Dispatched consolidated SNS alert. MessageId: %s", response.get("MessageId"))
            return True
        except ClientError as e:
            logger.error("Failed to publish alert to SNS topic %s: %s", self.sns_topic_arn, str(e))
            return False

