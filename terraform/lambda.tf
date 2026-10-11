# ==============================================================================
# AWS Lambda Packaging & Function Resource
# ==============================================================================

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/build/quota_monitor_lambda.zip"
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-${var.environment}-logs"
  }
}

resource "aws_lambda_function" "quota_monitor" {
  function_name    = "${var.project_name}-${var.environment}"
  description      = "Monitors Amazon Connect Service Quotas and publishes CloudWatch metrics"
  role             = aws_iam_role.lambda.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  timeout     = 300
  memory_size = 256

  environment {
    variables = {
      THRESHOLD_PERCENTAGE = tostring(var.threshold_percentage)
      SNS_TOPIC_ARN        = aws_sns_topic.quota_alerts.arn
      CONNECT_INSTANCE_ID  = var.connect_instance_id
      LOG_LEVEL            = "INFO"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs,
    aws_iam_role_policy_attachment.lambda_attach
  ]

  tags = {
    Name = "${var.project_name}-${var.environment}"
  }
}

