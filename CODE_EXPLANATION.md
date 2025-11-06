# 📖 Code Explanation for Beginners

## Understanding the Agentic AI System

This document explains every piece of code in simple terms, perfect for Python beginners.

---

## 🏗️ Project Structure

```
agentic-ai-usecase/
├── terraform/              # Infrastructure (AWS setup)
│   ├── main.tf             # Main configuration
│   ├── bedrock_agents.tf   # AI agent setup
│   ├── lambda.tf           # Function definitions
│   └── ...
├── src/                    # Application code
│   ├── functions/          # Individual functions
│   │   ├── bedrock-supervisor/
│   │   ├── bedrock-tools/
│   │   └── ...
│   └── layers/             # Shared code
└── examples/               # Learning examples
```

---

## 🧠 How the System Works

### Simple Flow:
```
1. User uploads document → 2. AI reads it → 3. User asks questions → 4. AI answers
```

### Detailed Flow:
```
User Request → API Gateway → Lambda Function → Bedrock Agent → Tools → Response
```

---

## 📝 Code Walkthrough

### 1. Upload Handler (`src/functions/upload-handler/handler.py`)

This function creates secure upload links for documents.

```python
def lambda_handler(event, context):
    """
    This is the main function AWS calls when someone wants to upload a document
    
    event: Contains the request data (like filename)
    context: Contains AWS runtime information
    """
    try:
        # STEP 1: Get the customer ID (tenant_id)
        # This helps us keep different customers' data separate
        tenant_id = extract_tenant_id(event)
        
        # STEP 2: Parse the request
        # Convert JSON string to Python dictionary
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename')  # Get the filename
        
        # STEP 3: Validate input
        # Make sure they provided a filename
        if not filename:
            return create_response(400, {'error': 'filename is required'})
        
        # STEP 4: Generate unique ID
        # Every document gets a unique identifier
        document_id = generate_id()  # Creates something like "doc_12345"
        
        # STEP 5: Create storage path
        # Organize files by customer and document ID
        s3_key = f"uploads/{tenant_id}/{document_id}/{filename}"
        # Example: "uploads/company_abc/doc_12345/report.pdf"
        
        # STEP 6: Generate secure upload URL
        # This creates a temporary link that expires in 1 hour
        clients = AWSClients()  # Connect to AWS services
        bucket_name = os.environ['DOCUMENTS_BUCKET']  # Get bucket name
        
        presigned_url = clients.s3.generate_presigned_url(
            'put_object',  # Type of operation (upload)
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
                'ContentType': 'application/octet-stream'
            },
            ExpiresIn=3600  # 1 hour = 3600 seconds
        )
        
        # STEP 7: Save document info to database
        # Store metadata so we can track the document
        metadata_table = clients.dynamodb.Table(os.environ['METADATA_TABLE'])
        metadata_table.put_item(
            Item={
                'document_id': document_id,
                'version': 1,
                'tenant_id': tenant_id,
                'filename': filename,
                's3_key': s3_key,
                'status': 'pending_upload',  # Not uploaded yet
                'created_at': get_current_timestamp(),
                'document_type': 'unknown'  # We'll detect this later
            }
        )
        
        # STEP 8: Track usage (for billing)
        update_usage_tracking(tenant_id, 'upload_requests')
        
        # STEP 9: Return success response
        return create_response(200, {
            'upload_url': presigned_url,      # Where to upload
            'document_id': document_id,       # Document identifier
            'expires_in': 3600               # How long URL is valid
        })
        
    except Exception as e:
        # STEP 10: Handle errors
        # If anything goes wrong, return error message
        return create_response(500, {'error': str(e)})
```

**What this does in simple terms:**
1. Someone says "I want to upload report.pdf"
2. System creates a unique ID for the document
3. System creates a secure upload link
4. System saves document info in database
5. System returns the upload link
6. User can now upload their file using that link

---

### 2. Bedrock Supervisor (`src/functions/bedrock-supervisor/handler.py`)

This function talks to the AI agent to process requests.

```python
def lambda_handler(event, context):
    """
    This function receives user questions and sends them to the AI agent
    """
    try:
        # STEP 1: Extract user information
        tenant_id = extract_tenant_id(event)  # Which customer
        body = json.loads(event.get('body', '{}'))
        prompt = body.get('prompt', '')       # User's question
        file_ids = body.get('file_ids', [])   # Which documents to analyze
        
        # STEP 2: Validate input
        if not prompt or not file_ids:
            return create_response(400, {'error': 'Missing prompt or file_ids'})
        
        # STEP 3: Create tracking ID
        request_id = generate_id()  # Track this request
        
        # STEP 4: Save request status
        # Store that we're processing this request
        store_processing_status(request_id, tenant_id, prompt, file_ids, 'processing')
        
        # STEP 5: Talk to AI agent
        # This is where the magic happens!
        result = invoke_bedrock_agent(prompt, file_ids, tenant_id, context.aws_request_id)
        
        # STEP 6: Save results
        store_processing_status(request_id, tenant_id, prompt, file_ids, 'completed', result)
        
        # STEP 7: Track usage for billing
        update_usage_tracking(tenant_id, 'bedrock_agent_requests', 0.15)
        
        # STEP 8: Return results
        return create_response(200, {
            'request_id': request_id,
            'result': result,
            'processing_time': 'real-time',
            'agent_used': True
        })
        
    except Exception as e:
        # Handle errors
        return create_response(500, {'error': str(e)})

def invoke_bedrock_agent(prompt, file_ids, tenant_id, session_id):
    """
    This function talks to the Bedrock AI agent
    """
    
    # Connect to Bedrock Agent service
    bedrock_agent = boto3.client('bedrock-agent-runtime')
    
    # Create enhanced prompt with context
    enhanced_prompt = f"""
    Process this financial document request:
    
    User Request: {prompt}
    Document IDs: {file_ids}
    Tenant ID: {tenant_id}
    
    Instructions:
    1. First, validate that all documents are accessible for this tenant
    2. If this is a compliance calculation request:
       - Extract relevant financial data from the documents
       - Build the appropriate mathematical formula
       - Calculate the result and check against any thresholds
    3. If this is a Q&A request:
       - Retrieve document data
       - Answer the question based on the document content
    4. Provide a comprehensive, structured response
    """
    
    try:
        # Send request to AI agent
        response = bedrock_agent.invoke_agent(
            agentId=os.environ['BEDROCK_AGENT_ID'],        # Which AI agent
            agentAliasId=os.environ['BEDROCK_AGENT_ALIAS_ID'],  # Which version
            sessionId=f"session-{tenant_id}-{session_id}",      # Conversation ID
            inputText=enhanced_prompt                           # What to ask
        )
        
        # Process AI response
        completion = ""
        for event in response.get('completion', []):
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    completion += chunk['bytes'].decode('utf-8')
        
        # Try to parse as structured data
        try:
            structured_result = json.loads(completion)
        except json.JSONDecodeError:
            # If not JSON, return as text
            structured_result = {
                'response': completion,
                'type': 'text_response',
                'agent_processing': True
            }
        
        return structured_result
        
    except Exception as e:
        return {
            'error': f'Bedrock Agent invocation failed: {str(e)}',
            'fallback_used': True
        }
```

**What this does in simple terms:**
1. User asks "What's the revenue in document ABC?"
2. System creates a tracking ID for the request
3. System sends the question to the AI agent
4. AI agent processes the question and documents
5. AI agent returns an intelligent answer
6. System saves the result and returns it to user

---

### 3. Bedrock Tools (`src/functions/bedrock-tools/handler.py`)

This function provides tools that the AI agent can use.

```python
def lambda_handler(event, context):
    """
    This function provides tools for the Bedrock Agent to use
    The AI agent calls this when it needs to perform specific actions
    """
    
    try:
        # STEP 1: Parse Bedrock Agent request
        # Bedrock Agent sends requests in a special format
        action_group = event.get('actionGroup', '')
        function = event.get('function', '')
        
        # Get the data the AI agent sent
        request_body = event.get('requestBody', {}).get('content', {}).get('application/json', {})
        if isinstance(request_body, str):
            request_body = json.loads(request_body)
        
        # STEP 2: Route to the right tool
        # Based on what the AI agent wants to do
        if function == 'validate_document':
            result = validate_document(request_body)
        elif function == 'extract_data':
            result = extract_data(request_body)
        elif function == 'calculate_compliance':
            result = calculate_compliance(request_body)
        elif function == 'get_document_data':
            result = get_document_data(request_body)
        else:
            result = {'error': f'Unknown function: {function}'}
        
        # STEP 3: Return result in Bedrock format
        return {
            'response': {
                'actionGroup': action_group,
                'function': function,
                'functionResponse': {
                    'responseBody': {
                        'application/json': {
                            'body': json.dumps(result)
                        }
                    }
                }
            }
        }
        
    except Exception as e:
        # Handle errors
        return {
            'response': {
                'actionGroup': event.get('actionGroup', ''),
                'function': event.get('function', ''),
                'functionResponse': {
                    'responseBody': {
                        'application/json': {
                            'body': json.dumps({'error': str(e)})
                        }
                    }
                }
            }
        }

def validate_document(request_body):
    """
    Tool: Check if a document exists and user has access
    """
    
    document_id = request_body.get('document_id')
    tenant_id = request_body.get('tenant_id')
    
    # Check inputs
    if not document_id or not tenant_id:
        return {'error': 'Missing document_id or tenant_id'}
    
    try:
        # Connect to database
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['METADATA_TABLE'])
        
        # Look up the document
        response = table.get_item(
            Key={'document_id': document_id, 'version': 1}
        )
        
        # Check if document exists
        if 'Item' not in response:
            return {'valid': False, 'error': 'Document not found'}
        
        metadata = response['Item']
        
        # Check if user owns this document
        if metadata.get('tenant_id') != tenant_id:
            return {'valid': False, 'error': 'Access denied'}
        
        # Return validation result
        return {
            'valid': True,
            'document_type': metadata.get('document_type', 'unknown'),
            'status': metadata.get('status', 'unknown'),
            'filename': metadata.get('filename'),
            'confidence': 0.95
        }
        
    except Exception as e:
        return {'valid': False, 'error': str(e)}

def calculate_compliance(request_body):
    """
    Tool: Calculate financial ratios and compliance metrics
    """
    
    formula = request_body.get('formula', '')
    parameters = request_body.get('parameters', {})
    threshold = request_body.get('threshold')
    
    # Check inputs
    if not formula or not parameters:
        return {'error': 'Missing formula or parameters'}
    
    try:
        # Build the calculation
        safe_formula = formula
        for param, value in parameters.items():
            if isinstance(value, (int, float)):
                safe_formula = safe_formula.replace(param, str(value))
        
        # Safety check - only allow math operations
        import re
        if not re.match(r'^[\d\.\+\-\*/\(\)\s]+$', safe_formula):
            return {'error': 'Invalid formula contains non-mathematical characters'}
        
        # Do the calculation
        result = eval(safe_formula)  # Calculate the result
        
        # Check compliance if threshold provided
        compliance_status = 'calculated'
        meets_threshold = None
        
        if threshold:
            if threshold.startswith('<'):
                threshold_value = float(threshold[1:].strip())
                meets_threshold = result < threshold_value
            elif threshold.startswith('>'):
                threshold_value = float(threshold[1:].strip())
                meets_threshold = result > threshold_value
            
            compliance_status = 'compliant' if meets_threshold else 'non_compliant'
        
        return {
            'success': True,
            'result': result,
            'formula_used': formula,
            'parameters_used': parameters,
            'compliance_status': compliance_status,
            'meets_threshold': meets_threshold,
            'threshold': threshold
        }
        
    except Exception as e:
        return {'error': str(e), 'success': False}
```

**What this does in simple terms:**
1. AI agent says "I need to validate document XYZ"
2. Tool checks if document exists and user has access
3. Tool returns "Yes, document is valid" or "No, access denied"
4. AI agent says "I need to calculate debt-to-equity ratio"
5. Tool performs the math: debt ÷ equity = ratio
6. Tool returns the result and compliance status

---

## 🔧 Utility Functions (`src/layers/python/common/utils.py`)

These are helper functions used throughout the system.

```python
def generate_id():
    """Generate a unique ID for documents or requests"""
    return str(uuid.uuid4())  # Creates something like "12345-67890-abcde"

def get_current_timestamp():
    """Get current time in standard format"""
    return datetime.now(timezone.utc).isoformat()  # "2024-01-15T10:30:00Z"

def create_response(status_code, body, headers=None):
    """Create a standard API response"""
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'  # Allow web browsers to access
    }
    
    return {
        'statusCode': status_code,  # 200 = success, 400 = error, etc.
        'headers': default_headers,
        'body': json.dumps(body)    # Convert to JSON string
    }

def extract_tenant_id(event):
    """Get customer ID from request"""
    headers = event.get('headers', {})
    return headers.get('x-tenant-id', 'default-tenant')

class AWSClients:
    """Helper class to connect to AWS services"""
    def __init__(self):
        self.s3 = boto3.client('s3')           # File storage
        self.dynamodb = boto3.resource('dynamodb')  # Database
        self.lambda_client = boto3.client('lambda')  # Functions
        self.textract = boto3.client('textract')    # OCR
        self.bedrock = boto3.client('bedrock-runtime')  # AI
```

**What these do in simple terms:**
- `generate_id()`: Creates unique identifiers like "doc_12345"
- `get_current_timestamp()`: Gets current time in standard format
- `create_response()`: Formats responses for web APIs
- `extract_tenant_id()`: Figures out which customer made the request
- `AWSClients`: Connects to different AWS services

---

## 🏗️ Infrastructure Code (Terraform)

### Main Configuration (`terraform/main.tf`)

```hcl
# This tells Terraform which cloud provider to use
provider "aws" {
  region = var.aws_region  # Which AWS region (like us-east-1)
  
  # Add these tags to all resources
  default_tags {
    tags = {
      Project     = "agentic-ai-financial-processing"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Get information about current AWS account
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Create random suffix for unique names
resource "random_id" "suffix" {
  byte_length = 4
}
```

### Bedrock Agent Configuration (`terraform/bedrock_agents.tf`)

```hcl
# Create the AI agent
resource "aws_bedrockagent_agent" "document_processor" {
  agent_name              = "${var.project_name}-document-processor-${local.suffix}"
  agent_resource_role_arn = aws_iam_role.bedrock_agent_role.arn
  foundation_model        = "anthropic.claude-3-sonnet-20240229-v1:0"
  
  # Instructions for the AI agent
  instruction = <<EOF
You are a financial document processing AI agent specialized in:

1. DOCUMENT VALIDATION: Check document format, type, and accessibility
2. DATA EXTRACTION: Extract structured financial data using Textract integration
3. COMPLIANCE CALCULATIONS: Perform financial ratio calculations and compliance checks
4. DOCUMENT Q&A: Answer questions about document content

Always use the appropriate tools for each task. For compliance calculations, build mathematical formulas from natural language and execute them with extracted parameters.
EOF

  # Define what tools the agent can use
  action_group {
    action_group_name = "document_operations"
    description       = "Core document processing operations"
    
    # Connect to our Lambda function that provides tools
    action_group_executor {
      lambda {
        lambda_arn = aws_lambda_function.bedrock_tools.arn
      }
    }

    # Define the API schema for tools
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
              # ... more API definition
            }
          }
          # ... more tool definitions
        }
      })
    }
  }
}
```

**What this does in simple terms:**
- Creates an AI agent in AWS Bedrock
- Gives the agent instructions on what it should do
- Connects the agent to tools (Lambda functions) it can use
- Defines what each tool does and how to call it

---

## 🔄 How Everything Works Together

### Complete Flow Example:

1. **User uploads document**:
   ```
   User → API Gateway → Upload Handler → S3 → Database
   ```

2. **User asks question**:
   ```
   User → API Gateway → Bedrock Supervisor → Bedrock Agent
   ```

3. **AI agent processes request**:
   ```
   Bedrock Agent → Bedrock Tools → Database/S3 → Textract → Calculations
   ```

4. **AI agent returns answer**:
   ```
   Bedrock Agent → Bedrock Supervisor → API Gateway → User
   ```

### Example Conversation:

**User**: "Upload financial_report.pdf"
**System**: "Here's your upload URL: https://s3.amazonaws.com/..."

**User**: "What's the total revenue in document doc_12345?"
**AI Agent**: 
1. "Let me validate document doc_12345" → calls validate_document tool
2. "Let me extract data from this document" → calls extract_data tool  
3. "Based on the financial report, total revenue is $1,250,000"

**User**: "Calculate debt-to-equity ratio"
**AI Agent**:
1. "Let me get the financial data" → calls get_document_data tool
2. "Let me calculate the ratio" → calls calculate_compliance tool
3. "Debt-to-equity ratio is 1.5, which is within acceptable limits"

---

## 🎯 Key Concepts for Beginners

### 1. **Serverless Functions (Lambda)**
- Think of them as small programs that run when needed
- You don't manage servers, AWS does it for you
- You only pay when they run

### 2. **APIs (Application Programming Interfaces)**
- Ways for programs to talk to each other
- Like a waiter taking your order to the kitchen
- Our API Gateway receives requests and routes them

### 3. **Databases (DynamoDB)**
- Store information in tables
- Like a spreadsheet with rows and columns
- Very fast for looking up specific items

### 4. **AI Agents (Bedrock)**
- Smart programs that can reason and make decisions
- Can use tools to perform actions
- Learn from instructions and examples

### 5. **Infrastructure as Code (Terraform)**
- Describe your cloud setup in files
- Terraform reads the files and creates everything
- Repeatable and version-controlled

This system combines all these concepts to create an intelligent document processing platform that can understand, analyze, and answer questions about financial documents automatically!
