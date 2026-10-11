# ==============================================================================
# CloudWatch Metric Alarms (Real-Time Sub-Minute Telephony Alarms & Quota Thresholds)
# Scoped strictly to the targeted Amazon Connect instance
# ==============================================================================

# 1. Critical Telephony Drop Alarm (1-minute immediate evaluation for target instance)
resource "aws_cloudwatch_metric_alarm" "calls_breaching_quota" {
  alarm_name          = "${var.project_name}-${var.environment}-${var.connect_instance_id}-calls-breached"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CallsBreachingConcurrencyQuota"
  namespace           = "AWS/Connect"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "CRITICAL: Callers dropped or rejected in Amazon Connect instance ${var.connect_instance_id} due to concurrent call quota breach!"
  alarm_actions       = [aws_sns_topic.quota_alerts.arn]
  ok_actions          = [aws_sns_topic.quota_alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    InstanceId = var.connect_instance_id
  }

  tags = {
    Severity   = "CRITICAL"
    InstanceId = var.connect_instance_id
  }
}

# 2. Throttled Calls Alarm (1-minute immediate evaluation for target instance)
resource "aws_cloudwatch_metric_alarm" "throttled_calls" {
  alarm_name          = "${var.project_name}-${var.environment}-${var.connect_instance_id}-throttled-calls"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ThrottledCalls"
  namespace           = "AWS/Connect"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "WARNING: Amazon Connect instance ${var.connect_instance_id} is experiencing call throttling."
  alarm_actions       = [aws_sns_topic.quota_alerts.arn]
  ok_actions          = [aws_sns_topic.quota_alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    InstanceId = var.connect_instance_id
  }

  tags = {
    Severity   = "WARNING"
    InstanceId = var.connect_instance_id
  }
}

# 3. Peak Quota Utilization Warning Alarm for Target Instance
resource "aws_cloudwatch_metric_alarm" "peak_quota_utilization" {
  alarm_name          = "${var.project_name}-${var.environment}-${var.connect_instance_id}-quota-utilization"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "QuotaUtilizationPercent"
  namespace           = "AmazonConnect/ServiceQuotas"
  period              = 300
  statistic           = "Maximum"
  threshold           = var.threshold_percentage
  alarm_description   = "WARNING: Amazon Connect instance ${var.connect_instance_id} quota utilization reached or exceeded ${var.threshold_percentage}%."
  alarm_actions       = [aws_sns_topic.quota_alerts.arn]
  ok_actions          = [aws_sns_topic.quota_alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    InstanceId = var.connect_instance_id
  }

  tags = {
    Severity   = "WARNING"
    InstanceId = var.connect_instance_id
  }
}
