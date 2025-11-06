"""
Validator Agent - Validates uploaded documents
"""
import json
import os
from common.utils import (
    AWSClients, extract_tenant_id, get_current_timestamp, 
    send_notification_email, update_usage_tracking
)

def lambda_handler(event, context):
    """Handle S3 upload events and validate documents"""
    try:
        # Parse S3 event
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            # Extract tenant_id and document_id from key
            # Format: uploads/{tenant_id}/{document_id}/{filename}
            key_parts = key.split('/')
            if len(key_parts) < 4 or key_parts[0] != 'uploads':
                continue
                
            tenant_id = key_parts[1]
            document_id = key_parts[2]
            filename = key_parts[3]
            
            # Validate document
            validation_result = validate_document(bucket, key)
            
            # Update document metadata
            clients = AWSClients()
            metadata_table = clients.dynamodb.Table(os.environ['METADATA_TABLE'])
            
            if validation_result['valid']:
                # Update status to validated
                metadata_table.update_item(
                    Key={'document_id': document_id, 'version': 1},
                    UpdateExpression='SET #status = :status, #doc_type = :doc_type, #validated_at = :validated_at',
                    ExpressionAttributeNames={
                        '#status': 'status',
                        '#doc_type': 'document_type',
                        '#validated_at': 'validated_at'
                    },
                    ExpressionAttributeValues={
                        ':status': 'validated',
                        ':doc_type': validation_result['document_type'],
                        ':validated_at': get_current_timestamp()
                    }
                )
                
                # Trigger extractor agent
                invoke_extractor_agent(bucket, key, document_id, tenant_id)
                
            else:
                # Update status to validation_failed
                metadata_table.update_item(
                    Key={'document_id': document_id, 'version': 1},
                    UpdateExpression='SET #status = :status, #error = :error',
                    ExpressionAttributeNames={
                        '#status': 'status',
                        '#error': 'validation_error'
                    },
                    ExpressionAttributeValues={
                        ':status': 'validation_failed',
                        ':error': validation_result['reason']
                    }
                )
                
                # Send notification email
                send_validation_notification(tenant_id, filename, validation_result['reason'])
            
            # Update usage tracking
            update_usage_tracking(tenant_id, 'documents_validated')
        
        return {'statusCode': 200}
        
    except Exception as e:
        print(f"Validation error: {str(e)}")
        return {'statusCode': 500, 'error': str(e)}

def validate_document(bucket: str, key: str) -> dict:
    """Validate document content and format"""
    try:
        clients = AWSClients()
        
        # Get object metadata
        response = clients.s3.head_object(Bucket=bucket, Key=key)
        content_length = response['ContentLength']
        content_type = response.get('ContentType', '')
        
        # Check file size (50MB limit)
        if content_length > 50 * 1024 * 1024:
            return {'valid': False, 'reason': 'File size exceeds 50MB limit'}
        
        # Check if file is empty
        if content_length == 0:
            return {'valid': False, 'reason': 'File is empty'}
        
        # Get file content for type detection
        obj = clients.s3.get_object(Bucket=bucket, Key=key)
        content = obj['Body'].read(1024)  # Read first 1KB for type detection
        
        # Detect document type
        document_type = detect_document_type(content, key)
        
        if document_type == 'unknown':
            return {'valid': False, 'reason': 'Unsupported file type'}
        
        return {
            'valid': True,
            'document_type': document_type,
            'size': content_length
        }
        
    except Exception as e:
        return {'valid': False, 'reason': f'Validation error: {str(e)}'}

def detect_document_type(content: bytes, filename: str) -> str:
    """Detect document type from content and filename"""
    # PDF detection
    if content.startswith(b'%PDF'):
        return 'pdf'
    
    # Office document detection (ZIP-based)
    if content.startswith(b'PK\x03\x04'):
        if filename.lower().endswith(('.xlsx', '.xls')):
            return 'spreadsheet'
        elif filename.lower().endswith(('.docx', '.doc')):
            return 'document'
        elif filename.lower().endswith(('.pptx', '.ppt')):
            return 'presentation'
        else:
            return 'office_document'
    
    # Image detection
    if content.startswith(b'\xff\xd8\xff'):  # JPEG
        return 'image'
    elif content.startswith(b'\x89PNG'):  # PNG
        return 'image'
    elif content.startswith(b'GIF8'):  # GIF
        return 'image'
    
    # Text files
    if filename.lower().endswith(('.txt', '.csv')):
        return 'text'
    
    return 'unknown'

def invoke_extractor_agent(bucket: str, key: str, document_id: str, tenant_id: str):
    """Invoke extractor agent for validated documents"""
    try:
        clients = AWSClients()
        
        payload = {
            'bucket': bucket,
            'key': key,
            'document_id': document_id,
            'tenant_id': tenant_id
        }
        
        clients.lambda_client.invoke(
            FunctionName=os.environ['EXTRACTOR_FUNCTION'],
            InvocationType='Event',  # Async invocation
            Payload=json.dumps(payload)
        )
        
    except Exception as e:
        print(f"Failed to invoke extractor agent: {str(e)}")

def send_validation_notification(tenant_id: str, filename: str, reason: str):
    """Send validation failure notification"""
    try:
        subject = f"Document Validation Failed: {filename}"
        body = f"""
        Document validation failed for tenant: {tenant_id}
        
        Filename: {filename}
        Reason: {reason}
        Timestamp: {get_current_timestamp()}
        
        Please check the document format and try uploading again.
        """
        
        # In production, get tenant email from tenant config table
        notification_email = os.environ.get('NOTIFICATION_EMAIL', 'admin@company.com')
        send_notification_email(notification_email, subject, body)
        
    except Exception as e:
        print(f"Failed to send notification: {str(e)}")
