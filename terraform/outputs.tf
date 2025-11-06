output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${local.region}.amazonaws.com/${var.environment}"
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = aws_api_gateway_rest_api.main.id
}

output "bedrock_agent_id" {
  description = "Bedrock Agent ID"
  value       = aws_bedrockagent_agent.document_processor.agent_id
}

output "bedrock_agent_alias_id" {
  description = "Bedrock Agent Alias ID"
  value       = aws_bedrockagent_agent_alias.document_processor_alias.agent_alias_id
}

output "documents_bucket" {
  description = "S3 bucket for document storage"
  value       = aws_s3_bucket.documents.bucket
}

output "processed_data_bucket" {
  description = "S3 bucket for processed data"
  value       = aws_s3_bucket.processed_data.bucket
}

output "document_metadata_table" {
  description = "DynamoDB table for document metadata"
  value       = aws_dynamodb_table.document_metadata.name
}

output "processing_status_table" {
  description = "DynamoDB table for processing status"
  value       = aws_dynamodb_table.processing_status.name
}

output "tenant_config_table" {
  description = "DynamoDB table for tenant configuration"
  value       = aws_dynamodb_table.tenant_config.name
}

output "usage_tracking_table" {
  description = "DynamoDB table for usage tracking"
  value       = aws_dynamodb_table.usage_tracking.name
}

output "lambda_functions" {
  description = "Lambda function names"
  value = {
    upload_handler      = aws_lambda_function.upload_handler.function_name
    bedrock_supervisor  = aws_lambda_function.bedrock_supervisor.function_name
    bedrock_tools      = aws_lambda_function.bedrock_tools.function_name
    validator_agent    = aws_lambda_function.validator_agent.function_name
    extractor_agent    = aws_lambda_function.extractor_agent.function_name
    status_handler     = aws_lambda_function.status_handler.function_name
  }
}

output "cloudwatch_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = "https://${local.region}.console.aws.amazon.com/cloudwatch/home?region=${local.region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.alerts.arn
}

output "kms_key_id" {
  description = "KMS key ID for encryption"
  value       = aws_kms_key.s3_key.key_id
}
