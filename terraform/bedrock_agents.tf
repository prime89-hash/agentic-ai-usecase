# Bedrock Agents Implementation

# IAM role for Bedrock Agent
resource "aws_iam_role" "bedrock_agent_role" {
  name = "${var.project_name}-bedrock-agent-role-${local.suffix}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "bedrock_agent_policy" {
  name = "${var.project_name}-bedrock-agent-policy-${local.suffix}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:${local.region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "bedrock_agent_policy_attachment" {
  role       = aws_iam_role.bedrock_agent_role.name
  policy_arn = aws_iam_policy.bedrock_agent_policy.arn
}

# Document Processing Agent
resource "aws_bedrockagent_agent" "document_processor" {
  agent_name              = "${var.project_name}-document-processor-${local.suffix}"
  agent_resource_role_arn = aws_iam_role.bedrock_agent_role.arn
  foundation_model        = "anthropic.claude-3-sonnet-20240229-v1:0"
  
  instruction = <<EOF
You are a financial document processing AI agent specialized in:

1. DOCUMENT VALIDATION: Check document format, type, and accessibility
2. DATA EXTRACTION: Extract structured financial data using Textract integration
3. COMPLIANCE CALCULATIONS: Perform financial ratio calculations and compliance checks
4. DOCUMENT Q&A: Answer questions about document content

Always use the appropriate tools for each task. For compliance calculations, build mathematical formulas from natural language and execute them with extracted parameters.

When processing requests:
- First validate document access
- Extract relevant data if needed
- Perform calculations for compliance requests
- Provide structured, accurate responses
- Include confidence scores and data sources
EOF

  action_group {
    action_group_name = "document_operations"
    description       = "Core document processing operations"
    
    action_group_executor {
      lambda {
        lambda_arn = aws_lambda_function.bedrock_tools.arn
      }
    }

    api_schema {
      payload = jsonencode({
        openapi = "3.0.0"
        info = {
          title   = "Document Processing Tools"
          version = "1.0.0"
        }
        paths = {
          "/validate_document" = {
            post = {
              description = "Validate document accessibility and format"
              requestBody = {
                required = true
                content = {
                  "application/json" = {
                    schema = {
                      type = "object"
                      properties = {
                        document_id = { type = "string" }
                        tenant_id = { type = "string" }
                      }
                      required = ["document_id", "tenant_id"]
                    }
                  }
                }
              }
            }
          }
          "/extract_data" = {
            post = {
              description = "Extract structured data from document using Textract"
              requestBody = {
                required = true
                content = {
                  "application/json" = {
                    schema = {
                      type = "object"
                      properties = {
                        document_id = { type = "string" }
                        tenant_id = { type = "string" }
                      }
                      required = ["document_id", "tenant_id"]
                    }
                  }
                }
              }
            }
          }
          "/calculate_compliance" = {
            post = {
              description = "Calculate financial ratios and compliance metrics"
              requestBody = {
                required = true
                content = {
                  "application/json" = {
                    schema = {
                      type = "object"
                      properties = {
                        formula = { type = "string" }
                        parameters = { type = "object" }
                        threshold = { type = "string" }
                      }
                      required = ["formula", "parameters"]
                    }
                  }
                }
              }
            }
          }
          "/get_document_data" = {
            post = {
              description = "Retrieve processed document data"
              requestBody = {
                required = true
                content = {
                  "application/json" = {
                    schema = {
                      type = "object"
                      properties = {
                        document_ids = { 
                          type = "array"
                          items = { type = "string" }
                        }
                        tenant_id = { type = "string" }
                      }
                      required = ["document_ids", "tenant_id"]
                    }
                  }
                }
              }
            }
          }
        }
      })
    }
  }
}

# Bedrock Agent Alias
resource "aws_bedrockagent_agent_alias" "document_processor_alias" {
  agent_alias_name = "LIVE"
  agent_id         = aws_bedrockagent_agent.document_processor.agent_id
  description      = "Live alias for document processing agent"
}
