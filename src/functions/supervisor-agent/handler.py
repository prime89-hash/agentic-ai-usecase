"""
Supervisor Agent - Routes requests to appropriate specialized agents
"""
import json
import os
from common.utils import (
    AWSClients, create_response, extract_tenant_id, validate_request_body,
    generate_id, get_current_timestamp, invoke_bedrock_model, update_usage_tracking
)

def lambda_handler(event, context):
    """Handle processing requests and route to appropriate agents"""
    try:
        # Extract tenant ID
        tenant_id = extract_tenant_id(event)
        
        # Validate request body
        body = validate_request_body(event, ['prompt', 'file_ids'])
        prompt = body['prompt']
        file_ids = body['file_ids']
        
        if not isinstance(file_ids, list) or not file_ids:
            return create_response(400, {'error': 'file_ids must be a non-empty list'})
        
        # Generate request ID for tracking
        request_id = generate_id()
        
        # Store processing status
        clients = AWSClients()
        status_table = clients.dynamodb.Table(os.environ['STATUS_TABLE'])
        status_table.put_item(
            Item={
                'request_id': request_id,
                'tenant_id': tenant_id,
                'status': 'analyzing',
                'prompt': prompt,
                'file_ids': file_ids,
                'created_at': get_current_timestamp(),
                'ttl': int(get_current_timestamp().timestamp()) + 86400  # 24 hours
            }
        )
        
        # Analyze prompt intent using Bedrock
        intent_prompt = f"""
        Analyze this user request and classify it as either "compliance" or "query":
        
        Request: {prompt}
        
        Classification rules:
        - "compliance": If the request involves calculations, ratios, financial metrics, compliance checks, or mathematical operations
        - "query": If the request involves questions about document content, data extraction, or information retrieval
        
        Respond with only one word: either "compliance" or "query"
        """
        
        intent = invoke_bedrock_model(intent_prompt, max_tokens=10).strip().lower()
        
        # Route to appropriate agent
        if intent == 'compliance':
            result = invoke_compliance_agent(request_id, tenant_id, prompt, file_ids)
        elif intent == 'query':
            result = invoke_qa_agent(request_id, tenant_id, prompt, file_ids)
        else:
            # Default to query if intent is unclear
            result = invoke_qa_agent(request_id, tenant_id, prompt, file_ids)
        
        # Update processing status
        status_table.update_item(
            Key={'request_id': request_id},
            UpdateExpression='SET #status = :status, #result = :result, #completed_at = :completed_at',
            ExpressionAttributeNames={
                '#status': 'status',
                '#result': 'result',
                '#completed_at': 'completed_at'
            },
            ExpressionAttributeValues={
                ':status': 'completed',
                ':result': result,
                ':completed_at': get_current_timestamp()
            }
        )
        
        # Update usage tracking
        update_usage_tracking(tenant_id, 'processing_requests')
        
        return create_response(200, {
            'request_id': request_id,
            'intent': intent,
            'result': result
        })
        
    except Exception as e:
        # Update status to failed if request_id exists
        if 'request_id' in locals():
            try:
                status_table.update_item(
                    Key={'request_id': request_id},
                    UpdateExpression='SET #status = :status, #error = :error',
                    ExpressionAttributeNames={
                        '#status': 'status',
                        '#error': 'error'
                    },
                    ExpressionAttributeValues={
                        ':status': 'failed',
                        ':error': str(e)
                    }
                )
            except:
                pass
        
        return create_response(500, {'error': str(e)})

def invoke_compliance_agent(request_id: str, tenant_id: str, prompt: str, file_ids: list) -> dict:
    """Invoke compliance check agent"""
    clients = AWSClients()
    
    payload = {
        'request_id': request_id,
        'tenant_id': tenant_id,
        'prompt': prompt,
        'file_ids': file_ids
    }
    
    response = clients.lambda_client.invoke(
        FunctionName=os.environ['COMPLIANCE_FUNCTION'],
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    return result

def invoke_qa_agent(request_id: str, tenant_id: str, prompt: str, file_ids: list) -> dict:
    """Invoke Q&A agent"""
    clients = AWSClients()
    
    payload = {
        'request_id': request_id,
        'tenant_id': tenant_id,
        'prompt': prompt,
        'file_ids': file_ids
    }
    
    response = clients.lambda_client.invoke(
        FunctionName=os.environ['QA_FUNCTION'],
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    return result
