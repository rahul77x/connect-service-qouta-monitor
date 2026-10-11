"""End-to-end unit tests for the main lambda_handler."""

import os
import unittest
from unittest.mock import patch, MagicMock
from src.lambda_function import lambda_handler


class TestLambdaFunction(unittest.TestCase):

    @patch.dict(os.environ, {
        "THRESHOLD_PERCENTAGE": "80",
        "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:test-topic",
        "CONNECT_INSTANCE_ID": "inst-1",
        "AWS_REGION": "us-east-1"
    })
    @patch("src.lambda_function._get_boto3_clients")
    def test_lambda_handler_success(self, mock_get_clients):
        mock_connect = MagicMock()
        mock_sq = MagicMock()
        mock_cw = MagicMock()
        mock_sns = MagicMock()

        mock_get_clients.return_value = {
            "connect": mock_connect,
            "service_quotas": mock_sq,
            "cloudwatch": mock_cw,
            "sns": mock_sns
        }

        # Mock describe_instance for targeted instance
        mock_connect.describe_instance.return_value = {
            "Instance": {
                "Id": "inst-1",
                "Arn": "arn:aws:connect:us-east-1:123:instance/inst-1",
                "InstanceAlias": "BankProd",
                "InstanceStatus": "ACTIVE"
            }
        }

        # Mock list_queues etc.
        mock_paginator_generic = MagicMock()
        mock_paginator_generic.paginate.return_value = [
            {"QueueSummaryList": [{"Id": "q1"}]}
        ]
        mock_connect.get_paginator.return_value = mock_paginator_generic

        # Mock service quotas
        mock_sq_paginator = MagicMock()
        mock_sq_paginator.paginate.return_value = [
            {"Quotas": [{"QuotaCode": "L-28B936FD", "QuotaName": "Active concurrent calls", "Value": 50.0, "Unit": "Count"}]}
        ]
        mock_sq.get_paginator.return_value = mock_sq_paginator

        # Mock CloudWatch metrics
        mock_cw.get_metric_data.return_value = {
            "MetricDataResults": [{"Values": [15.0]}]
        }

        result = lambda_handler({}, None)

        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(result["instances_monitored"], 1)
        self.assertGreater(result["quotas_evaluated"], 0)
        self.assertGreater(result["metrics_pushed_to_cloudwatch"], 0)
        self.assertTrue(mock_cw.put_metric_data.called)

    @patch.dict(os.environ, {
        "THRESHOLD_PERCENTAGE": "80",
        "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:test-topic",
        "CONNECT_INSTANCE_ID": ""
    })
    def test_lambda_handler_missing_instance_id(self):
        result = lambda_handler({}, None)
        self.assertEqual(result["statusCode"], 400)
        self.assertIn("CONNECT_INSTANCE_ID", result["error"])


if __name__ == "__main__":
    unittest.main()
