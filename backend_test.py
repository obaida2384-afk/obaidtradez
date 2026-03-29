#!/usr/bin/env python3
"""
AlphaLens Backend API Testing Suite
Tests all endpoints with real FMP data integration
"""

import requests
import sys
import json
from datetime import datetime
import time

class AlphaLensAPITester:
    def __init__(self, base_url="https://obaid-tradez-preview.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.session = requests.Session()
        self.session.timeout = 30

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
            self.failed_tests.append({"test": name, "error": details})

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test with detailed logging"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        default_headers = {'Content-Type': 'application/json'}
        if headers:
            default_headers.update(headers)

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=default_headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=default_headers)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
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
        """Test basic API connectivity"""
        try:
            response = self.session.get(f"{self.api_url}/")
            success = response.status_code == 200
            data = response.json() if success else {}
            
            if success and "AlphaLens API" in data.get("message", ""):
                self.log_test("API Status Check", True)
                return True
            else:
                self.log_test("API Status Check", False, f"Status: {response.status_code}, Response: {data}")
                return False
        except Exception as e:
            self.log_test("API Status Check", False, str(e))
            return False

    def test_stock_analysis(self, symbol="AAPL"):
        """Test stock analysis endpoint with real data"""
        try:
            response = self.session.get(f"{self.api_url}/stock/{symbol}")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                required_fields = ["symbol", "overall_score", "valuation_score", "fundamentals_score", 
                                 "growth_score", "momentum_score", "investment_signal"]
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    self.log_test(f"Stock Analysis ({symbol})", False, f"Missing fields: {missing_fields}")
                    return False
                
                # Validate score ranges
                score_fields = ["overall_score", "valuation_score", "fundamentals_score", "growth_score", "momentum_score"]
                invalid_scores = []
                for field in score_fields:
                    score = data.get(field, 0)
                    if not (0 <= score <= 100):
                        invalid_scores.append(f"{field}={score}")
                
                if invalid_scores:
                    self.log_test(f"Stock Analysis ({symbol})", False, f"Invalid scores: {invalid_scores}")
                    return False
                
                self.log_test(f"Stock Analysis ({symbol})", True)
                print(f"   📊 Overall Score: {data['overall_score']:.1f}/100")
                print(f"   🎯 Signal: {data['investment_signal']}")
                return True
            else:
                error_msg = response.text[:200] if response.text else f"HTTP {response.status_code}"
                self.log_test(f"Stock Analysis ({symbol})", False, error_msg)
                return False
                
        except Exception as e:
            self.log_test(f"Stock Analysis ({symbol})", False, str(e))
            return False

    def test_recommendations(self):
        """Test recommendations endpoint"""
        try:
            response = self.session.get(f"{self.api_url}/recommendations?limit=5")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Check first recommendation structure
                    rec = data[0]
                    required_fields = ["symbol", "overall_score", "investment_signal"]
                    missing_fields = [field for field in required_fields if field not in rec]
                    
                    if missing_fields:
                        self.log_test("Recommendations", False, f"Missing fields in recommendation: {missing_fields}")
                        return False
                    
                    self.log_test("Recommendations", True)
                    print(f"   📈 Returned {len(data)} recommendations")
                    print(f"   🥇 Top pick: {rec['symbol']} (Score: {rec['overall_score']:.1f})")
                    return True
                else:
                    self.log_test("Recommendations", False, "Empty or invalid response format")
                    return False
            else:
                self.log_test("Recommendations", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Recommendations", False, str(e))
            return False

    def test_rankings(self, strategy="value"):
        """Test strategy rankings endpoint"""
        try:
            response = self.session.get(f"{self.api_url}/rankings/{strategy}?limit=5")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    self.log_test(f"Rankings ({strategy})", True)
                    print(f"   📊 {strategy.title()} strategy: {len(data)} stocks")
                    return True
                else:
                    self.log_test(f"Rankings ({strategy})", False, "Empty response")
                    return False
            else:
                self.log_test(f"Rankings ({strategy})", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test(f"Rankings ({strategy})", False, str(e))
            return False

    def test_screener(self):
        """Test stock screener endpoint"""
        try:
            payload = {
                "min_market_cap": 10000000000,  # 10B
                "limit": 5
            }
            response = self.session.post(f"{self.api_url}/screener", json=payload)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Screener", True)
                    print(f"   🔍 Found {len(data)} stocks matching criteria")
                    return True
                else:
                    self.log_test("Screener", False, "Invalid response format")
                    return False
            else:
                self.log_test("Screener", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Screener", False, str(e))
            return False

    def test_chat(self):
        """Test AI chat endpoint"""
        try:
            payload = {
                "message": "What are the top 3 value stocks?",
                "session_id": f"test_{int(time.time())}"
            }
            response = self.session.post(f"{self.api_url}/chat", json=payload)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                required_fields = ["response", "session_id"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("AI Chat", False, f"Missing fields: {missing_fields}")
                    return False
                
                if len(data["response"]) < 10:
                    self.log_test("AI Chat", False, "Response too short")
                    return False
                
                self.log_test("AI Chat", True)
                print(f"   🤖 Response length: {len(data['response'])} chars")
                return True
            else:
                self.log_test("AI Chat", False, f"HTTP {response.status_code}: {response.text[:100]}")
                return False
                
        except Exception as e:
            self.log_test("AI Chat", False, str(e))
            return False

    def test_search(self):
        """Test stock search endpoint"""
        try:
            response = self.session.get(f"{self.api_url}/search?q=AAPL")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("Stock Search", True)
                    print(f"   🔍 Search results: {len(data)} items")
                    return True
                else:
                    self.log_test("Stock Search", False, "Invalid response format")
                    return False
            else:
                self.log_test("Stock Search", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Stock Search", False, str(e))
            return False

    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting AlphaLens API Test Suite")
        print(f"📡 Testing against: {self.base_url}")
        print("=" * 50)
        
        # Core API tests
        if not self.test_api_status():
            print("❌ API is not accessible. Stopping tests.")
            return False
        
        # Stock analysis tests
        self.test_stock_analysis("AAPL")
        self.test_stock_analysis("MSFT")
        
        # Recommendation tests
        self.test_recommendations()
        
        # Strategy ranking tests
        for strategy in ["value", "growth", "momentum", "quality"]:
            self.test_rankings(strategy)
        
        # Screener test
        self.test_screener()
        
        # Search test
        self.test_search()
        
        # AI Chat test (may take longer)
        print("\n🤖 Testing AI Chat (this may take a few seconds)...")
        self.test_chat()
        
        # Summary
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for failure in self.failed_tests:
                print(f"   • {failure['test']}: {failure['error']}")
        
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"✅ Success Rate: {success_rate:.1f}%")
        
        return success_rate >= 80  # 80% pass rate considered successful

def main():
    """Main test execution"""
    print("🚀 Starting AlphaLens API Tests")
    print("=" * 50)
    
    tester = AlphaLensAPITester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()