"""
Bedrock Agent Tool - Document Validator
"""
import json
import boto3
from typing import Dict, Any

def lambda_handler(event, context):
    """Bedrock Agent tool for document validation"""
    
    # Parse Bedrock Agent event
    agent_request = event.get('requestBody', {}).get('content', {}).get('application/json', {})
    parameters = event.get('parameters', [])
    
    # Extract parameters
    document_id = None
    tenant_id = None
    
    for param in parameters:
        if param['name'] == 'document_id':
            document_id = param['value']
        elif param['name'] == 'tenant_id':
            tenant_id = param['value']
    
    if not document_id or not tenant_id:
        return {
            'response': {
                'actionGroup': event['actionGroup'],
                'function': event['function'],
                'functionResponse': {
                    'responseBody': {
                        'application/json': {
                            'body': json.dumps({
                                'error': 'Missing required parameters: document_id and tenant_id'
                            })
                        }
                    }
                }
            }
        }
    
    try:
        # Validate document
        validation_result = validate_document(document_id, tenant_id)
        
        return {
            'response': {
                'actionGroup': event['actionGroup'],
                'function': event['function'],
                'functionResponse': {
                    'responseBody': {
                        'application/json': {
                            'body': json.dumps(validation_result)
                        }
                    }
                }
            }
        }
        
    except Exception as e:
        return {
            'response': {
                'actionGroup': event['actionGroup'],
                'function': event['function'],
                'functionResponse': {
                    'responseBody': {
                        'application/json': {
                            'body': json.dumps({
                                'error': str(e),
                                'valid': False
                            })
                        }
                    }
                }
            }
        }

def validate_document(document_id: str, tenant_id: str) -> Dict[str, Any]:
    """Validate document and return structured result"""
    
    # Get document from S3
    s3 = boto3.client('s3')
    dynamodb = boto3.resource('dynamodb')
    
    # Get document metadata
    table = dynamodb.Table('document-metadata')  # Use actual table name
    response = table.get_item(
        Key={'document_id': document_id, 'version': 1}
    )
    
    if 'Item' not in response:
        return {
            'valid': False,
            'error': 'Document not found',
            'confidence': 0.0
        }
    
    metadata = response['Item']
    
    # Verify tenant access
    if metadata.get('tenant_id') != tenant_id:
        return {
            'valid': False,
            'error': 'Access denied',
            'confidence': 0.0
        }
    
    # Get document from S3
    bucket = 'documents-bucket'  # Use actual bucket name
    s3_key = metadata.get('s3_key')
    
    try:
        obj = s3.get_object(Bucket=bucket, Key=s3_key)
        content = obj['Body'].read(1024)  # Read first 1KB
        
        # Perform validation
        if content.startswith(b'%PDF'):
            return {
                'valid': True,
                'document_type': 'pdf',
                'confidence': 0.95,
                'size_bytes': len(content)
            }
        elif content.startswith(b'PK'):
            return {
                'valid': True,
                'document_type': 'office_document',
                'confidence': 0.90,
                'size_bytes': len(content)
            }
        else:
            return {
                'valid': False,
                'error': 'Unsupported document type',
                'confidence': 0.0
            }
            
    except Exception as e:
        return {
            'valid': False,
            'error': f'Failed to access document: {str(e)}',
            'confidence': 0.0
        }
