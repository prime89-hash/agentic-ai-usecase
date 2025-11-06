"""
Bedrock Agent Supervisor - Main orchestrator using Bedrock Agents
"""
import json
import boto3
import os
from typing import Dict, Any
from common.utils import create_response, extract_tenant_id, generate_id, get_current_timestamp, update_usage_tracking

def lambda_handler(event, context):
    """Handle processing requests using Bedrock Agents"""
    try:
        # Extract tenant ID and parse request
        tenant_id = extract_tenant_id(event)
        body = json.loads(event.get('body', '{}'))
        prompt = body.get('prompt', '')
        file_ids = body.get('file_ids', [])
        
        if not prompt or not file_ids:
            return create_response(400, {'error': 'Missing prompt or file_ids'})
        
        # Generate request ID for tracking
        request_id = generate_id()
        
        # Store initial processing status
        store_processing_status(request_id, tenant_id, prompt, file_ids, 'processing')
        
        # Invoke Bedrock Agent
        result = invoke_bedrock_agent(prompt, file_ids, tenant_id, context.aws_request_id)
        
        # Update processing status with result
        store_processing_status(request_id, tenant_id, prompt, file_ids, 'completed', result)
        
        # Update usage tracking
        update_usage_tracking(tenant_id, 'bedrock_agent_requests', 0.15)
        
        return create_response(200, {
            'request_id': request_id,
            'result': result,
            'processing_time': 'real-time',
            'agent_used': True
        })
        
    except Exception as e:
        # Update status to failed if request_id exists
        if 'request_id' in locals():
            store_processing_status(request_id, tenant_id, prompt, file_ids, 'failed', {'error': str(e)})
        
        return create_response(500, {'error': str(e)})

def invoke_bedrock_agent(prompt: str, file_ids: list, tenant_id: str, session_id: str) -> Dict[str, Any]:
    """Invoke Bedrock Agent with the user request"""
    
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
    
    Always include confidence scores and cite your data sources.
    """
    
    try:
        # Invoke the Bedrock Agent
        response = bedrock_agent.invoke_agent(
            agentId=os.environ['BEDROCK_AGENT_ID'],
            agentAliasId=os.environ['BEDROCK_AGENT_ALIAS_ID'],
            sessionId=f"session-{tenant_id}-{session_id}",
            inputText=enhanced_prompt
        )
        
        # Process the agent's response
        completion = ""
        for event in response.get('completion', []):
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    completion += chunk['bytes'].decode('utf-8')
        
        # Try to parse as JSON if possible, otherwise return as text
        try:
            structured_result = json.loads(completion)
        except json.JSONDecodeError:
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

def store_processing_status(request_id: str, tenant_id: str, prompt: str, file_ids: list, 
                          status: str, result: Dict[str, Any] = None):
    """Store processing status in DynamoDB"""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['STATUS_TABLE'])
        
        item = {
            'request_id': request_id,
            'tenant_id': tenant_id,
            'status': status,
            'prompt': prompt,
            'file_ids': file_ids,
            'created_at': get_current_timestamp(),
            'ttl': int(get_current_timestamp().timestamp()) + 86400  # 24 hours
        }
        
        if status == 'completed' and result:
            item['result'] = result
            item['completed_at'] = get_current_timestamp()
        elif status == 'failed' and result:
            item['error'] = result.get('error', 'Unknown error')
        
        table.put_item(Item=item)
        
    except Exception as e:
        print(f"Failed to store processing status: {str(e)}")
