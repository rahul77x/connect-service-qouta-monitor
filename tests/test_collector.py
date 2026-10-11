"""Unit tests for the QuotaCollector module."""

import unittest
from unittest.mock import MagicMock
from src.collector import QuotaCollector


class TestQuotaCollector(unittest.TestCase):

    def setUp(self):
        self.sample_quota_definitions = {
            "L-AA17A6B9": {
                "name": "Amazon Connect instance count",
                "category": "CORE_CONNECT",
                "scope": "ACCOUNT",
                "method": "api_count",
                "api": "list_instances",
                "default_limit": 2,
                "unit": "Count"
            },
            "L-28B936FD": {
                "name": "Active concurrent voice calls",
                "category": "TELEPHONY",
                "scope": "INSTANCE",
                "method": "cloudwatch",
                "metric_namespace": "AWS/Connect",
                "metric_name": "ConcurrentCalls",
                "default_limit": 50,
                "unit": "Count"
            },
            "L-0304675A": {
                "name": "Queues per instance",
                "category": "ROUTING",
                "scope": "INSTANCE",
                "method": "api_count",
                "api": "list_queues",
                "default_limit": 100,
                "unit": "Count"
            }
        }

    def test_collect_all_quotas(self):
        mock_connect = MagicMock()
        mock_cw = MagicMock()

        # Mock list_queues
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {"QueueSummaryList": [{"Id": "q1"}, {"Id": "q2"}, {"Id": "q3"}]}
        ]
        mock_connect.get_paginator.return_value = mock_paginator

        # Mock CloudWatch ConcurrentCalls
        mock_cw.get_metric_data.return_value = {
            "MetricDataResults": [{"Values": [42.0]}]
        }

        collector = QuotaCollector(mock_connect, mock_cw, self.sample_quota_definitions)

        instances = [{"id": "inst-1", "alias": "ProdConnect"}]
        quota_limits = {
            "L-AA17A6B9": 2.0,
            "L-28B936FD": 50.0,
            "L-0304675A": 100.0
        }

        results = collector.collect_all_quotas(
            instances=instances,
            quota_catalog=quota_limits,
            threshold_percentage=80.0
        )

        self.assertEqual(len(results), 3)

        # Check Account quota
        inst_count_rec = next(r for r in results if r["quota_code"] == "L-AA17A6B9")
        self.assertEqual(inst_count_rec["usage"], 1.0)
        self.assertEqual(inst_count_rec["limit"], 2.0)
        self.assertEqual(inst_count_rec["utilization_percent"], 50.0)
        self.assertFalse(inst_count_rec["is_warning"])

        # Check ConcurrentCalls quota (42 / 50 = 84% -> Warning!)
        calls_rec = next(r for r in results if r["quota_code"] == "L-28B936FD")
        self.assertEqual(calls_rec["usage"], 42.0)
        self.assertEqual(calls_rec["limit"], 50.0)
        self.assertEqual(calls_rec["utilization_percent"], 84.0)
        self.assertTrue(calls_rec["is_warning"])
        self.assertFalse(calls_rec["is_breached"])

        # Check Queues quota (3 / 100 = 3%)
        queues_rec = next(r for r in results if r["quota_code"] == "L-0304675A")
        self.assertEqual(queues_rec["usage"], 3.0)
        self.assertEqual(queues_rec["limit"], 100.0)
        self.assertEqual(queues_rec["utilization_percent"], 3.0)
        self.assertFalse(queues_rec["is_warning"])


if __name__ == "__main__":
    unittest.main()

