"""
Extractor Agent - Extracts and formats document data using Textract and Bedrock
"""
import json
import os
from common.utils import (
    AWSClients, get_current_timestamp, invoke_bedrock_model, update_usage_tracking
)

def lambda_handler(event, context):
    """Handle document extraction requests"""
    try:
        # Parse event (from validator agent or direct invocation)
        bucket = event['bucket']
        key = event['key']
        document_id = event['document_id']
        tenant_id = event['tenant_id']
        
        # Extract text using Textract
        textract_result = extract_with_textract(bucket, key)
        
        # Format extracted data using Bedrock
        formatted_data = format_with_bedrock(textract_result, document_id)
        
        # Store results in DynamoDB and S3
        store_extracted_data(document_id, tenant_id, textract_result, formatted_data)
        
        # Update document status
        update_document_status(document_id, 'extracted')
        
        # Update usage tracking
        update_usage_tracking(tenant_id, 'documents_extracted', calculate_extraction_cost(textract_result))
        
        return {
            'statusCode': 200,
            'document_id': document_id,
            'extracted_fields': len(formatted_data.get('fields', {})),
            'pages_processed': len(textract_result.get('Blocks', []))
        }
        
    except Exception as e:
        # Update document status to failed
        if 'document_id' in locals():
            update_document_status(document_id, 'extraction_failed', str(e))
        
        return {
            'statusCode': 500,
            'error': str(e)
        }

def extract_with_textract(bucket: str, key: str) -> dict:
    """Extract text and structure using Amazon Textract"""
    clients = AWSClients()
    
    # Use Textract to analyze document
    response = clients.textract.analyze_document(
        Document={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        },
        FeatureTypes=['TABLES', 'FORMS', 'LAYOUT']
    )
    
    return response

def format_with_bedrock(textract_result: dict, document_id: str) -> dict:
    """Format extracted data using Bedrock LLM"""
    # Extract text content from Textract blocks
    extracted_text = extract_text_from_blocks(textract_result['Blocks'])
    
    # Extract key-value pairs from forms
    key_value_pairs = extract_key_value_pairs(textract_result['Blocks'])
    
    # Extract tables
    tables = extract_tables(textract_result['Blocks'])
    
    # Use Bedrock to structure and enhance the data
    formatting_prompt = f"""
    You are a financial document processing AI. Analyze this extracted document data and structure it into a standardized JSON format.
    
    Extracted Text:
    {extracted_text[:4000]}  # Limit text to avoid token limits
    
    Key-Value Pairs:
    {json.dumps(key_value_pairs, indent=2)}
    
    Tables Found: {len(tables)}
    
    Please structure this into a JSON format with the following sections:
    1. document_summary: Brief summary of the document type and purpose
    2. key_financial_metrics: Important financial numbers, ratios, and metrics
    3. entities: Companies, people, dates, addresses mentioned
    4. tables_summary: Summary of any tables found
    5. compliance_relevant_data: Data relevant for compliance calculations
    
    Focus on financial data extraction and ensure all numbers are properly formatted.
    Return only valid JSON.
    """
    
    try:
        formatted_json = invoke_bedrock_model(formatting_prompt, max_tokens=4000)
        # Try to parse as JSON to validate
        formatted_data = json.loads(formatted_json)
    except json.JSONDecodeError:
        # Fallback to basic structure if LLM doesn't return valid JSON
        formatted_data = {
            'document_summary': 'Financial document processed',
            'key_financial_metrics': {},
            'entities': {},
            'tables_summary': f'{len(tables)} tables found',
            'compliance_relevant_data': {},
            'raw_text': extracted_text[:2000],  # Store some raw text as fallback
            'processing_note': 'Automated extraction with basic formatting'
        }
    
    # Add metadata
    formatted_data['extraction_metadata'] = {
        'document_id': document_id,
        'extracted_at': get_current_timestamp(),
        'textract_blocks': len(textract_result['Blocks']),
        'key_value_pairs': len(key_value_pairs),
        'tables_found': len(tables)
    }
    
    return formatted_data

def extract_text_from_blocks(blocks: list) -> str:
    """Extract plain text from Textract blocks"""
    text_lines = []
    
    for block in blocks:
        if block['BlockType'] == 'LINE':
            text_lines.append(block['Text'])
    
    return '\n'.join(text_lines)

def extract_key_value_pairs(blocks: list) -> dict:
    """Extract key-value pairs from Textract form data"""
    key_value_pairs = {}
    
    # Create a map of block IDs to blocks
    block_map = {block['Id']: block for block in blocks}
    
    for block in blocks:
        if block['BlockType'] == 'KEY_VALUE_SET':
            if 'KEY' in block.get('EntityTypes', []):
                # This is a key block
                key_text = get_text_from_relationships(block, block_map)
                
                # Find the corresponding value
                if 'Relationships' in block:
                    for relationship in block['Relationships']:
                        if relationship['Type'] == 'VALUE':
                            for value_id in relationship['Ids']:
                                value_block = block_map.get(value_id)
                                if value_block:
                                    value_text = get_text_from_relationships(value_block, block_map)
                                    if key_text and value_text:
                                        key_value_pairs[key_text] = value_text
    
    return key_value_pairs

def extract_tables(blocks: list) -> list:
    """Extract table data from Textract blocks"""
    tables = []
    
    # Create a map of block IDs to blocks
    block_map = {block['Id']: block for block in blocks}
    
    for block in blocks:
        if block['BlockType'] == 'TABLE':
            table_data = []
            
            if 'Relationships' in block:
                for relationship in block['Relationships']:
                    if relationship['Type'] == 'CHILD':
                        for cell_id in relationship['Ids']:
                            cell_block = block_map.get(cell_id)
                            if cell_block and cell_block['BlockType'] == 'CELL':
                                cell_text = get_text_from_relationships(cell_block, block_map)
                                row_index = cell_block.get('RowIndex', 0)
                                col_index = cell_block.get('ColumnIndex', 0)
                                
                                # Ensure table_data has enough rows
                                while len(table_data) <= row_index:
                                    table_data.append([])
                                
                                # Ensure row has enough columns
                                while len(table_data[row_index]) <= col_index:
                                    table_data[row_index].append('')
                                
                                table_data[row_index][col_index] = cell_text or ''
            
            if table_data:
                tables.append(table_data)
    
    return tables

def get_text_from_relationships(block: dict, block_map: dict) -> str:
    """Get text content from block relationships"""
    text_parts = []
    
    if 'Relationships' in block:
        for relationship in block['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    child_block = block_map.get(child_id)
                    if child_block and child_block['BlockType'] == 'WORD':
                        text_parts.append(child_block['Text'])
    
    return ' '.join(text_parts)

def store_extracted_data(document_id: str, tenant_id: str, textract_result: dict, formatted_data: dict):
    """Store extraction results in DynamoDB and S3"""
    clients = AWSClients()
    
    # Store in S3 for detailed data
    processed_bucket = os.environ['PROCESSED_BUCKET']
    
    # Store raw Textract result
    textract_key = f"textract/{tenant_id}/{document_id}/raw_textract.json"
    clients.s3.put_object(
        Bucket=processed_bucket,
        Key=textract_key,
        Body=json.dumps(textract_result),
        ContentType='application/json'
    )
    
    # Store formatted data
    formatted_key = f"formatted/{tenant_id}/{document_id}/formatted_data.json"
    clients.s3.put_object(
        Bucket=processed_bucket,
        Key=formatted_key,
        Body=json.dumps(formatted_data, indent=2),
        ContentType='application/json'
    )
    
    # Update DynamoDB with extraction summary
    metadata_table = clients.dynamodb.Table(os.environ['METADATA_TABLE'])
    metadata_table.update_item(
        Key={'document_id': document_id, 'version': 1},
        UpdateExpression='SET #textract_s3_key = :textract_key, #formatted_s3_key = :formatted_key, #extracted_at = :extracted_at, #extraction_summary = :summary',
        ExpressionAttributeNames={
            '#textract_s3_key': 'textract_s3_key',
            '#formatted_s3_key': 'formatted_s3_key',
            '#extracted_at': 'extracted_at',
            '#extraction_summary': 'extraction_summary'
        },
        ExpressionAttributeValues={
            ':textract_key': textract_key,
            ':formatted_key': formatted_key,
            ':extracted_at': get_current_timestamp(),
            ':summary': {
                'blocks_processed': len(textract_result['Blocks']),
                'key_fields_found': len(formatted_data.get('key_financial_metrics', {})),
                'tables_found': len(formatted_data.get('extraction_metadata', {}).get('tables_found', 0))
            }
        }
    )

def update_document_status(document_id: str, status: str, error: str = None):
    """Update document processing status"""
    try:
        clients = AWSClients()
        metadata_table = clients.dynamodb.Table(os.environ['METADATA_TABLE'])
        
        update_expression = 'SET #status = :status, #updated_at = :updated_at'
        expression_values = {
            ':status': status,
            ':updated_at': get_current_timestamp()
        }
        expression_names = {
            '#status': 'status',
            '#updated_at': 'updated_at'
        }
        
        if error:
            update_expression += ', #error = :error'
            expression_values[':error'] = error
            expression_names['#error'] = 'error'
        
        metadata_table.update_item(
            Key={'document_id': document_id, 'version': 1},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values
        )
    except Exception as e:
        print(f"Failed to update document status: {str(e)}")

def calculate_extraction_cost(textract_result: dict) -> float:
    """Calculate estimated cost for Textract processing"""
    # Rough cost estimation based on pages processed
    # Actual costs would depend on specific Textract pricing
    pages = len([block for block in textract_result['Blocks'] if block['BlockType'] == 'PAGE'])
    return pages * 0.05  # Estimated $0.05 per page
