# ==============================================================================
# Amazon CloudWatch Custom Dashboard (Bank IAM & SSO Compliant)
# Scoped strictly to the targeted Amazon Connect instance in the specified region
# ==============================================================================

resource "aws_cloudwatch_dashboard" "connect_quotas" {
  dashboard_name = "${var.project_name}-${var.environment}-${var.connect_instance_id}"

  dashboard_body = jsonencode({
    widgets = [
      # 1. Header Banner & Target Scope
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 2
        properties = {
          markdown = "## 📞 Amazon Connect Service Quota Dashboard (${upper(var.environment)})\n**Target Instance:** `${var.connect_instance_id}` | **Region:** `${var.aws_region}` | **Warning Threshold:** `${var.threshold_percentage}%`"
        }
      },

      # 2. Alarm Status Badges
      {
        type   = "alarm"
        x      = 0
        y      = 2
        width  = 24
        height = 3
        properties = {
          title = "Active Health & Telephony Alarm Status"
          alarms = [
            aws_cloudwatch_metric_alarm.calls_breaching_quota.arn,
            aws_cloudwatch_metric_alarm.throttled_calls.arn,
            aws_cloudwatch_metric_alarm.peak_quota_utilization.arn
          ]
        }
      },

      # 3. Speedometer Gauge: Peak Quota Utilization (%)
      {
        type   = "metric"
        x      = 0
        y      = 5
        width  = 8
        height = 6
        properties = {
          view    = "gauge"
          title   = "Peak Quota Utilization (%) - Target Instance"
          region  = var.aws_region
          metrics = [
            [
              "AmazonConnect/ServiceQuotas",
              "QuotaUtilizationPercent",
              "InstanceId", var.connect_instance_id,
              {
                "stat"   = "Maximum"
                "period" = 300
                "label"  = "Max Quota %"
              }
            ]
          ]
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
          annotations = {
            horizontal = [
              {
                color = "#ff7f0e"
                label = "Warning (${var.threshold_percentage}%)"
                value = var.threshold_percentage
              },
              {
                color = "#d62728"
                label = "Breached (100%)"
                value = 100
              }
            ]
          }
        }
      },

      # 4. Real-Time Active Concurrent Calls vs Quota Ceiling (Line Chart)
      {
        type   = "metric"
        x      = 8
        y      = 5
        width  = 16
        height = 6
        properties = {
          view    = "timeSeries"
          stacked = false
          title   = "Real-Time Active Concurrent Calls (Instance: ${var.connect_instance_id})"
          region  = var.aws_region
          metrics = [
            [
              "AWS/Connect",
              "ConcurrentCalls",
              "InstanceId", var.connect_instance_id,
              {
                "stat"   = "Maximum"
                "period" = 60
                "label"  = "Active Concurrent Calls"
                "color"  = "#1f77b4"
              }
            ],
            [
              "AWS/Connect",
              "CallsBreachingConcurrencyQuota",
              "InstanceId", var.connect_instance_id,
              {
                "stat"   = "Sum"
                "period" = 60
                "label"  = "Calls Breached / Dropped"
                "color"  = "#d62728"
              }
            ]
          ]
          yAxis = {
            left = {
              min   = 0
              label = "Call Count"
            }
          }
          annotations = {
            horizontal = [
              {
                color = "#ff7f0e"
                label = "Warning (80%)"
                value = 40
              },
              {
                color = "#d62728"
                label = "Default Quota Limit (50)"
                value = 50
              }
            ]
          }
        }
      },

      # 5. API Rate Limits (Transactions Per Second - TPS via Metric Math)
      {
        type   = "metric"
        x      = 0
        y      = 11
        width  = 12
        height = 6
        properties = {
          view    = "timeSeries"
          stacked = false
          title   = "Connect API Rate Limits (TPS)"
          region  = var.aws_region
          metrics = [
            [
              "AWS/Usage", "CallCount",
              "Service", "Connect",
              "Type", "API",
              "Resource", "GetContactAttributes",
              { "id" = "m1", "visible" = false, "period" = 60, "stat" = "Sum" }
            ],
            [
              { "expression" = "m1 / 60", "label" = "GetContactAttributes TPS", "id" = "e1", "color" = "#2ca02c" }
            ],
            [
              "AWS/Usage", "CallCount",
              "Service", "Connect",
              "Type", "API",
              "Resource", "UpdateContactAttributes",
              { "id" = "m2", "visible" = false, "period" = 60, "stat" = "Sum" }
            ],
            [
              { "expression" = "m2 / 60", "label" = "UpdateContactAttributes TPS", "id" = "e2", "color" = "#1f77b4" }
            ],
            [
              "AWS/Usage", "CallCount",
              "Service", "Connect",
              "Type", "API",
              "Resource", "StartOutboundVoiceContact",
              { "id" = "m3", "visible" = false, "period" = 60, "stat" = "Sum" }
            ],
            [
              { "expression" = "m3 / 60", "label" = "StartOutboundVoiceContact TPS", "id" = "e3", "color" = "#ff7f0e" }
            ]
          ]
          yAxis = {
            left = {
              min   = 0
              label = "TPS (req/sec)"
            }
          }
        }
      },

      # 6. Static Resource Allocations for Target Instance (Bar Chart)
      {
        type   = "metric"
        x      = 12
        y      = 11
        width  = 12
        height = 6
        properties = {
          view    = "bar"
          stacked = false
          title   = "Resource Allocations (Instance: ${var.connect_instance_id})"
          region  = var.aws_region
          metrics = [
            [
              "AmazonConnect/ServiceQuotas", "QuotaUsage",
              "InstanceId", var.connect_instance_id,
              "QuotaName", "Phone numbers per instance",
              { "stat" = "Maximum", "period" = 300, "label" = "Phone Numbers" }
            ],
            [
              "AmazonConnect/ServiceQuotas", "QuotaUsage",
              "InstanceId", var.connect_instance_id,
              "QuotaName", "Contact flows per instance",
              { "stat" = "Maximum", "period" = 300, "label" = "Contact Flows" }
            ],
            [
              "AmazonConnect/ServiceQuotas", "QuotaUsage",
              "InstanceId", var.connect_instance_id,
              "QuotaName", "Queues per instance",
              { "stat" = "Maximum", "period" = 300, "label" = "Queues" }
            ],
            [
              "AmazonConnect/ServiceQuotas", "QuotaUsage",
              "InstanceId", var.connect_instance_id,
              "QuotaName", "Routing profiles per instance",
              { "stat" = "Maximum", "period" = 300, "label" = "Routing Profiles" }
            ]
          ]
          yAxis = {
            left = {
              min   = 0
              label = "Count"
            }
          }
        }
      },

      # 7. Summary Table for Target Instance
      {
        type   = "metric"
        x      = 0
        y      = 17
        width  = 24
        height = 6
        properties = {
          view    = "table"
          title   = "Instance Quotas - Latest Utilization & Headroom Table"
          region  = var.aws_region
          metrics = [
            [
              "AmazonConnect/ServiceQuotas", "QuotaUtilizationPercent",
              "InstanceId", var.connect_instance_id,
              { "stat" = "Maximum", "period" = 300, "label" = "Utilization %" }
            ],
            [
              "AmazonConnect/ServiceQuotas", "QuotaUsage",
              "InstanceId", var.connect_instance_id,
              { "stat" = "Maximum", "period" = 300, "label" = "Usage Count" }
            ],
            [
              "AmazonConnect/ServiceQuotas", "QuotaLimit",
              "InstanceId", var.connect_instance_id,
              { "stat" = "Maximum", "period" = 300, "label" = "Limit Ceiling" }
            ]
          ]
        }
      }
    ]
  })
}
