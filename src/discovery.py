"""Discovery module for Amazon Connect instances and Service Quotas limits."""

import logging
from typing import Any, Dict, List, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger("connect-quota-monitor.discovery")


class ConnectDiscovery:
    """Discovers Amazon Connect instances and dynamic Service Quotas limits."""

    def __init__(self, connect_client, service_quotas_client):
        self.connect_client = connect_client
        self.sq_client = service_quotas_client

    def discover_instances(self, target_instance_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Discover Amazon Connect instances in the current region.

        If target_instance_id is provided, only that instance is returned.
        Otherwise, auto-discovers all instances via list_instances.
        """
        instances = []
        if target_instance_id:
            logger.info("Target instance ID specified: %s", target_instance_id)
            try:
                response = self.connect_client.describe_instance(InstanceId=target_instance_id)
                inst = response.get("Instance", {})
                instances.append({
                    "id": inst.get("Id", target_instance_id),
                    "arn": inst.get("Arn", ""),
                    "alias": inst.get("InstanceAlias", target_instance_id),
                    "status": inst.get("InstanceStatus", "ACTIVE")
                })
                return instances
            except ClientError as e:
                logger.error("Failed to describe instance %s: %s", target_instance_id, str(e))
                # Fallback to minimal dict so monitoring can attempt execution
                return [{
                    "id": target_instance_id,
                    "arn": "",
                    "alias": target_instance_id,
                    "status": "UNKNOWN"
                }]

        logger.info("Auto-discovering all Amazon Connect instances in region...")
        try:
            paginator = self.connect_client.get_paginator("list_instances")
            for page in paginator.paginate():
                for item in page.get("InstanceSummaryList", []):
                    instances.append({
                        "id": item.get("Id"),
                        "arn": item.get("Arn"),
                        "alias": item.get("InstanceAlias", item.get("Id")),
                        "status": item.get("InstanceStatus", "ACTIVE")
                    })
            logger.info("Discovered %d Amazon Connect instance(s)", len(instances))
        except ClientError as e:
            logger.error("Failed to list Amazon Connect instances: %s", str(e))
            raise

        return instances

    def fetch_service_quotas(self, service_code: str = "connect") -> Dict[str, float]:
        """
        Fetch active service quota limits for Amazon Connect from AWS Service Quotas.
        Returns a mapping of QuotaCode -> QuotaValue (limit).
        """
        quota_limits: Dict[str, float] = {}
        try:
            paginator = self.sq_client.get_paginator("list_service_quotas")
            for page in paginator.paginate(ServiceCode=service_code):
                for q in page.get("Quotas", []):
                    code = q.get("QuotaCode")
                    value = q.get("Value")
                    if code and value is not None:
                        quota_limits[code] = float(value)
            logger.info("Fetched %d active service quota limits for '%s'", len(quota_limits), service_code)
        except ClientError as e:
            logger.warning("Could not fetch service quotas from API (will use defaults): %s", str(e))

        return quota_limits

