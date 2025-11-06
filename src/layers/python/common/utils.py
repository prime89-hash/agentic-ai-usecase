"""
Common utilities for financial document processing
"""
import json
import boto3
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class AWSClients:
    """Singleton AWS clients"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.s3 = boto3.client('s3')
            self.dynamodb = boto3.resource('dynamodb')
            self.lambda_client = boto3.client('lambda')
            self.textract = boto3.client('textract')
            self.bedrock = boto3.client('bedrock-runtime')
            self.ses = boto3.client('ses')
            self._initialized = True

def generate_id() -> str:
    """Generate unique ID"""
    return str(uuid.uuid4())

def get_current_timestamp() -> str:
    """Get current ISO timestamp"""
    return datetime.now(timezone.utc).isoformat()

def create_response(status_code: int, body: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Create standardized API response"""
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body)
    }

def extract_tenant_id(event: Dict[str, Any]) -> str:
    """Extract tenant ID from request context"""
    # In production, this would extract from JWT token or API key
    # For demo purposes, using a header or default
    headers = event.get('headers', {})
    return headers.get('x-tenant-id', 'default-tenant')

def validate_request_body(event: Dict[str, Any], required_fields: list) -> Dict[str, Any]:
    """Validate request body has required fields"""
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in request body")
    
    missing_fields = [field for field in required_fields if field not in body]
    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")
    
    return body

def update_usage_tracking(tenant_id: str, operation: str, cost: float = 0.0):
    """Update usage tracking for billing"""
    try:
        clients = AWSClients()
        table_name = os.environ['USAGE_TRACKING_TABLE']
        table = clients.dynamodb.Table(table_name)
        
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        table.update_item(
            Key={
                'tenant_id': tenant_id,
                'date': today
            },
            UpdateExpression='ADD #op :inc, #cost :cost_inc',
            ExpressionAttributeNames={
                '#op': operation,
                '#cost': 'total_cost'
            },
            ExpressionAttributeValues={
                ':inc': 1,
                ':cost_inc': cost
            }
        )
    except Exception as e:
        logger.error(f"Failed to update usage tracking: {str(e)}")

def invoke_bedrock_model(prompt: str, model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0", max_tokens: int = 4000) -> str:
    """Invoke Bedrock model with prompt"""
    clients = AWSClients()
    
    body = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.1
    }
    
    response = clients.bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps(body)
    )
    
    result = json.loads(response['body'].read())
    return result['content'][0]['text']

def send_notification_email(to_email: str, subject: str, body: str):
    """Send notification email via SES"""
    try:
        clients = AWSClients()
        clients.ses.send_email(
            Source='noreply@company.com',
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")

import os
