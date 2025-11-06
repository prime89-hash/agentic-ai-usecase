"""
Q&A Agent - Handles document content queries
"""
import json
import os
from typing import Dict, Any, List
from common.utils import (
    AWSClients, get_current_timestamp, invoke_bedrock_model, update_usage_tracking
)

def lambda_handler(event, context):
    """Handle Q&A requests about document content"""
    try:
        request_id = event['request_id']
        tenant_id = event['tenant_id']
        prompt = event['prompt']
        file_ids = event['file_ids']
        
        # Fetch document data
        document_data = fetch_document_data(file_ids, tenant_id)
        
        if not document_data:
            return {
                'error': 'No valid document data found for the provided file IDs',
                'answer': None
            }
        
        # Generate answer using Bedrock
        answer = generate_answer(prompt, document_data)
        
        # Update usage tracking
        update_usage_tracking(tenant_id, 'qa_queries', 0.05)  # $0.05 per query
        
        return {
            'answer': answer,
            'documents_analyzed': len(document_data),
            'request_id': request_id,
            'confidence': calculate_confidence_score(answer, document_data)
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'answer': None,
            'request_id': event.get('request_id')
        }

def fetch_document_data(file_ids: List[str], tenant_id: str) -> List[Dict[str, Any]]:
    """Fetch document data for Q&A processing"""
    clients = AWSClients()
    document_data = []
    
    for file_id in file_ids:
        try:
            # Get document metadata
            metadata_table = clients.dynamodb.Table(os.environ['METADATA_TABLE'])
            response = metadata_table.get_item(
                Key={'document_id': file_id, 'version': 1}
            )
            
            if 'Item' not in response:
                continue
                
            metadata = response['Item']
            
            # Verify tenant access
            if metadata.get('tenant_id') != tenant_id:
                continue
            
            # Get formatted data from S3
            formatted_s3_key = metadata.get('formatted_s3_key')
            if formatted_s3_key:
                processed_bucket = os.environ['PROCESSED_BUCKET']
                obj = clients.s3.get_object(Bucket=processed_bucket, Key=formatted_s3_key)
                formatted_data = json.loads(obj['Body'].read())
                
                document_data.append({
                    'document_id': file_id,
                    'filename': metadata.get('filename'),
                    'document_type': metadata.get('document_type'),
                    'data': formatted_data
                })
                
        except Exception as e:
            print(f"Failed to fetch data for document {file_id}: {str(e)}")
            continue
    
    return document_data

def generate_answer(prompt: str, document_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate answer to user question using document data"""
    
    # Prepare context from all documents
    context_parts = []
    
    for doc in document_data:
        doc_context = f"""
Document: {doc['filename']} (ID: {doc['document_id']})
Type: {doc['document_type']}

Summary: {doc['data'].get('document_summary', 'No summary available')}

Key Financial Metrics:
{json.dumps(doc['data'].get('key_financial_metrics', {}), indent=2)}

Entities:
{json.dumps(doc['data'].get('entities', {}), indent=2)}

Compliance Data:
{json.dumps(doc['data'].get('compliance_relevant_data', {}), indent=2)}
"""
        context_parts.append(doc_context)
    
    combined_context = "\n\n".join(context_parts)
    
    # Create comprehensive Q&A prompt
    qa_prompt = f"""
You are a financial document analysis AI assistant. Answer the user's question based on the provided document data.

User Question: {prompt}

Document Context:
{combined_context[:8000]}  # Limit context to avoid token limits

Instructions:
1. Provide a clear, accurate answer based on the document data
2. If the information is not available in the documents, clearly state this
3. Include specific references to document names when citing information
4. For numerical data, provide exact values when available
5. If the question requires calculations, show your work
6. Be concise but comprehensive

Format your response as JSON with these fields:
{{
    "answer": "Your detailed answer here",
    "sources": ["list of document filenames that provided the information"],
    "confidence": "high/medium/low based on data availability",
    "data_points": ["key data points used in the answer"],
    "limitations": "any limitations or missing information"
}}
"""
    
    try:
        response = invoke_bedrock_model(qa_prompt, max_tokens=2000)
        answer_data = json.loads(response)
        
        # Validate response format
        required_fields = ['answer', 'sources', 'confidence']
        if not all(field in answer_data for field in required_fields):
            raise ValueError("Invalid response format from LLM")
            
        return answer_data
        
    except (json.JSONDecodeError, ValueError) as e:
        # Fallback to simple text response
        simple_prompt = f"""
Based on the following financial document data, answer this question: {prompt}

Document Data:
{combined_context[:6000]}

Provide a clear, factual answer. If the information is not available, state this clearly.
"""
        
        simple_response = invoke_bedrock_model(simple_prompt, max_tokens=1000)
        
        return {
            'answer': simple_response,
            'sources': [doc['filename'] for doc in document_data],
            'confidence': 'medium',
            'data_points': ['Extracted from document analysis'],
            'limitations': 'Simplified response due to processing constraints'
        }

def calculate_confidence_score(answer_data: Dict[str, Any], document_data: List[Dict[str, Any]]) -> str:
    """Calculate confidence score based on answer quality and data availability"""
    
    if isinstance(answer_data, dict):
        # Use LLM-provided confidence if available
        llm_confidence = answer_data.get('confidence', 'medium').lower()
        
        # Adjust based on data quality
        total_docs = len(document_data)
        docs_with_data = sum(1 for doc in document_data 
                           if doc['data'].get('key_financial_metrics') or 
                              doc['data'].get('compliance_relevant_data'))
        
        data_ratio = docs_with_data / total_docs if total_docs > 0 else 0
        
        if data_ratio >= 0.8 and llm_confidence == 'high':
            return 'high'
        elif data_ratio >= 0.5 and llm_confidence in ['high', 'medium']:
            return 'medium'
        else:
            return 'low'
    
    return 'medium'  # Default confidence
