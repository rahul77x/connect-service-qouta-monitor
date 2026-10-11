variable "aws_region" {
  description = "AWS region where Amazon Connect is deployed"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (e.g. dev, test, prod)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
  default     = "connect-quota-monitor"
}

variable "threshold_percentage" {
  description = "Warning threshold percentage for quota utilization (1-100)"
  type        = number
  default     = 80

  validation {
    condition     = var.threshold_percentage >= 1 && var.threshold_percentage <= 100
    error_message = "threshold_percentage must be between 1 and 100."
  }
}

variable "connect_instance_id" {
  description = "Target Amazon Connect instance ID (UUID) or ARN to monitor in the specified region"
  type        = string

  validation {
    condition     = length(trimspace(var.connect_instance_id)) > 0
    error_message = "connect_instance_id must not be empty. Please specify your target Amazon Connect Instance ID or ARN."
  }
}

variable "schedule_expression" {
  description = "EventBridge schedule expression for the quota monitor scan"
  type        = string
  default     = "rate(15 minutes)"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project   = "Amazon Connect Service Quota Monitor"
    ManagedBy = "Terraform"
  }
}

