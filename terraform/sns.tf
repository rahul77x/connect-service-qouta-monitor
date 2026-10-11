# ==============================================================================
# Amazon SNS Topic for Service Quota Alerts
# Created as a dummy/baseline topic ready for manual subscriptions (email, SMS, etc.)
# ==============================================================================

resource "aws_sns_topic" "quota_alerts" {
  name         = "${var.project_name}-${var.environment}-alerts"
  display_name = "Connect Quota Alerts (${var.environment})"

  # Banking / Security best practices: enable server-side encryption
  kms_master_key_id = "alias/aws/sns"

  tags = {
    Name = "${var.project_name}-${var.environment}-alerts"
  }
}

# Policy allowing CloudWatch Alarms and Lambda to publish to this topic
resource "aws_sns_topic_policy" "quota_alerts_policy" {
  arn = aws_sns_topic.quota_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudWatchAlarmsPublish"
        Effect    = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action   = "sns:Publish"
        Resource = aws_sns_topic.quota_alerts.arn
      },
      {
        Sid       = "AllowLambdaPublish"
        Effect    = "Allow"
        Principal = {
          AWS = aws_iam_role.lambda.arn
        }
        Action   = "sns:Publish"
        Resource = aws_sns_topic.quota_alerts.arn
      }
    ]
  })
}

