"""End-to-end unit tests for the main lambda_handler."""

import os
import unittest
from unittest.mock import patch, MagicMock
from src.lambda_function import lambda_handler


class TestLambdaFunction(unittest.TestCase):

    @patch.dict(os.environ, {
        "THRESHOLD_PERCENTAGE": "80",
        "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:test-topic",
        "CONNECT_INSTANCE_ID": ""
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

        # Mock list_instances
        mock_paginator_inst = MagicMock()
        mock_paginator_inst.paginate.return_value = [
            {"InstanceSummaryList": [{"Id": "inst-1", "InstanceAlias": "BankProd"}]}
        ]

        # Mock list_queues etc.
        mock_paginator_generic = MagicMock()
        mock_paginator_generic.paginate.return_value = [
            {"QueueSummaryList": [{"Id": "q1"}]}
        ]

        def get_paginator_side_effect(api_name):
            if api_name == "list_instances":
                return mock_paginator_inst
            return mock_paginator_generic

        mock_connect.get_paginator.side_effect = get_paginator_side_effect

        # Mock service quotas
        mock_sq_paginator = MagicMock()
        mock_sq_paginator.paginate.return_value = [
            {"Quotas": [{"QuotaCode": "L-28B936FD", "Value": 50.0}]}
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


if __name__ == "__main__":
    unittest.main()

