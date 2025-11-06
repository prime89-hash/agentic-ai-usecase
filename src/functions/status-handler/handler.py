"""
Status Handler - Retrieves processing status for requests
"""
import json
import os
from common.utils import AWSClients, create_response, extract_tenant_id

def lambda_handler(event, context):
    """Handle status check requests"""
    try:
        # Extract tenant ID
        tenant_id = extract_tenant_id(event)
        
        # Get request ID from path parameters
        path_params = event.get('pathParameters', {})
        request_id = path_params.get('id')
        
        if not request_id:
            return create_response(400, {'error': 'Request ID is required'})
        
        # Fetch status from DynamoDB
        clients = AWSClients()
        status_table = clients.dynamodb.Table(os.environ['STATUS_TABLE'])
        
        response = status_table.get_item(
            Key={'request_id': request_id}
        )
        
        if 'Item' not in response:
            return create_response(404, {'error': 'Request not found'})
        
        status_item = response['Item']
        
        # Verify tenant access
        if status_item.get('tenant_id') != tenant_id:
            return create_response(403, {'error': 'Access denied'})
        
        # Format response
        status_response = {
            'request_id': request_id,
            'status': status_item.get('status'),
            'created_at': status_item.get('created_at'),
            'completed_at': status_item.get('completed_at'),
            'prompt': status_item.get('prompt'),
            'file_ids': status_item.get('file_ids', [])
        }
        
        # Include result if completed
        if status_item.get('status') == 'completed' and 'result' in status_item:
            status_response['result'] = status_item['result']
        
        # Include error if failed
        if status_item.get('status') == 'failed' and 'error' in status_item:
            status_response['error'] = status_item['error']
        
        return create_response(200, status_response)
        
    except Exception as e:
        return create_response(500, {'error': str(e)})
