# ==============================================================================
# IAM Role and Least-Privilege Execution Policy for Quota Monitor Lambda
# ==============================================================================

resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-${var.environment}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-lambda-role"
  }
}

resource "aws_iam_policy" "lambda_policy" {
  name        = "${var.project_name}-${var.environment}-policy"
  description = "Least privilege permissions for Amazon Connect Quota Monitor"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logging
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.project_name}-${var.environment}:*"
      },

      # CloudWatch Metrics (Read native Connect metrics & write custom quota metrics)
      {
        Sid    = "CloudWatchMetrics"
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "cloudwatch:GetMetricData",
          "cloudwatch:ListMetrics"
        ]
        Resource = "*"
      },

      # Amazon Connect Family Discovery and Resource Counting
      {
        Sid    = "ConnectFamilyReadOnly"
        Effect = "Allow"
        Action = [
          "connect:List*",
          "connect:Describe*",
          "connectcases:List*",
          "connectcases:Get*",
          "connectcampaigns:List*",
          "connectcampaigns:Get*",
          "profile:List*",
          "profile:Get*",
          "wisdom:List*",
          "wisdom:Get*",
          "voiceid:List*",
          "voiceid:Describe*",
          "appintegrations:List*",
          "appintegrations:Get*"
        ]
        Resource = "*"
      },

      # AWS Service Quotas Access
      {
        Sid    = "ServiceQuotasReadOnly"
        Effect = "Allow"
        Action = [
          "servicequotas:ListServiceQuotas",
          "servicequotas:GetServiceQuota",
          "servicequotas:ListServices"
        ]
        Resource = "*"
      },

      # SNS Alert Publishing
      {
        Sid    = "SNSPublishAlerts"
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.quota_alerts.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

