#!/usr/bin/env python3
"""
API Testing Script for Agentic AI Financial Document Processing
"""
import requests
import json
import time
import os
import sys
from typing import Dict, Any

class FinancialDocProcessingTester:
    def __init__(self, api_endpoint: str, tenant_id: str = "test-tenant"):
        self.api_endpoint = api_endpoint.rstrip('/')
        self.tenant_id = tenant_id
        self.headers = {
            'Content-Type': 'application/json',
            'x-tenant-id': tenant_id
        }
    
    def test_upload_flow(self, test_file_path: str) -> str:
        """Test document upload flow"""
        print("🔄 Testing document upload flow...")
        
        # Step 1: Request upload URL
        filename = os.path.basename(test_file_path)
        upload_request = {
            'filename': filename
        }
        
        response = requests.post(
            f"{self.api_endpoint}/v1/upload",
            headers=self.headers,
            json=upload_request
        )
        
        if response.status_code != 200:
            raise Exception(f"Upload URL request failed: {response.text}")
        
        upload_data = response.json()
        upload_url = upload_data['upload_url']
        document_id = upload_data['document_id']
        
        print(f"✅ Got upload URL for document ID: {document_id}")
        
        # Step 2: Upload file
        if os.path.exists(test_file_path):
            with open(test_file_path, 'rb') as f:
                upload_response = requests.put(upload_url, data=f.read())
            
            if upload_response.status_code not in [200, 204]:
                raise Exception(f"File upload failed: {upload_response.text}")
            
            print(f"✅ File uploaded successfully")
        else:
            print(f"⚠️ Test file not found: {test_file_path}, skipping actual upload")
        
        return document_id
    
    def test_processing_request(self, document_ids: list, prompt: str) -> str:
        """Test document processing request"""
        print(f"🔄 Testing processing request: {prompt}")
        
        process_request = {
            'prompt': prompt,
            'file_ids': document_ids
        }
        
        response = requests.post(
            f"{self.api_endpoint}/v1/process",
            headers=self.headers,
            json=process_request
        )
        
        if response.status_code != 200:
            raise Exception(f"Processing request failed: {response.text}")
        
        result = response.json()
        request_id = result.get('request_id')
        
        print(f"✅ Processing request submitted: {request_id}")
        print(f"📊 Intent detected: {result.get('intent')}")
        
        if 'result' in result:
            print(f"📋 Result: {json.dumps(result['result'], indent=2)}")
        
        return request_id
    
    def test_status_check(self, request_id: str) -> Dict[str, Any]:
        """Test status checking"""
        print(f"🔄 Checking status for request: {request_id}")
        
        response = requests.get(
            f"{self.api_endpoint}/v1/status/{request_id}",
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Status check failed: {response.text}")
        
        status = response.json()
        print(f"📊 Status: {status.get('status')}")
        
        return status
    
    def run_comprehensive_test(self):
        """Run comprehensive API test suite"""
        print("🚀 Starting comprehensive API test suite...")
        print(f"🌐 API Endpoint: {self.api_endpoint}")
        print(f"👤 Tenant ID: {self.tenant_id}")
        print("-" * 50)
        
        try:
            # Test 1: Upload a sample document
            print("\n📤 Test 1: Document Upload")
            sample_file = "sample_financial_statement.pdf"
            document_id = self.test_upload_flow(sample_file)
            
            # Wait for processing
            print("⏳ Waiting for document processing...")
            time.sleep(10)
            
            # Test 2: Compliance check
            print("\n🔍 Test 2: Compliance Check")
            compliance_prompt = "Calculate the debt-to-equity ratio and check if it's below 2.0"
            compliance_request_id = self.test_processing_request([document_id], compliance_prompt)
            
            # Test 3: Q&A query
            print("\n❓ Test 3: Q&A Query")
            qa_prompt = "What is the total revenue mentioned in the document?"
            qa_request_id = self.test_processing_request([document_id], qa_prompt)
            
            # Test 4: Status checks
            print("\n📊 Test 4: Status Checks")
            compliance_status = self.test_status_check(compliance_request_id)
            qa_status = self.test_status_check(qa_request_id)
            
            print("\n🎉 All tests completed successfully!")
            print("\n📋 Test Summary:")
            print(f"- Document uploaded: {document_id}")
            print(f"- Compliance check: {compliance_status.get('status')}")
            print(f"- Q&A query: {qa_status.get('status')}")
            
        except Exception as e:
            print(f"\n❌ Test failed: {str(e)}")
            sys.exit(1)

def main():
    """Main test function"""
    if len(sys.argv) < 2:
        print("Usage: python test_api.py <API_ENDPOINT> [TENANT_ID]")
        print("Example: python test_api.py https://api123.execute-api.us-east-1.amazonaws.com/production")
        sys.exit(1)
    
    api_endpoint = sys.argv[1]
    tenant_id = sys.argv[2] if len(sys.argv) > 2 else "test-tenant"
    
    tester = FinancialDocProcessingTester(api_endpoint, tenant_id)
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()
