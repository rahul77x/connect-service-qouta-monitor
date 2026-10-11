# ==============================================================================
# Terraform Outputs
# ==============================================================================

output "target_connect_instance_id" {
  description = "Target Amazon Connect Instance ID being monitored"
  value       = var.connect_instance_id
}

output "monitored_region" {
  description = "Target AWS region being monitored"
  value       = var.aws_region
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for service quota alerts"
  value       = aws_sns_topic.quota_alerts.arn
}

output "sns_topic_name" {
  description = "Name of the SNS topic"
  value       = aws_sns_topic.quota_alerts.name
}

output "lambda_function_name" {
  description = "Name of the Quota Monitor Lambda function"
  value       = aws_lambda_function.quota_monitor.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Quota Monitor Lambda function"
  value       = aws_lambda_function.quota_monitor.arn
}

output "cloudwatch_dashboard_name" {
  description = "Name of the CloudWatch Service Quota Dashboard"
  value       = aws_cloudwatch_dashboard.connect_quotas.dashboard_name
}

output "cloudwatch_dashboard_url" {
  description = "Direct AWS Console URL to access the CloudWatch Dashboard"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.connect_quotas.dashboard_name}"
}

output "eventbridge_schedule" {
  description = "Active schedule expression for the quota monitor scan"
  value       = var.schedule_expression
}

