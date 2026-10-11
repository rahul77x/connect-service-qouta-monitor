"""Collector module for querying Connect API counts, CloudWatch metrics, and API rate TPS across all Connect services."""

import datetime
import logging
from typing import Any, Dict, List, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger("connect-quota-monitor.collector")


class QuotaCollector:
    """Collects current usage for Amazon Connect service quotas across all services and instances."""

    def __init__(self, connect_client, cloudwatch_client, quota_definitions: Dict[str, Any]):
        self.connect = connect_client
        self.cloudwatch = cloudwatch_client
        self.quota_defs = quota_definitions

    def collect_all_quotas(
        self,
        instances: List[Dict[str, Any]],
        quota_catalog: Dict[str, Any],
        threshold_percentage: float = 80.0
    ) -> List[Dict[str, Any]]:
        """
        Collect quota usage for all discovered instances and account-level quotas.
        Merges catalog definitions with dynamic Service Quotas discovery.
        """
        # Normalize quota limits map
        limits_map: Dict[str, float] = {}
        for code, details in quota_catalog.items():
            if isinstance(details, dict):
                limits_map[code] = float(details.get("limit", 0.0))
            else:
                limits_map[code] = float(details)

        # Build merged quota definitions (base catalog + dynamically discovered quotas)
        active_definitions = dict(self.quota_defs)
        for code, details in quota_catalog.items():
            if code not in active_definitions and isinstance(details, dict):
                # Dynamically classify discovered quota
                name = details.get("name", code)
                usage_metric = details.get("usage_metric") or {}
                method = "service_quotas"
                operation = ""

                if usage_metric.get("MetricName") == "CallCount" or "Rate of " in name:
                    method = "cloudwatch_api"
                    operation = (usage_metric.get("MetricDimensions") or {}).get("Resource")
                    if not operation:
                        operation = name.replace("Rate of ", "").replace(" API requests", "").strip()

                active_definitions[code] = {
                    "name": name,
                    "category": details.get("service", "CONNECT_FAMILY").upper(),
                    "scope": "ACCOUNT" if "per account" in name.lower() or "instance count" in name.lower() else "INSTANCE",
                    "method": method,
                    "service": details.get("service", "connect"),
                    "operation": operation,
                    "default_limit": details.get("limit", 0),
                    "unit": details.get("unit", "Count")
                }

        results: List[Dict[str, Any]] = []

        # 1. Process Account-level quotas
        account_results = self._collect_account_quotas(
            instances=instances,
            definitions=active_definitions,
            limits_map=limits_map,
            threshold_percentage=threshold_percentage
        )
        results.extend(account_results)

        # 2. Process Instance-level quotas for each instance
        for inst in instances:
            instance_id = inst.get("id")
            instance_alias = inst.get("alias", instance_id)
            inst_results = self._collect_instance_quotas(
                instance_id=instance_id,
                instance_alias=instance_alias,
                definitions=active_definitions,
                limits_map=limits_map,
                threshold_percentage=threshold_percentage
            )
            results.extend(inst_results)

        return results

    def _collect_account_quotas(
        self,
        instances: List[Dict[str, Any]],
        definitions: Dict[str, Any],
        limits_map: Dict[str, float],
        threshold_percentage: float
    ) -> List[Dict[str, Any]]:
        """Collect account-wide quotas (e.g. Instance Count, external connectors)."""
        records = []
        for code, qdef in definitions.items():
            if qdef.get("scope") != "ACCOUNT":
                continue

            limit = limits_map.get(code, float(qdef.get("default_limit", 0)))
            usage = 0.0

            if qdef.get("api") == "list_instances":
                usage = float(len(instances))

            util_pct = (usage / limit * 100.0) if limit > 0 else 0.0
            records.append({
                "quota_code": code,
                "quota_name": qdef.get("name", code),
                "category": qdef.get("category", "CORE_CONNECT"),
                "scope": "ACCOUNT",
                "instance_id": "ACCOUNT",
                "instance_alias": "Account-Wide",
                "usage": usage,
                "limit": limit,
                "unit": qdef.get("unit", "Count"),
                "utilization_percent": round(util_pct, 2),
                "threshold_percent": threshold_percentage,
                "is_warning": util_pct >= threshold_percentage and limit > 0,
                "is_breached": util_pct >= 100.0 and limit > 0
            })
        return records

    def _collect_instance_quotas(
        self,
        instance_id: str,
        instance_alias: str,
        definitions: Dict[str, Any],
        limits_map: Dict[str, float],
        threshold_percentage: float
    ) -> List[Dict[str, Any]]:
        """Collect instance-specific quotas for a single Connect instance."""
        records = []
        for code, qdef in definitions.items():
            if qdef.get("scope") != "INSTANCE":
                continue

            limit = limits_map.get(code, float(qdef.get("default_limit", 100)))
            method = qdef.get("method")
            usage = 0.0

            try:
                if method == "api_count":
                    usage = self._get_api_count(instance_id, qdef.get("api"))
                elif method == "cloudwatch":
                    metric_name = qdef.get("metric_name") or qdef.get("metric")
                    usage = self._get_cloudwatch_metric(
                        instance_id,
                        qdef.get("metric_namespace", "AWS/Connect"),
                        metric_name
                    )
                elif method == "cloudwatch_api":
                    operation = qdef.get("api_resource") or qdef.get("operation")
                    usage = self._get_cloudwatch_api_tps(operation)
                elif method == "service_quotas":
                    usage = 0.0  # Allocation / Limit tracking
            except Exception as e:
                logger.warning(
                    "Error measuring quota '%s' (%s) for instance %s: %s",
                    qdef.get("name"), code, instance_id, str(e)
                )
                usage = 0.0

            util_pct = (usage / limit * 100.0) if limit > 0 else 0.0
            records.append({
                "quota_code": code,
                "quota_name": qdef.get("name", code),
                "category": qdef.get("category", "CORE_CONNECT"),
                "scope": "INSTANCE",
                "instance_id": instance_id,
                "instance_alias": instance_alias,
                "usage": round(usage, 2),
                "limit": limit,
                "unit": qdef.get("unit", "Count"),
                "utilization_percent": round(util_pct, 2),
                "threshold_percent": threshold_percentage,
                "is_warning": util_pct >= threshold_percentage and limit > 0,
                "is_breached": util_pct >= 100.0 and limit > 0
            })
        return records

    def _get_api_count(self, instance_id: str, api_name: str) -> float:
        """Call Connect listing API and count total items across pagination."""
        if not api_name or not hasattr(self.connect, api_name):
            logger.debug("Connect client has no method: %s", api_name)
            return 0.0

        count = 0
        try:
            # Handle describe_user_hierarchy_structure separately
            if api_name == "describe_user_hierarchy_structure":
                resp = self.connect.describe_user_hierarchy_structure(InstanceId=instance_id)
                struct = resp.get("HierarchyStructure", {})
                return float(len([k for k, v in struct.items() if v]))

            # Standard paginated listing APIs
            paginator = self.connect.get_paginator(api_name)
            for page in paginator.paginate(InstanceId=instance_id):
                for key, val in page.items():
                    if isinstance(val, list) and key != "ResponseMetadata":
                        count += len(val)
        except ClientError as e:
            logger.debug("Could not count %s for instance %s: %s", api_name, instance_id, str(e))
            return 0.0
        except Exception as e:
            logger.debug("Unexpected error counting %s: %s", api_name, str(e))
            return 0.0

        return float(count)

    def _get_cloudwatch_metric(self, instance_id: str, namespace: str, metric_name: str) -> float:
        """Query CloudWatch for peak metric value over the past 30 minutes."""
        if not metric_name:
            return 0.0

        now = datetime.datetime.now(datetime.timezone.utc)
        start_time = now - datetime.timedelta(minutes=30)

        try:
            response = self.cloudwatch.get_metric_data(
                MetricDataQueries=[
                    {
                        "Id": "m1",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": namespace,
                                "MetricName": metric_name,
                                "Dimensions": [
                                    {"Name": "InstanceId", "Value": instance_id}
                                ]
                            },
                            "Period": 60,
                            "Stat": "Maximum"
                        },
                        "ReturnData": True
                    }
                ],
                StartTime=start_time,
                EndTime=now
            )
            values = response.get("MetricDataResults", [{}])[0].get("Values", [])
            return float(max(values)) if values else 0.0
        except ClientError as e:
            logger.debug("Could not fetch CloudWatch metric %s: %s", metric_name, str(e))
            return 0.0

    def _get_cloudwatch_api_tps(self, operation: str) -> float:
        """
        Query AWS/Usage namespace for API CallCount and derive transactions per second (TPS).
        Formula: CallCount / 60 seconds = TPS.
        """
        if not operation:
            return 0.0

        now = datetime.datetime.now(datetime.timezone.utc)
        start_time = now - datetime.timedelta(minutes=15)

        try:
            response = self.cloudwatch.get_metric_data(
                MetricDataQueries=[
                    {
                        "Id": "m1",
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/Usage",
                                "MetricName": "CallCount",
                                "Dimensions": [
                                    {"Name": "Service", "Value": "Connect"},
                                    {"Name": "Type", "Value": "API"},
                                    {"Name": "Resource", "Value": operation}
                                ]
                            },
                            "Period": 60,
                            "Stat": "Sum"
                        },
                        "ReturnData": True
                    }
                ],
                StartTime=start_time,
                EndTime=now
            )
            values = response.get("MetricDataResults", [{}])[0].get("Values", [])
            if values:
                peak_per_minute = max(values)
                return peak_per_minute / 60.0
            return 0.0
        except ClientError as e:
            logger.debug("Could not fetch CallCount for API %s: %s", operation, str(e))
            return 0.0
