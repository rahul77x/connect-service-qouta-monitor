"""Unit tests for the MetricsAndAlertPublisher module."""

import unittest
from unittest.mock import MagicMock
from src.publisher import MetricsAndAlertPublisher


class TestMetricsAndAlertPublisher(unittest.TestCase):

    def test_publish_metrics_to_cloudwatch(self):
        mock_cw = MagicMock()
        mock_sns = MagicMock()

        publisher = MetricsAndAlertPublisher(mock_cw, mock_sns, sns_topic_arn="arn:aws:sns:us-east-1:123:alerts")

        records = [
            {
                "instance_id": "inst-1",
                "quota_code": "L-28B936FD",
                "quota_name": "Active concurrent voice calls",
                "category": "TELEPHONY",
                "utilization_percent": 84.0,
                "usage": 42.0,
                "limit": 50.0
            }
        ]

        pushed_count = publisher.publish_metrics_to_cloudwatch(records)

        # 1 record generates 3 metrics: QuotaUtilizationPercent, QuotaUsage, QuotaLimit
        self.assertEqual(pushed_count, 3)
        self.assertTrue(mock_cw.put_metric_data.called)
        call_args = mock_cw.put_metric_data.call_args[1]
        self.assertEqual(call_args["Namespace"], "AmazonConnect/ServiceQuotas")
        self.assertEqual(len(call_args["MetricData"]), 3)

    def test_publish_alerts_when_warning_detected(self):
        mock_cw = MagicMock()
        mock_sns = MagicMock()
        mock_sns.publish.return_value = {"MessageId": "msg-12345"}

        publisher = MetricsAndAlertPublisher(mock_cw, mock_sns, sns_topic_arn="arn:aws:sns:us-east-1:123:alerts")

        records = [
            {
                "instance_alias": "ProdConnect",
                "instance_id": "inst-1",
                "quota_code": "L-28B936FD",
                "quota_name": "Active concurrent voice calls",
                "usage": 45.0,
                "limit": 50.0,
                "unit": "Count",
                "utilization_percent": 90.0,
                "threshold_percent": 80.0,
                "is_warning": True,
                "is_breached": False
            }
        ]

        alert_sent = publisher.publish_alerts_if_needed(records)

        self.assertTrue(alert_sent)
        self.assertTrue(mock_sns.publish.called)
        call_args = mock_sns.publish.call_args[1]
        self.assertEqual(call_args["TopicArn"], "arn:aws:sns:us-east-1:123:alerts")
        self.assertIn("[ALERT]", call_args["Subject"])
        self.assertIn("ProdConnect", call_args["Message"])
        self.assertIn("90.0%", call_args["Message"])

    def test_skip_alerts_when_no_warning(self):
        mock_cw = MagicMock()
        mock_sns = MagicMock()

        publisher = MetricsAndAlertPublisher(mock_cw, mock_sns, sns_topic_arn="arn:aws:sns:us-east-1:123:alerts")

        records = [
            {
                "instance_id": "inst-1",
                "quota_code": "L-28B936FD",
                "utilization_percent": 40.0,
                "is_warning": False,
                "is_breached": False
            }
        ]

        alert_sent = publisher.publish_alerts_if_needed(records)

        self.assertFalse(alert_sent)
        self.assertFalse(mock_sns.publish.called)


if __name__ == "__main__":
    unittest.main()

