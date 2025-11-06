# Document metadata table
resource "aws_dynamodb_table" "document_metadata" {
  name           = "${var.project_name}-document-metadata-${local.suffix}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "document_id"
  range_key      = "version"

  attribute {
    name = "document_id"
    type = "S"
  }

  attribute {
    name = "version"
    type = "N"
  }

  attribute {
    name = "tenant_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "document_type"
    type = "S"
  }

  global_secondary_index {
    name     = "tenant-created-index"
    hash_key = "tenant_id"
    range_key = "created_at"
  }

  global_secondary_index {
    name     = "type-created-index"
    hash_key = "document_type"
    range_key = "created_at"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = local.common_tags
}

# Processing status table
resource "aws_dynamodb_table" "processing_status" {
  name           = "${var.project_name}-processing-status-${local.suffix}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "request_id"

  attribute {
    name = "request_id"
    type = "S"
  }

  attribute {
    name = "tenant_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name     = "tenant-status-index"
    hash_key = "tenant_id"
    range_key = "status"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = local.common_tags
}

# Tenant configuration table
resource "aws_dynamodb_table" "tenant_config" {
  name           = "${var.project_name}-tenant-config-${local.suffix}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "tenant_id"

  attribute {
    name = "tenant_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = local.common_tags
}

# Usage tracking table
resource "aws_dynamodb_table" "usage_tracking" {
  name           = "${var.project_name}-usage-tracking-${local.suffix}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "tenant_id"
  range_key      = "date"

  attribute {
    name = "tenant_id"
    type = "S"
  }

  attribute {
    name = "date"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = local.common_tags
}
