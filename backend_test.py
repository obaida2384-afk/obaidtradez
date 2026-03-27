import requests
import sys
import json
from datetime import datetime

class FinanceAPITester:
    def __init__(self, base_url="https://fintech-agent-obaid.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.session_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        default_headers = {'Content-Type': 'application/json'}
        if headers:
            default_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=default_headers, timeout=30)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_api_status(self):
        """Test basic API status"""
        return self.run_test("API Status", "GET", "", 200)

    def test_infographic_data(self):
        """Test infographic data endpoint"""
        return self.run_test("Infographic Data", "GET", "infographic/data", 200)

    def test_chat_functionality(self):
        """Test chat with Obaid"""
        success, response = self.run_test(
            "Chat with Obaid",
            "POST",
            "chat",
            200,
            data={"message": "What is the P/E ratio formula?"}
        )
        
        if success and 'session_id' in response:
            self.session_id = response['session_id']
            print(f"   Session ID: {self.session_id}")
            
            # Test follow-up message
            follow_up_success, _ = self.run_test(
                "Chat Follow-up",
                "POST", 
                "chat",
                200,
                data={"message": "Can you explain ROI?", "session_id": self.session_id}
            )
            return follow_up_success
        
        return success

    def test_chat_history(self):
        """Test chat history retrieval"""
        if not self.session_id:
            print("⚠️  Skipping chat history test - no session ID available")
            return True
            
        return self.run_test(
            "Chat History",
            "GET",
            f"chat/history/{self.session_id}",
            200
        )[0]

    def test_stock_lookup(self):
        """Test stock lookup functionality"""
        # Test with valid stock symbol
        success1, response1 = self.run_test(
            "Stock Lookup (AAPL)",
            "GET",
            "stock/AAPL",
            200
        )
        
        # Test with POST method
        success2, response2 = self.run_test(
            "Stock Lookup POST (MSFT)",
            "POST",
            "stock",
            200,
            data={"symbol": "MSFT"}
        )
        
        # Test with invalid symbol
        success3, response3 = self.run_test(
            "Stock Lookup (Invalid)",
            "GET",
            "stock/INVALID123",
            200  # API should return 200 with error message
        )
        
        return success1 and success2 and success3

    def test_status_endpoints(self):
        """Test status check endpoints"""
        # Test POST status
        success1, response1 = self.run_test(
            "Create Status Check",
            "POST",
            "status",
            200,
            data={"client_name": "test_client"}
        )
        
        # Test GET status
        success2, response2 = self.run_test(
            "Get Status Checks",
            "GET",
            "status",
            200
        )
        
        return success1 and success2

def main():
    print("🚀 Starting Finance AI API Tests")
    print("=" * 50)
    
    tester = FinanceAPITester()
    
    # Test basic API functionality
    print("\n📡 Testing Basic API Endpoints...")
    api_status = tester.test_api_status()
    
    print("\n📊 Testing Infographic Data...")
    infographic_status = tester.test_infographic_data()
    
    print("\n🤖 Testing Chat Functionality...")
    chat_status = tester.test_chat_functionality()
    
    print("\n📈 Testing Stock Lookup...")
    stock_status = tester.test_stock_lookup()
    
    print("\n💬 Testing Chat History...")
    history_status = tester.test_chat_history()
    
    print("\n🔍 Testing Status Endpoints...")
    status_endpoints = tester.test_status_endpoints()
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())