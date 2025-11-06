"""
Compliance Agent - Performs compliance calculations and validations
"""
import json
import os
import re
from typing import Dict, Any, List
from common.utils import (
    AWSClients, get_current_timestamp, invoke_bedrock_model, update_usage_tracking
)

def lambda_handler(event, context):
    """Handle compliance check requests"""
    try:
        request_id = event['request_id']
        tenant_id = event['tenant_id']
        prompt = event['prompt']
        file_ids = event['file_ids']
        
        # Fetch document data for all files
        document_data = fetch_document_data(file_ids, tenant_id)
        
        if not document_data:
            return {
                'error': 'No valid document data found for the provided file IDs',
                'compliance_result': None
            }
        
        # Build mathematical formula from prompt
        formula_result = build_formula_from_prompt(prompt)
        
        # Extract required parameters from documents
        parameters = extract_parameters_from_documents(formula_result['parameters'], document_data)
        
        # Perform compliance calculation
        calculation_result = perform_compliance_calculation(
            formula_result['formula'],
            parameters,
            formula_result.get('threshold')
        )
        
        # Generate compliance report
        compliance_report = generate_compliance_report(
            prompt, formula_result, parameters, calculation_result, document_data
        )
        
        # Update usage tracking
        update_usage_tracking(tenant_id, 'compliance_checks', 0.10)  # $0.10 per check
        
        return {
            'compliance_result': compliance_report,
            'calculation_details': calculation_result,
            'documents_analyzed': len(document_data),
            'request_id': request_id
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'compliance_result': None,
            'request_id': event.get('request_id')
        }

def fetch_document_data(file_ids: List[str], tenant_id: str) -> List[Dict[str, Any]]:
    """Fetch formatted document data from S3"""
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

def build_formula_from_prompt(prompt: str) -> Dict[str, Any]:
    """Use Bedrock to build mathematical formula from natural language prompt"""
    formula_prompt = f"""
    You are a financial compliance expert. Analyze this request and extract:
    1. The mathematical formula needed
    2. The parameters required
    3. Any compliance threshold mentioned
    
    Request: {prompt}
    
    Common financial ratios and formulas:
    - Debt-to-Equity Ratio: Total Debt / Total Equity
    - Current Ratio: Current Assets / Current Liabilities  
    - Quick Ratio: (Current Assets - Inventory) / Current Liabilities
    - Return on Assets: Net Income / Total Assets
    - Return on Equity: Net Income / Shareholders Equity
    - Gross Margin: (Revenue - COGS) / Revenue
    - Operating Margin: Operating Income / Revenue
    - Interest Coverage: EBIT / Interest Expense
    
    Respond in this exact JSON format:
    {{
        "formula": "mathematical expression using parameter names",
        "parameters": ["list", "of", "required", "parameters"],
        "threshold": "compliance threshold if mentioned",
        "description": "what this calculation measures"
    }}
    
    Example:
    {{
        "formula": "total_debt / total_equity",
        "parameters": ["total_debt", "total_equity"],
        "threshold": "< 2.0",
        "description": "Debt-to-Equity Ratio compliance check"
    }}
    """
    
    try:
        response = invoke_bedrock_model(formula_prompt, max_tokens=1000)
        formula_result = json.loads(response)
        
        # Validate required fields
        if not all(key in formula_result for key in ['formula', 'parameters']):
            raise ValueError("Invalid formula response format")
            
        return formula_result
        
    except (json.JSONDecodeError, ValueError) as e:
        # Fallback for common ratios if LLM fails
        return extract_common_ratio_fallback(prompt)

def extract_common_ratio_fallback(prompt: str) -> Dict[str, Any]:
    """Fallback method to extract common financial ratios"""
    prompt_lower = prompt.lower()
    
    if 'debt' in prompt_lower and 'equity' in prompt_lower:
        return {
            'formula': 'total_debt / total_equity',
            'parameters': ['total_debt', 'total_equity'],
            'threshold': extract_threshold_from_text(prompt),
            'description': 'Debt-to-Equity Ratio'
        }
    elif 'current ratio' in prompt_lower:
        return {
            'formula': 'current_assets / current_liabilities',
            'parameters': ['current_assets', 'current_liabilities'],
            'threshold': extract_threshold_from_text(prompt),
            'description': 'Current Ratio'
        }
    elif 'return on assets' in prompt_lower or 'roa' in prompt_lower:
        return {
            'formula': 'net_income / total_assets',
            'parameters': ['net_income', 'total_assets'],
            'threshold': extract_threshold_from_text(prompt),
            'description': 'Return on Assets'
        }
    else:
        return {
            'formula': 'unknown',
            'parameters': [],
            'threshold': None,
            'description': 'Unable to determine calculation'
        }

def extract_threshold_from_text(text: str) -> str:
    """Extract numerical thresholds from text"""
    # Look for patterns like "below 2.0", "less than 1.5", "> 0.15", etc.
    patterns = [
        r'below\s+(\d+\.?\d*)',
        r'less than\s+(\d+\.?\d*)',
        r'under\s+(\d+\.?\d*)',
        r'>\s*(\d+\.?\d*)',
        r'<\s*(\d+\.?\d*)',
        r'above\s+(\d+\.?\d*)',
        r'greater than\s+(\d+\.?\d*)',
        r'over\s+(\d+\.?\d*)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            value = match.group(1)
            if 'below' in pattern or 'less' in pattern or 'under' in pattern or '<' in pattern:
                return f"< {value}"
            else:
                return f"> {value}"
    
    return None

def extract_parameters_from_documents(required_params: List[str], document_data: List[Dict[str, Any]]) -> Dict[str, float]:
    """Extract required parameters from document data using Bedrock"""
    parameters = {}
    
    # Combine all document data for parameter extraction
    combined_data = {}
    for doc in document_data:
        doc_data = doc['data']
        combined_data[doc['document_id']] = {
            'filename': doc['filename'],
            'key_financial_metrics': doc_data.get('key_financial_metrics', {}),
            'compliance_relevant_data': doc_data.get('compliance_relevant_data', {}),
            'entities': doc_data.get('entities', {})
        }
    
    for param in required_params:
        param_value = extract_single_parameter(param, combined_data)
        if param_value is not None:
            parameters[param] = param_value
    
    return parameters

def extract_single_parameter(param_name: str, document_data: Dict[str, Any]) -> float:
    """Extract a single parameter value from document data"""
    extraction_prompt = f"""
    Find the value for "{param_name}" in this financial document data.
    
    Document Data:
    {json.dumps(document_data, indent=2)[:3000]}
    
    Look for variations of "{param_name}" such as:
    - Different formatting (spaces, underscores, capitalization)
    - Synonyms (e.g., "total debt" = "total liabilities", "net income" = "profit")
    - Related terms in financial statements
    
    Return only the numerical value as a float, or "null" if not found.
    Do not include currency symbols, commas, or other formatting.
    
    Examples:
    - "$1,234,567" should return: 1234567
    - "2.5%" should return: 0.025
    - "Not found" should return: null
    """
    
    try:
        response = invoke_bedrock_model(extraction_prompt, max_tokens=100)
        response = response.strip()
        
        if response.lower() in ['null', 'not found', 'n/a', 'none']:
            return None
        
        # Try to parse as float
        # Remove common formatting
        cleaned_value = re.sub(r'[,$%]', '', response)
        
        # Handle percentage conversion
        if '%' in response:
            return float(cleaned_value) / 100
        else:
            return float(cleaned_value)
            
    except (ValueError, json.JSONDecodeError):
        # Fallback: try to find parameter in the data directly
        return search_parameter_directly(param_name, document_data)

def search_parameter_directly(param_name: str, document_data: Dict[str, Any]) -> float:
    """Direct search for parameter in document data"""
    param_variations = [
        param_name,
        param_name.replace('_', ' '),
        param_name.replace('_', ''),
        param_name.title(),
        param_name.upper(),
        param_name.lower()
    ]
    
    for doc_id, doc_data in document_data.items():
        for section in ['key_financial_metrics', 'compliance_relevant_data', 'entities']:
            section_data = doc_data.get(section, {})
            
            for variation in param_variations:
                if variation in section_data:
                    try:
                        value = section_data[variation]
                        if isinstance(value, (int, float)):
                            return float(value)
                        elif isinstance(value, str):
                            # Try to extract number from string
                            numbers = re.findall(r'-?\d+\.?\d*', value.replace(',', ''))
                            if numbers:
                                return float(numbers[0])
                    except (ValueError, TypeError):
                        continue
    
    return None

def perform_compliance_calculation(formula: str, parameters: Dict[str, float], threshold: str = None) -> Dict[str, Any]:
    """Perform the compliance calculation"""
    try:
        # Check if all required parameters are available
        missing_params = []
        for param in re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', formula):
            if param not in parameters:
                missing_params.append(param)
        
        if missing_params:
            return {
                'success': False,
                'error': f'Missing parameters: {missing_params}',
                'result': None,
                'compliance_status': 'unknown'
            }
        
        # Safely evaluate the formula
        # Replace parameter names with values
        safe_formula = formula
        for param, value in parameters.items():
            safe_formula = safe_formula.replace(param, str(value))
        
        # Basic safety check - only allow mathematical operations
        if not re.match(r'^[\d\.\+\-\*/\(\)\s]+$', safe_formula):
            return {
                'success': False,
                'error': 'Invalid formula contains non-mathematical characters',
                'result': None,
                'compliance_status': 'error'
            }
        
        # Calculate result
        result = eval(safe_formula)
        
        # Check compliance if threshold is provided
        compliance_status = 'calculated'
        if threshold:
            compliance_status = check_compliance_threshold(result, threshold)
        
        return {
            'success': True,
            'result': result,
            'formula_used': formula,
            'parameters_used': parameters,
            'compliance_status': compliance_status,
            'threshold': threshold
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'result': None,
            'compliance_status': 'error'
        }

def check_compliance_threshold(result: float, threshold: str) -> str:
    """Check if result meets compliance threshold"""
    try:
        if threshold.startswith('<'):
            threshold_value = float(threshold[1:].strip())
            return 'compliant' if result < threshold_value else 'non_compliant'
        elif threshold.startswith('>'):
            threshold_value = float(threshold[1:].strip())
            return 'compliant' if result > threshold_value else 'non_compliant'
        elif threshold.startswith('<='):
            threshold_value = float(threshold[2:].strip())
            return 'compliant' if result <= threshold_value else 'non_compliant'
        elif threshold.startswith('>='):
            threshold_value = float(threshold[2:].strip())
            return 'compliant' if result >= threshold_value else 'non_compliant'
        else:
            return 'threshold_format_error'
    except (ValueError, IndexError):
        return 'threshold_parse_error'

def generate_compliance_report(prompt: str, formula_result: Dict[str, Any], parameters: Dict[str, float], 
                             calculation_result: Dict[str, Any], document_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate comprehensive compliance report"""
    return {
        'request_summary': {
            'original_prompt': prompt,
            'calculation_type': formula_result.get('description', 'Unknown'),
            'documents_analyzed': len(document_data),
            'timestamp': get_current_timestamp()
        },
        'calculation_details': {
            'formula': formula_result.get('formula'),
            'parameters_found': parameters,
            'result': calculation_result.get('result'),
            'success': calculation_result.get('success', False)
        },
        'compliance_assessment': {
            'status': calculation_result.get('compliance_status'),
            'threshold': calculation_result.get('threshold'),
            'meets_compliance': calculation_result.get('compliance_status') == 'compliant'
        },
        'document_sources': [
            {
                'document_id': doc['document_id'],
                'filename': doc['filename'],
                'document_type': doc['document_type']
            }
            for doc in document_data
        ],
        'recommendations': generate_recommendations(calculation_result, formula_result)
    }

def generate_recommendations(calculation_result: Dict[str, Any], formula_result: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on calculation results"""
    recommendations = []
    
    if not calculation_result.get('success'):
        recommendations.append("Review document data quality and ensure all required financial metrics are clearly labeled")
        recommendations.append("Consider manual verification of extracted values")
    
    compliance_status = calculation_result.get('compliance_status')
    if compliance_status == 'non_compliant':
        recommendations.append("The calculated ratio does not meet the specified compliance threshold")
        recommendations.append("Review financial position and consider corrective actions")
    elif compliance_status == 'compliant':
        recommendations.append("The calculated ratio meets the compliance requirements")
        recommendations.append("Continue monitoring this metric regularly")
    
    if calculation_result.get('result') is not None:
        result = calculation_result['result']
        description = formula_result.get('description', '')
        
        if 'debt' in description.lower() and 'equity' in description.lower():
            if result > 2.0:
                recommendations.append("High debt-to-equity ratio indicates higher financial risk")
            elif result < 0.5:
                recommendations.append("Low debt-to-equity ratio indicates conservative financial structure")
    
    return recommendations
