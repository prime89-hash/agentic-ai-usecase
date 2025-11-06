"""
Upload handler - Generates presigned URLs for document upload
"""
import json
import os
from common.utils import AWSClients, create_response, extract_tenant_id, generate_id, get_current_timestamp, update_usage_tracking

def lambda_handler(event, context):
    """Handle upload URL generation requests"""
    try:
        # Extract tenant ID
        tenant_id = extract_tenant_id(event)
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename')
        
        if not filename:
            return create_response(400, {'error': 'filename is required'})
        
        # Generate unique document ID
        document_id = generate_id()
        
        # Create S3 key with tenant isolation
        s3_key = f"uploads/{tenant_id}/{document_id}/{filename}"
        
        # Generate presigned URL
        clients = AWSClients()
        bucket_name = os.environ['DOCUMENTS_BUCKET']
        
        presigned_url = clients.s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
                'ContentType': 'application/octet-stream'
            },
            ExpiresIn=3600  # 1 hour
        )
        
        # Store initial metadata
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
        
        # Update usage tracking
        update_usage_tracking(tenant_id, 'upload_requests')
        
        return create_response(200, {
            'upload_url': presigned_url,
            'document_id': document_id,
            'expires_in': 3600
        })
        
    except Exception as e:
        return create_response(500, {'error': str(e)})
