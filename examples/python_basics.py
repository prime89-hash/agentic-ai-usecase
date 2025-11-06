"""
Python Basics for Agentic AI Project
Simple examples to understand the concepts used in our project
"""

# ============================================================================
# 1. BASIC PYTHON CONCEPTS
# ============================================================================

print("=== Python Basics for AI Document Processing ===\n")

# Variables - storing data
document_name = "financial_report.pdf"
document_size = 1024
is_processed = False

print(f"Document: {document_name}")
print(f"Size: {document_size} bytes")
print(f"Processed: {is_processed}\n")

# ============================================================================
# 2. DICTIONARIES - Key-Value pairs (like JSON)
# ============================================================================

print("=== Working with Document Data ===")

# This is how we store document information
document_info = {
    "document_id": "doc_12345",
    "filename": "balance_sheet.pdf",
    "tenant_id": "company_abc",
    "status": "uploaded",
    "size_bytes": 2048,
    "document_type": "financial_statement"
}

# Access data
print(f"Document ID: {document_info['document_id']}")
print(f"Status: {document_info['status']}")
print(f"Type: {document_info['document_type']}\n")

# ============================================================================
# 3. LISTS - Multiple items
# ============================================================================

print("=== Working with Multiple Documents ===")

# List of document IDs
document_ids = ["doc_001", "doc_002", "doc_003"]
document_types = ["pdf", "excel", "word"]

print("Document IDs:")
for doc_id in document_ids:
    print(f"  - {doc_id}")

print(f"\nFirst document: {document_ids[0]}")
print(f"Total documents: {len(document_ids)}\n")

# ============================================================================
# 4. FUNCTIONS - Reusable code blocks
# ============================================================================

print("=== Functions for Document Processing ===")

def validate_document(filename):
    """Check if document is valid"""
    if not filename:
        return False, "No filename provided"
    
    if filename.endswith('.pdf'):
        return True, "PDF document is valid"
    elif filename.endswith('.xlsx'):
        return True, "Excel document is valid"
    else:
        return False, "Unsupported file type"

# Test the function
test_files = ["report.pdf", "data.xlsx", "image.jpg"]

for file in test_files:
    is_valid, message = validate_document(file)
    print(f"{file}: {message}")

print()

# ============================================================================
# 5. ERROR HANDLING - try/except
# ============================================================================

print("=== Error Handling ===")

def safe_divide(a, b):
    """Safely divide two numbers"""
    try:
        result = a / b
        return {"success": True, "result": result}
    except ZeroDivisionError:
        return {"success": False, "error": "Cannot divide by zero"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Test error handling
test_cases = [(10, 2), (10, 0), (10, "invalid")]

for a, b in test_cases:
    result = safe_divide(a, b)
    if result["success"]:
        print(f"{a} ÷ {b} = {result['result']}")
    else:
        print(f"{a} ÷ {b} failed: {result['error']}")

print()

# ============================================================================
# 6. JSON - Data format for APIs
# ============================================================================

print("=== Working with JSON (API Data) ===")

import json

# This is how API requests look
api_request = {
    "prompt": "Calculate debt-to-equity ratio",
    "file_ids": ["doc_001", "doc_002"],
    "tenant_id": "company_abc"
}

# Convert to JSON string (for sending over internet)
json_string = json.dumps(api_request, indent=2)
print("API Request as JSON:")
print(json_string)

# Convert back to Python dictionary (when receiving)
received_data = json.loads(json_string)
print(f"\nPrompt from API: {received_data['prompt']}")
print(f"Files to process: {received_data['file_ids']}\n")

# ============================================================================
# 7. LAMBDA FUNCTION STRUCTURE
# ============================================================================

print("=== Lambda Function Example ===")

def lambda_handler(event, context):
    """
    This is the main function that AWS Lambda calls
    - event: contains the request data
    - context: contains runtime information
    """
    try:
        # Extract data from the request
        body = json.loads(event.get('body', '{}'))
        action = body.get('action', 'unknown')
        
        # Process based on action
        if action == 'upload':
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Upload URL generated',
                    'upload_url': 'https://s3.amazonaws.com/bucket/upload-url'
                })
            }
        elif action == 'process':
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Document processed',
                    'result': 'Debt-to-equity ratio: 1.5'
                })
            }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Unknown action: {action}'
                })
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

# Test the lambda function
test_event = {
    'body': json.dumps({
        'action': 'upload',
        'filename': 'test.pdf'
    })
}

result = lambda_handler(test_event, None)
print(f"Lambda Response: {result}")
print()

# ============================================================================
# 8. BEDROCK AGENT TOOL FUNCTION
# ============================================================================

print("=== Bedrock Agent Tool Example ===")

def bedrock_tool_handler(event, context):
    """
    This handles requests from Bedrock Agent
    The AI agent calls this when it needs to perform actions
    """
    try:
        # Bedrock Agent sends data in a specific format
        function_name = event.get('function', '')
        request_body = event.get('requestBody', {}).get('content', {}).get('application/json', {})
        
        if isinstance(request_body, str):
            request_body = json.loads(request_body)
        
        # Route to the right function
        if function_name == 'validate_document':
            result = validate_document_for_agent(request_body)
        elif function_name == 'calculate_ratio':
            result = calculate_financial_ratio(request_body)
        else:
            result = {'error': f'Unknown function: {function_name}'}
        
        # Return in Bedrock Agent format
        return {
            'response': {
                'actionGroup': event.get('actionGroup', ''),
                'function': function_name,
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

def validate_document_for_agent(request_body):
    """Validate document for Bedrock Agent"""
    document_id = request_body.get('document_id')
    
    if not document_id:
        return {'valid': False, 'error': 'No document ID provided'}
    
    # Simulate document validation
    return {
        'valid': True,
        'document_type': 'financial_statement',
        'confidence': 0.95,
        'status': 'ready_for_processing'
    }

def calculate_financial_ratio(request_body):
    """Calculate financial ratios for Bedrock Agent"""
    formula = request_body.get('formula', '')
    parameters = request_body.get('parameters', {})
    
    if formula == 'debt_to_equity':
        total_debt = parameters.get('total_debt', 0)
        total_equity = parameters.get('total_equity', 1)
        
        if total_equity == 0:
            return {'error': 'Cannot calculate ratio: equity is zero'}
        
        ratio = total_debt / total_equity
        return {
            'success': True,
            'result': ratio,
            'interpretation': 'Good' if ratio < 2.0 else 'High risk'
        }
    
    return {'error': f'Unknown formula: {formula}'}

# Test Bedrock Agent tool
test_bedrock_event = {
    'actionGroup': 'financial_calculations',
    'function': 'calculate_ratio',
    'requestBody': {
        'content': {
            'application/json': json.dumps({
                'formula': 'debt_to_equity',
                'parameters': {
                    'total_debt': 100000,
                    'total_equity': 200000
                }
            })
        }
    }
}

bedrock_result = bedrock_tool_handler(test_bedrock_event, None)
print("Bedrock Agent Tool Response:")
print(json.dumps(bedrock_result, indent=2))

print("\n=== End of Python Basics ===")
print("Now you understand the core concepts used in our AI document processing system!")
