variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "agentic-ai-finproc"
}

variable "api_throttle_rate" {
  description = "API Gateway throttle rate limit"
  type        = number
  default     = 1000
}

variable "api_throttle_burst" {
  description = "API Gateway throttle burst limit"
  type        = number
  default     = 2000
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 1024
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 900
}

variable "enable_xray" {
  description = "Enable X-Ray tracing"
  type        = bool
  default     = true
}

variable "enable_waf" {
  description = "Enable WAF for API Gateway"
  type        = bool
  default     = true
}

variable "document_retention_days" {
  description = "Document retention period in days"
  type        = number
  default     = 2555  # 7 years for financial compliance
}

variable "notification_email" {
  description = "Email for system notifications"
  type        = string
  default     = "admin@company.com"
}
