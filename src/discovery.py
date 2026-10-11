"""Discovery module for Amazon Connect instances and Service Quotas limits across all related services."""

import logging
from typing import Any, Dict, List, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger("connect-quota-monitor.discovery")

# Connect service family codes in AWS Service Quotas
CONNECT_FAMILY_SERVICES = [
    "connect",           # Amazon Connect Core
    "connectcases",      # Amazon Connect Cases
    "connectcampaigns",  # Amazon Connect Outbound Campaigns
    "profile",           # Amazon Connect Customer Profiles
    "wisdom",            # Amazon Q in Connect / Wisdom
    "voiceid",           # Amazon Connect Voice ID
    "appintegrations",   # Amazon AppIntegrations
]


class ConnectDiscovery:
    """Discovers Amazon Connect instances and dynamic Service Quotas limits across the Connect family."""

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

    def fetch_all_service_quotas(self, service_codes: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Fetch active service quota limits for Amazon Connect and all related services from AWS Service Quotas.
        Returns a mapping of QuotaCode -> QuotaDetails (limit, name, service, usage_metric).
        """
        services_to_scan = service_codes or CONNECT_FAMILY_SERVICES
        quota_catalog: Dict[str, Dict[str, Any]] = {}

        for service_code in services_to_scan:
            try:
                paginator = self.sq_client.get_paginator("list_service_quotas")
                for page in paginator.paginate(ServiceCode=service_code):
                    for q in page.get("Quotas", []):
                        code = q.get("QuotaCode")
                        value = q.get("Value")
                        if code and value is not None:
                            quota_catalog[code] = {
                                "quota_code": code,
                                "name": q.get("QuotaName", code),
                                "limit": float(value),
                                "service": service_code,
                                "unit": q.get("Unit", "Count"),
                                "usage_metric": q.get("UsageMetric")
                            }
                logger.debug("Fetched quotas for service '%s'", service_code)
            except ClientError as e:
                err_code = e.response.get("Error", {}).get("Code")
                if err_code in ["NoSuchResourceException", "TemplatesNotAvailableForServiceException"]:
                    logger.debug("Service '%s' not present or supported in this region: %s", service_code, str(e))
                else:
                    logger.warning("Could not fetch service quotas for service '%s': %s", service_code, str(e))

        logger.info("Total discovered Service Quotas across all Connect services: %d", len(quota_catalog))
        return quota_catalog
