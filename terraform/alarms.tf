# ==============================================================================
# CloudWatch Metric Alarms (Real-Time Sub-Minute Telephony Alarms & Quota Thresholds)
# ==============================================================================

# 1. Critical Telephony Drop Alarm (1-minute immediate evaluation)
resource "aws_cloudwatch_metric_alarm" "calls_breaching_quota" {
  alarm_name          = "${var.project_name}-${var.environment}-calls-breaching-quota"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CallsBreachingConcurrencyQuota"
  namespace           = "AWS/Connect"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "CRITICAL: Callers dropped or rejected due to Amazon Connect concurrent call quota breach!"
  alarm_actions       = [aws_sns_topic.quota_alerts.arn]
  ok_actions          = [aws_sns_topic.quota_alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Severity = "CRITICAL"
  }
}

# 2. Throttled Calls Alarm (1-minute immediate evaluation)
resource "aws_cloudwatch_metric_alarm" "throttled_calls" {
  alarm_name          = "${var.project_name}-${var.environment}-throttled-calls"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ThrottledCalls"
  namespace           = "AWS/Connect"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "WARNING: Amazon Connect calls are experiencing API/telephony throttling."
  alarm_actions       = [aws_sns_topic.quota_alerts.arn]
  ok_actions          = [aws_sns_topic.quota_alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Severity = "WARNING"
  }
}

# 3. Peak Quota Utilization Warning Alarm
resource "aws_cloudwatch_metric_alarm" "peak_quota_utilization" {
  alarm_name          = "${var.project_name}-${var.environment}-peak-quota-utilization"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "QuotaUtilizationPercent"
  namespace           = "AmazonConnect/ServiceQuotas"
  period              = 300
  statistic           = "Maximum"
  threshold           = var.threshold_percentage
  alarm_description   = "WARNING: Amazon Connect quota utilization has reached or exceeded ${var.threshold_percentage}%."
  alarm_actions       = [aws_sns_topic.quota_alerts.arn]
  ok_actions          = [aws_sns_topic.quota_alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Severity = "WARNING"
  }
}

