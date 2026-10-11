"""Unit tests for the ConnectDiscovery module."""

import unittest
from unittest.mock import MagicMock

from src.discovery import ConnectDiscovery


class TestConnectDiscovery(unittest.TestCase):

    def test_discover_instances_with_target_id(self):
        mock_connect = MagicMock()
        mock_sq = MagicMock()

        mock_connect.describe_instance.return_value = {
            "Instance": {
                "Id": "inst-12345",
                "Arn": "arn:aws:connect:us-east-1:123456789012:instance/inst-12345",
                "InstanceAlias": "bank-prod-connect",
                "InstanceStatus": "ACTIVE"
            }
        }

        discovery = ConnectDiscovery(mock_connect, mock_sq)
        instances = discovery.discover_instances(target_instance_id="inst-12345")

        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]["id"], "inst-12345")
        self.assertEqual(instances[0]["alias"], "bank-prod-connect")
        mock_connect.describe_instance.assert_called_once_with(InstanceId="inst-12345")

    def test_discover_instances_auto_discovery(self):
        mock_connect = MagicMock()
        mock_sq = MagicMock()

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "InstanceSummaryList": [
                    {
                        "Id": "inst-1",
                        "Arn": "arn:aws:connect:us-east-1:123:instance/inst-1",
                        "InstanceAlias": "instance-one",
                        "InstanceStatus": "ACTIVE"
                    },
                    {
                        "Id": "inst-2",
                        "Arn": "arn:aws:connect:us-east-1:123:instance/inst-2",
                        "InstanceAlias": "instance-two",
                        "InstanceStatus": "ACTIVE"
                    }
                ]
            }
        ]
        mock_connect.get_paginator.return_value = mock_paginator

        discovery = ConnectDiscovery(mock_connect, mock_sq)
        instances = discovery.discover_instances()

        self.assertEqual(len(instances), 2)
        self.assertEqual(instances[0]["id"], "inst-1")
        self.assertEqual(instances[1]["id"], "inst-2")

    def test_fetch_service_quotas(self):
        mock_connect = MagicMock()
        mock_sq = MagicMock()

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Quotas": [
                    {"QuotaCode": "L-AA17A6B9", "Value": 5.0},
                    {"QuotaCode": "L-28B936FD", "Value": 100.0}
                ]
            }
        ]
        mock_sq.get_paginator.return_value = mock_paginator

        discovery = ConnectDiscovery(mock_connect, mock_sq)
        limits = discovery.fetch_service_quotas(service_code="connect")

        self.assertEqual(limits["L-AA17A6B9"], 5.0)
        self.assertEqual(limits["L-28B936FD"], 100.0)


if __name__ == "__main__":
    unittest.main()

