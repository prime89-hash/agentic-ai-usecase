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
        # Parse Bedrock Agent event
        action_group = event.get('actionGroup', '')
        function = event.get('function', '')
        
        # Get request body
        request_body = event.get('requestBody', {}).get('content', {}).get('application/json', {})
        if isinstance(request_body, str):
            request_body = json.loads(request_body)
        
        # Route to appropriate function
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
        
        # Return Bedrock Agent response format
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
    """Validate document accessibility and format"""
    
    document_id = request_body.get('document_id')
    tenant_id = request_body.get('tenant_id')
    
    if not document_id or not tenant_id:
        return {'error': 'Missing document_id or tenant_id'}
    
    try:
        # Get document metadata
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['METADATA_TABLE'])
        
        response = table.get_item(
            Key={'document_id': document_id, 'version': 1}
        )
        
        if 'Item' not in response:
            return {'valid': False, 'error': 'Document not found'}
        
        metadata = response['Item']
        
        # Verify tenant access
        if metadata.get('tenant_id') != tenant_id:
            return {'valid': False, 'error': 'Access denied'}
        
        # Check document status
        status = metadata.get('status', 'unknown')
        
        return {
            'valid': True,
            'document_type': metadata.get('document_type', 'unknown'),
            'status': status,
            'filename': metadata.get('filename'),
            'confidence': 0.95 if status == 'extracted' else 0.8
        }
        
    except Exception as e:
        return {'valid': False, 'error': str(e)}

def extract_data(request_body: Dict[str, Any]) -> Dict[str, Any]:
    """Extract or retrieve structured data from document"""
    
    document_id = request_body.get('document_id')
    tenant_id = request_body.get('tenant_id')
    
    if not document_id or not tenant_id:
        return {'error': 'Missing document_id or tenant_id'}
    
    try:
        # Check if data already extracted
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['METADATA_TABLE'])
        
        response = table.get_item(
            Key={'document_id': document_id, 'version': 1}
        )
        
        if 'Item' not in response:
            return {'error': 'Document not found'}
        
        metadata = response['Item']
        
        # Verify tenant access
        if metadata.get('tenant_id') != tenant_id:
            return {'error': 'Access denied'}
        
        # Get formatted data if available
        formatted_s3_key = metadata.get('formatted_s3_key')
        if formatted_s3_key:
            s3 = boto3.client('s3')
            obj = s3.get_object(Bucket=os.environ['PROCESSED_BUCKET'], Key=formatted_s3_key)
            formatted_data = json.loads(obj['Body'].read())
            
            return {
                'success': True,
                'financial_metrics': formatted_data.get('key_financial_metrics', {}),
                'entities': formatted_data.get('entities', {}),
                'compliance_data': formatted_data.get('compliance_relevant_data', {}),
                'document_summary': formatted_data.get('document_summary', ''),
                'extraction_metadata': formatted_data.get('extraction_metadata', {})
            }
        
        # If not extracted yet, trigger extraction
        if metadata.get('status') == 'validated':
            trigger_extraction(document_id, tenant_id, metadata)
            return {
                'success': False,
                'message': 'Extraction triggered, please try again in a few moments',
                'status': 'processing'
            }
        
        return {'error': 'Document not ready for extraction'}
        
    except Exception as e:
        return {'error': str(e)}

def calculate_compliance(request_body: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate financial ratios and compliance metrics"""
    
    formula = request_body.get('formula', '')
    parameters = request_body.get('parameters', {})
    threshold = request_body.get('threshold')
    
    if not formula or not parameters:
        return {'error': 'Missing formula or parameters'}
    
    try:
        # Safely evaluate formula
        safe_formula = formula
        for param, value in parameters.items():
            if isinstance(value, (int, float)):
                safe_formula = safe_formula.replace(param, str(value))
        
        # Basic safety check
        import re
        if not re.match(r'^[\d\.\+\-\*/\(\)\s]+$', safe_formula):
            return {'error': 'Invalid formula contains non-mathematical characters'}
        
        # Calculate result
        result = eval(safe_formula)
        
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

def get_document_data(request_body: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve processed data for multiple documents"""
    
    document_ids = request_body.get('document_ids', [])
    tenant_id = request_body.get('tenant_id')
    
    if not document_ids or not tenant_id:
        return {'error': 'Missing document_ids or tenant_id'}
    
    try:
        documents_data = []
        
        for doc_id in document_ids:
            # Get document data
            extract_result = extract_data({'document_id': doc_id, 'tenant_id': tenant_id})
            
            if extract_result.get('success'):
                documents_data.append({
                    'document_id': doc_id,
                    'data': extract_result
                })
        
        return {
            'success': True,
            'documents': documents_data,
            'count': len(documents_data)
        }
        
    except Exception as e:
        return {'error': str(e)}

def trigger_extraction(document_id: str, tenant_id: str, metadata: Dict[str, Any]):
    """Trigger document extraction process"""
    
    try:
        # Invoke extractor Lambda
        lambda_client = boto3.client('lambda')
        
        payload = {
            'bucket': os.environ['DOCUMENTS_BUCKET'],
            'key': metadata.get('s3_key'),
            'document_id': document_id,
            'tenant_id': tenant_id
        }
        
        lambda_client.invoke(
            FunctionName=os.environ['EXTRACTOR_FUNCTION'],
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
        
    except Exception as e:
        print(f"Failed to trigger extraction: {str(e)}")
