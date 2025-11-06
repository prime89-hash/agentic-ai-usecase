# Lambda layer for common dependencies
resource "aws_lambda_layer_version" "common_layer" {
  filename         = "../src/layers/common-layer.zip"
  layer_name       = "${var.project_name}-common-layer-${local.suffix}"
  source_code_hash = filebase64sha256("../src/layers/common-layer.zip")

  compatible_runtimes = ["python3.9"]
  description         = "Common dependencies for financial document processing"
}

# Upload handler Lambda
resource "aws_lambda_function" "upload_handler" {
  filename         = "../src/functions/upload-handler.zip"
  function_name    = "${var.project_name}-upload-handler-${local.suffix}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "handler.lambda_handler"
  source_code_hash = filebase64sha256("../src/functions/upload-handler.zip")
  runtime         = "python3.9"
  timeout         = 30
  memory_size     = 256

  layers = [aws_lambda_layer_version.common_layer.arn]

  environment {
    variables = {
      DOCUMENTS_BUCKET = aws_s3_bucket.documents.bucket
      METADATA_TABLE   = aws_dynamodb_table.document_metadata.name
      REGION          = local.region
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = local.common_tags
}

# Bedrock Agent Supervisor (replaces multiple agent functions)
resource "aws_lambda_function" "bedrock_supervisor" {
  filename         = "../src/functions/bedrock-supervisor.zip"
  function_name    = "${var.project_name}-bedrock-supervisor-${local.suffix}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "handler.lambda_handler"
  source_code_hash = filebase64sha256("../src/functions/bedrock-supervisor.zip")
  runtime         = "python3.9"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  layers = [aws_lambda_layer_version.common_layer.arn]

  environment {
    variables = {
      BEDROCK_AGENT_ID       = aws_bedrockagent_agent.document_processor.agent_id
      BEDROCK_AGENT_ALIAS_ID = aws_bedrockagent_agent_alias.document_processor_alias.agent_alias_id
      STATUS_TABLE           = aws_dynamodb_table.processing_status.name
      USAGE_TRACKING_TABLE   = aws_dynamodb_table.usage_tracking.name
      REGION                = local.region
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = local.common_tags
}

# Bedrock Agent Tools (unified tool functions)
resource "aws_lambda_function" "bedrock_tools" {
  filename         = "../src/functions/bedrock-tools.zip"
  function_name    = "${var.project_name}-bedrock-tools-${local.suffix}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "handler.lambda_handler"
  source_code_hash = filebase64sha256("../src/functions/bedrock-tools.zip")
  runtime         = "python3.9"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  layers = [aws_lambda_layer_version.common_layer.arn]

  environment {
    variables = {
      DOCUMENTS_BUCKET     = aws_s3_bucket.documents.bucket
      PROCESSED_BUCKET     = aws_s3_bucket.processed_data.bucket
      METADATA_TABLE       = aws_dynamodb_table.document_metadata.name
      STATUS_TABLE         = aws_dynamodb_table.processing_status.name
      EXTRACTOR_FUNCTION   = aws_lambda_function.extractor_agent.function_name
      REGION              = local.region
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = local.common_tags
}

# Validator agent Lambda (simplified for S3 triggers)
resource "aws_lambda_function" "validator_agent" {
  filename         = "../src/functions/validator-agent.zip"
  function_name    = "${var.project_name}-validator-agent-${local.suffix}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "handler.lambda_handler"
  source_code_hash = filebase64sha256("../src/functions/validator-agent.zip")
  runtime         = "python3.9"
  timeout         = 300
  memory_size     = 512

  layers = [aws_lambda_layer_version.common_layer.arn]

  environment {
    variables = {
      DOCUMENTS_BUCKET     = aws_s3_bucket.documents.bucket
      METADATA_TABLE       = aws_dynamodb_table.document_metadata.name
      STATUS_TABLE         = aws_dynamodb_table.processing_status.name
      EXTRACTOR_FUNCTION   = aws_lambda_function.extractor_agent.function_name
      NOTIFICATION_EMAIL   = var.notification_email
      REGION              = local.region
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = local.common_tags
}

# Extractor agent Lambda (keeps Textract integration)
resource "aws_lambda_function" "extractor_agent" {
  filename         = "../src/functions/extractor-agent.zip"
  function_name    = "${var.project_name}-extractor-agent-${local.suffix}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "handler.lambda_handler"
  source_code_hash = filebase64sha256("../src/functions/extractor-agent.zip")
  runtime         = "python3.9"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory_size

  layers = [aws_lambda_layer_version.common_layer.arn]

  environment {
    variables = {
      DOCUMENTS_BUCKET     = aws_s3_bucket.documents.bucket
      PROCESSED_BUCKET     = aws_s3_bucket.processed_data.bucket
      METADATA_TABLE       = aws_dynamodb_table.document_metadata.name
      STATUS_TABLE         = aws_dynamodb_table.processing_status.name
      REGION              = local.region
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = local.common_tags
}

# Status handler Lambda
resource "aws_lambda_function" "status_handler" {
  filename         = "../src/functions/status-handler.zip"
  function_name    = "${var.project_name}-status-handler-${local.suffix}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "handler.lambda_handler"
  source_code_hash = filebase64sha256("../src/functions/status-handler.zip")
  runtime         = "python3.9"
  timeout         = 30
  memory_size     = 256

  layers = [aws_lambda_layer_version.common_layer.arn]

  environment {
    variables = {
      STATUS_TABLE = aws_dynamodb_table.processing_status.name
      REGION      = local.region
    }
  }

  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  tags = local.common_tags
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "upload_handler_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "bedrock_supervisor_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bedrock_supervisor.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "status_handler_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.status_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# Bedrock Agent permissions for tools Lambda
resource "aws_lambda_permission" "bedrock_tools_permission" {
  statement_id  = "AllowExecutionFromBedrock"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.bedrock_tools.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = aws_bedrockagent_agent.document_processor.agent_arn
}

# S3 trigger for validator agent
resource "aws_lambda_permission" "validator_s3_permission" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.validator_agent.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.documents.arn
}

resource "aws_s3_bucket_notification" "documents_notification" {
  bucket = aws_s3_bucket.documents.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.validator_agent.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
  }

  depends_on = [aws_lambda_permission.validator_s3_permission]
}
