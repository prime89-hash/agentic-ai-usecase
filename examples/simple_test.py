#!/usr/bin/env python3
"""
Simple Test Script for Beginners
Test your deployed AI document processing system step by step
"""

import requests
import json
import time
import sys

class SimpleAPITester:
    def __init__(self, api_endpoint):
        """Initialize the tester with your API endpoint"""
        self.api_endpoint = api_endpoint.rstrip('/')
        self.tenant_id = "beginner-test"
        self.headers = {
            'Content-Type': 'application/json',
            'x-tenant-id': self.tenant_id
        }
        print(f"🚀 Testing API at: {self.api_endpoint}")
        print(f"👤 Using tenant ID: {self.tenant_id}")
        print("-" * 50)
    
    def test_1_basic_connection(self):
        """Test 1: Check if API is responding"""
        print("\n📡 Test 1: Basic API Connection")
        
        try:
            # Try to connect to the API
            response = requests.get(f"{self.api_endpoint}/v1/health", timeout=10)
            
            if response.status_code == 200:
                print("✅ API is responding!")
                return True
            else:
                print(f"⚠️ API responded with status: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to API: {e}")
            print("💡 Make sure your API endpoint is correct and deployment completed successfully")
            return False
    
    def test_2_upload_request(self):
        """Test 2: Request an upload URL"""
        print("\n📤 Test 2: Request Upload URL")
        
        try:
            # Request upload URL for a test file
            upload_request = {
                'filename': 'test-financial-report.pdf'
            }
            
            response = requests.post(
                f"{self.api_endpoint}/v1/upload",
                headers=self.headers,
                json=upload_request,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Upload URL generated successfully!")
                print(f"📄 Document ID: {data.get('document_id', 'N/A')}")
                print(f"⏰ Expires in: {data.get('expires_in', 'N/A')} seconds")
                
                # Save document ID for next test
                self.document_id = data.get('document_id')
                return True
            else:
                print(f"❌ Upload request failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Upload request error: {e}")
            return False
    
    def test_3_simple_processing(self):
        """Test 3: Simple document processing request"""
        print("\n🤖 Test 3: AI Processing Request")
        
        if not hasattr(self, 'document_id'):
            print("⚠️ Skipping - no document ID from previous test")
            return False
        
        try:
            # Send a simple processing request
            process_request = {
                'prompt': 'Hello AI! Can you tell me about document processing?',
                'file_ids': [self.document_id]
            }
            
            print(f"📝 Sending prompt: {process_request['prompt']}")
            print(f"📄 For document: {self.document_id}")
            
            response = requests.post(
                f"{self.api_endpoint}/v1/process",
                headers=self.headers,
                json=process_request,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ AI processing completed!")
                print(f"🆔 Request ID: {data.get('request_id', 'N/A')}")
                
                # Show AI response
                result = data.get('result', {})
                if isinstance(result, dict):
                    ai_response = result.get('response', 'No response')
                    print(f"🤖 AI Response: {ai_response}")
                else:
                    print(f"🤖 AI Response: {result}")
                
                return True
            else:
                print(f"❌ Processing failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Processing error: {e}")
            return False
    
    def test_4_financial_calculation(self):
        """Test 4: Financial calculation request"""
        print("\n💰 Test 4: Financial Calculation")
        
        if not hasattr(self, 'document_id'):
            print("⚠️ Skipping - no document ID from previous test")
            return False
        
        try:
            # Request a financial calculation
            calc_request = {
                'prompt': 'Calculate a simple debt-to-equity ratio using these example values: total debt = $100,000, total equity = $200,000',
                'file_ids': [self.document_id]
            }
            
            print(f"📊 Requesting calculation: debt-to-equity ratio")
            
            response = requests.post(
                f"{self.api_endpoint}/v1/process",
                headers=self.headers,
                json=calc_request,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Financial calculation completed!")
                
                result = data.get('result', {})
                if isinstance(result, dict):
                    ai_response = result.get('response', 'No response')
                    print(f"📈 Calculation Result: {ai_response}")
                else:
                    print(f"📈 Calculation Result: {result}")
                
                return True
            else:
                print(f"❌ Calculation failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Calculation error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🧪 Starting Simple API Tests")
        print("=" * 50)
        
        tests = [
            self.test_1_basic_connection,
            self.test_2_upload_request,
            self.test_3_simple_processing,
            self.test_4_financial_calculation
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
                time.sleep(2)  # Wait between tests
            except Exception as e:
                print(f"❌ Test failed with error: {e}")
                results.append(False)
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        
        test_names = [
            "Basic Connection",
            "Upload URL Request", 
            "AI Processing",
            "Financial Calculation"
        ]
        
        passed = 0
        for i, (name, result) in enumerate(zip(test_names, results)):
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"Test {i+1}: {name:<20} {status}")
            if result:
                passed += 1
        
        print(f"\n🎯 Overall: {passed}/{len(tests)} tests passed")
        
        if passed == len(tests):
            print("🎉 Congratulations! Your AI system is working perfectly!")
        elif passed > 0:
            print("👍 Good progress! Some features are working.")
        else:
            print("🔧 Need to troubleshoot - check your deployment.")
        
        return passed == len(tests)

def main():
    """Main function to run tests"""
    print("🤖 Simple AI Document Processing Tester")
    print("For beginners to test their deployed system")
    print()
    
    # Get API endpoint from user
    if len(sys.argv) > 1:
        api_endpoint = sys.argv[1]
    else:
        print("Please provide your API endpoint:")
        print("Example: https://abc123.execute-api.us-east-1.amazonaws.com/production")
        api_endpoint = input("Enter API endpoint: ").strip()
    
    if not api_endpoint:
        print("❌ No API endpoint provided!")
        print("Usage: python simple_test.py <API_ENDPOINT>")
        sys.exit(1)
    
    # Run tests
    tester = SimpleAPITester(api_endpoint)
    success = tester.run_all_tests()
    
    if success:
        print("\n🚀 Next Steps:")
        print("1. Try uploading a real PDF file")
        print("2. Ask questions about financial documents")
        print("3. Request compliance calculations")
        print("4. Explore the CloudWatch dashboard")
    else:
        print("\n🔧 Troubleshooting Tips:")
        print("1. Check if deployment completed successfully")
        print("2. Verify AWS credentials and permissions")
        print("3. Check CloudWatch logs for errors")
        print("4. Ensure Bedrock model access is granted")

if __name__ == "__main__":
    main()
