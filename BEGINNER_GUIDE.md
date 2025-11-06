# Complete Beginner's Guide to Agentic AI Financial Document Processing

## 🎯 What We're Building

A smart system that:
1. **Accepts financial documents** (PDFs, Excel files)
2. **Reads and understands** the content using AI
3. **Answers questions** about the documents
4. **Performs calculations** like debt-to-equity ratios
5. **Provides compliance reports**

## 📚 Prerequisites

### What You Need to Know
- **Basic computer skills** (file management, command line basics)
- **No Python experience required** - we'll explain everything
- **No AWS experience required** - step-by-step instructions provided

### What You Need to Install
1. **AWS Account** (free tier available)
2. **Python 3.9+** 
3. **AWS CLI**
4. **Terraform**
5. **Git**

## 🛠️ Step 1: Environment Setup

### Install Python (Windows)
```bash
# Download from python.org and install
# Or use chocolatey:
choco install python

# Verify installation
python --version
```

### Install Python (Mac)
```bash
# Using homebrew
brew install python

# Verify installation
python3 --version
```

### Install AWS CLI
```bash
# Windows
choco install awscli

# Mac
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify
aws --version
```

### Install Terraform
```bash
# Windows
choco install terraform

# Mac
brew install terraform

# Verify
terraform --version
```

## 🔑 Step 2: AWS Account Setup

### Create AWS Account
1. Go to [aws.amazon.com](https://aws.amazon.com)
2. Click "Create AWS Account"
3. Follow the signup process
4. **Important**: Enable free tier to avoid charges

### Configure AWS CLI
```bash
# Run this command and enter your credentials
aws configure

# You'll need:
# - AWS Access Key ID (from AWS Console > IAM > Users)
# - AWS Secret Access Key
# - Default region (e.g., us-east-1)
# - Default output format (json)
```

### Request Bedrock Access
1. Go to AWS Console > Bedrock
2. Click "Model access" in left menu
3. Request access to "Claude 3 Sonnet" model
4. Wait for approval (usually instant)

## 📁 Step 3: Download and Setup Project

### Clone the Project
```bash
# Create a folder for your projects
mkdir my-projects
cd my-projects

# Clone our project
git clone <repository-url>
cd agentic-ai-usecase

# Look at the project structure
ls -la
```

### Project Structure Explained
```
agentic-ai-usecase/
├── terraform/          # Infrastructure code (AWS resources)
├── src/                # Application code (Python functions)
│   ├── functions/      # Individual Lambda functions
│   └── layers/         # Shared code libraries
├── test/               # Testing scripts
└── docs/               # Documentation
```

## 🏗️ Step 4: Understanding the Architecture

### Simple Explanation
```
User uploads document → AWS stores it → AI reads it → AI answers questions
```

### Detailed Flow
```
1. User uploads PDF via web interface
2. Document stored in S3 (AWS file storage)
3. Bedrock Agent (AI) processes the document
4. Textract (AWS OCR) extracts text
5. AI analyzes and structures the data
6. User asks questions or requests calculations
7. AI provides intelligent responses
```

### AWS Services Used
- **S3**: File storage (like Google Drive)
- **Lambda**: Code execution (runs our Python code)
- **API Gateway**: Web API (handles web requests)
- **DynamoDB**: Database (stores document info)
- **Bedrock**: AI service (the smart brain)
- **Textract**: OCR service (reads text from images/PDFs)

## 🐍 Step 5: Understanding the Python Code

### Basic Python Concepts We Use

#### 1. Functions
```python
def hello_world():
    """This is a function that prints hello"""
    print("Hello, World!")
    return "success"

# Call the function
result = hello_world()
```

#### 2. Dictionaries (Key-Value pairs)
```python
# Like a real dictionary - word and definition
document_info = {
    "filename": "financial_report.pdf",
    "size": 1024,
    "type": "pdf"
}

# Access values
print(document_info["filename"])  # prints: financial_report.pdf
```

#### 3. Lists (Arrays)
```python
# List of document IDs
document_ids = ["doc1", "doc2", "doc3"]

# Access first item
first_doc = document_ids[0]  # "doc1"
```

#### 4. JSON (Data format)
```python
import json

# Convert dictionary to JSON string
data = {"name": "John", "age": 30}
json_string = json.dumps(data)

# Convert JSON string back to dictionary
data_back = json.loads(json_string)
```

#### 5. Try/Except (Error handling)
```python
try:
    # Try to do something that might fail
    result = 10 / 0
except Exception as e:
    # Handle the error
    print(f"Error occurred: {e}")
    result = None
```

## 📝 Step 6: Code Review - Upload Handler

Let's examine the upload handler function step by step:

```python
"""
Upload handler - Generates presigned URLs for document upload
"""
import json
import os
from common.utils import AWSClients, create_response, extract_tenant_id, generate_id, get_current_timestamp, update_usage_tracking

def lambda_handler(event, context):
    """Handle upload URL generation requests"""
    try:
        # Extract tenant ID (which customer is making the request)
        tenant_id = extract_tenant_id(event)
        
        # Parse request body (get the data sent by user)
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename')
        
        # Check if filename was provided
        if not filename:
            return create_response(400, {'error': 'filename is required'})
        
        # Generate unique document ID
        document_id = generate_id()
        
        # Create S3 key with tenant isolation (organize files by customer)
        s3_key = f"uploads/{tenant_id}/{document_id}/{filename}"
        
        # Generate presigned URL (secure upload link)
        clients = AWSClients()
        bucket_name = os.environ['DOCUMENTS_BUCKET']
        
        presigned_url = clients.s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
                'ContentType': 'application/octet-stream'
            },
            ExpiresIn=3600  # 1 hour expiry
        )
        
        # Store initial metadata in database
        metadata_table = clients.dynamodb.Table(os.environ.get('METADATA_TABLE', 'document-metadata'))
        metadata_table.put_item(
            Item={
                'document_id': document_id,
                'version': 1,
                'tenant_id': tenant_id,
                'filename': filename,
                's3_key': s3_key,
                'status': 'pending_upload',
                'created_at': get_current_timestamp(),
                'document_type': 'unknown'
            }
        )
        
        # Track usage for billing
        update_usage_tracking(tenant_id, 'upload_requests')
        
        # Return success response
        return create_response(200, {
            'upload_url': presigned_url,
            'document_id': document_id,
            'expires_in': 3600
        })
        
    except Exception as e:
        # Return error response if something goes wrong
        return create_response(500, {'error': str(e)})
```

### What This Code Does:
1. **Receives a request** to upload a document
2. **Generates a unique ID** for the document
3. **Creates a secure upload URL** that expires in 1 hour
4. **Stores document info** in the database
5. **Returns the upload URL** to the user

## 📝 Step 7: Code Review - Bedrock Agent Tools

```python
"""
Bedrock Agent Tools - Unified Lambda for all document processing operations
"""
import json
import os
import boto3
from typing import Dict, Any

def lambda_handler(event, context):
    """Handle all Bedrock Agent tool requests"""
    
    try:
        # Parse Bedrock Agent event (different format than regular Lambda)
        action_group = event.get('actionGroup', '')
        function = event.get('function', '')
        
        # Get request body from Bedrock Agent
        request_body = event.get('requestBody', {}).get('content', {}).get('application/json', {})
        if isinstance(request_body, str):
            request_body = json.loads(request_body)
        
        # Route to appropriate function based on what the AI agent wants to do
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
        
        # Return response in Bedrock Agent format
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

def validate_document(request_body: Dict[str, Any]) -> Dict[str, Any]:
    """Check if document exists and is accessible"""
    
    document_id = request_body.get('document_id')
    tenant_id = request_body.get('tenant_id')
    
    # Validate inputs
    if not document_id or not tenant_id:
        return {'error': 'Missing document_id or tenant_id'}
    
    try:
        # Connect to database
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['METADATA_TABLE'])
        
        # Look up document
        response = table.get_item(
            Key={'document_id': document_id, 'version': 1}
        )
        
        # Check if document exists
        if 'Item' not in response:
            return {'valid': False, 'error': 'Document not found'}
        
        metadata = response['Item']
        
        # Check if user has access to this document
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
```

### What This Code Does:
1. **Receives requests from Bedrock Agent** (the AI)
2. **Routes to the right function** based on what AI wants
3. **Validates documents** - checks if they exist and user has access
4. **Returns structured data** back to the AI

## 🚀 Step 8: Deployment Process

### Prepare for Deployment
```bash
# Navigate to project directory
cd agentic-ai-usecase

# Make sure you're in the right place
pwd
ls -la

# Check AWS credentials
aws sts get-caller-identity
```

### Deploy the System
```bash
# Navigate to source directory
cd src

# Make deploy script executable
chmod +x deploy.sh

# Run deployment (this will take 10-15 minutes)
./deploy.sh
```

### What Happens During Deployment:
1. **Builds Python packages** - Packages your code for AWS
2. **Creates AWS resources** - Sets up S3, Lambda, DynamoDB, etc.
3. **Configures Bedrock Agent** - Creates the AI agent
4. **Sets up API Gateway** - Creates web endpoints
5. **Configures monitoring** - Sets up logging and alerts

## 🧪 Step 9: Testing Your System

### Test 1: Check API Endpoint
```bash
# Get your API endpoint from deployment output
API_ENDPOINT="https://your-api-id.execute-api.us-east-1.amazonaws.com/production"

# Test basic connectivity
curl $API_ENDPOINT/v1/health
```

### Test 2: Upload a Document
```python
# Create a test script: test_upload.py
import requests
import json

# Your API endpoint
API_ENDPOINT = "https://your-api-id.execute-api.us-east-1.amazonaws.com/production"

# Request upload URL
response = requests.post(
    f"{API_ENDPOINT}/v1/upload",
    headers={
        'Content-Type': 'application/json',
        'x-tenant-id': 'test-tenant'
    },
    json={'filename': 'test-document.pdf'}
)

print("Upload URL Response:", response.json())
```

### Test 3: Process a Document
```python
# Create test_process.py
import requests
import json

API_ENDPOINT = "https://your-api-id.execute-api.us-east-1.amazonaws.com/production"

# Process document
response = requests.post(
    f"{API_ENDPOINT}/v1/process",
    headers={
        'Content-Type': 'application/json',
        'x-tenant-id': 'test-tenant'
    },
    json={
        'prompt': 'What is the total revenue in this document?',
        'file_ids': ['your-document-id']
    }
)

print("Processing Response:", response.json())
```

## 🔍 Step 10: Understanding the Results

### Successful Response Example:
```json
{
    "request_id": "12345-67890",
    "result": {
        "response": "Based on the financial document, the total revenue is $1,250,000 for the fiscal year 2023.",
        "confidence": "high",
        "sources": ["financial_statement.pdf"],
        "agent_processing": true
    },
    "processing_time": "real-time",
    "agent_used": true
}
```

### What Each Field Means:
- **request_id**: Unique identifier for tracking
- **result.response**: The AI's answer to your question
- **result.confidence**: How confident the AI is (high/medium/low)
- **result.sources**: Which documents were used
- **agent_used**: Confirms Bedrock Agent was used

## 🐛 Step 11: Troubleshooting Common Issues

### Issue 1: "Access Denied" Errors
```bash
# Check AWS credentials
aws sts get-caller-identity

# If this fails, reconfigure:
aws configure
```

### Issue 2: Bedrock Access Denied
```bash
# Check Bedrock model access in AWS Console
# Go to: Bedrock > Model access > Request access to Claude 3 Sonnet
```

### Issue 3: Terraform Errors
```bash
# If deployment fails, check Terraform state
cd terraform
terraform plan

# If needed, destroy and redeploy
terraform destroy
terraform apply
```

### Issue 4: Lambda Function Errors
```bash
# Check CloudWatch logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/"

# View specific function logs
aws logs tail /aws/lambda/your-function-name --follow
```

## 📊 Step 12: Monitoring Your System

### CloudWatch Dashboard
1. Go to AWS Console > CloudWatch
2. Click "Dashboards" in left menu
3. Find your dashboard (named after your project)
4. Monitor metrics like:
   - API requests per minute
   - Lambda function duration
   - Error rates
   - Bedrock Agent invocations

### Cost Monitoring
```bash
# Check current month costs
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

## 🎓 Step 13: Next Steps for Learning

### Beginner Level
1. **Modify agent instructions** in `bedrock_agents.tf`
2. **Add new document types** in validation logic
3. **Customize response formats** in tool functions

### Intermediate Level
1. **Add new tools** to the Bedrock Agent
2. **Implement user authentication**
3. **Add email notifications**
4. **Create a web interface**

### Advanced Level
1. **Multi-region deployment**
2. **Custom machine learning models**
3. **Advanced compliance rules**
4. **Integration with external systems**

## 📚 Learning Resources

### Python Basics
- [Python.org Tutorial](https://docs.python.org/3/tutorial/)
- [Automate the Boring Stuff](https://automatetheboringstuff.com/)

### AWS Basics
- [AWS Getting Started](https://aws.amazon.com/getting-started/)
- [AWS Free Tier](https://aws.amazon.com/free/)

### Bedrock and AI
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Bedrock Agents Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)

## 🆘 Getting Help

### When You're Stuck
1. **Check the logs** in CloudWatch
2. **Review error messages** carefully
3. **Search AWS documentation**
4. **Ask in AWS forums** or Stack Overflow
5. **Check GitHub issues** for similar problems

### Common Commands for Debugging
```bash
# Check AWS service status
aws sts get-caller-identity

# List your Lambda functions
aws lambda list-functions

# Check Bedrock agents
aws bedrock-agent list-agents

# View recent logs
aws logs tail /aws/lambda/function-name --since 1h
```

This guide should get you started from zero to a working AI document processing system! Take it step by step, and don't hesitate to ask for help when needed.
