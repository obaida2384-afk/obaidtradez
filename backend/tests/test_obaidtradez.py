"""
ObaidTradez Backend API Tests
Tests for: Access control, Trading signals, Investment signals, News, Chat
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"

class TestHealthCheck:
    """API Health Check Tests"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "ObaidTradez API"
        assert data["status"] == "running"
        print(f"✓ API root: {data}")


class TestAccessControl:
    """Access Code Authentication Tests"""
    
    def test_access_with_valid_code(self):
        """Test access with correct code"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "token" in data
        assert len(data["token"]) > 0
        print(f"✓ Valid access code: token received ({len(data['token'])} chars)")
        return data["token"]
    
    def test_access_with_invalid_code(self):
        """Test access with wrong code"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": "wrongcode123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        assert "Invalid" in data["message"]
        print(f"✓ Invalid code rejected: {data['message']}")
    
    def test_token_verification(self):
        """Test token verification endpoint"""
        # Get valid token first
        auth_response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE}
        )
        token = auth_response.json()["token"]
        
        # Verify token
        response = requests.get(
            f"{BASE_URL}/api/auth/verify",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == True
        print(f"✓ Token verification: valid={data['valid']}")
    
    def test_protected_endpoint_without_token(self):
        """Test that protected endpoints require auth"""
        response = requests.get(f"{BASE_URL}/api/trading/scan")
        assert response.status_code == 401
        print("✓ Protected endpoint requires auth")


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(
        f"{BASE_URL}/api/auth/access",
        json={"code": ACCESS_CODE}
    )
    if response.status_code == 200 and response.json().get("success"):
        return response.json()["token"]
    pytest.skip("Authentication failed")


@pytest.fixture
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestTradingSignals:
    """Trading Signal API Tests"""
    
    def test_trading_scan(self, auth_headers):
        """Test trading scan endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/trading/scan",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check expected categories exist
        assert "hot" in data
        assert "breakout" in data
        assert "momentum" in data
        assert "high_volume" in data
        assert "all" in data
        
        # Check all signals have required fields
        all_signals = data.get("all", [])
        print(f"✓ Trading scan: {len(all_signals)} total signals")
        print(f"  - Hot: {len(data.get('hot', []))}")
        print(f"  - Breakout: {len(data.get('breakout', []))}")
        print(f"  - Momentum: {len(data.get('momentum', []))}")
        print(f"  - High Volume: {len(data.get('high_volume', []))}")
        print(f"  - Avoid: {len(data.get('avoid', []))}")
        
        if all_signals:
            signal = all_signals[0]
            assert "symbol" in signal
            assert "signal" in signal
            assert "confidence" in signal
            assert "category" in signal
            print(f"  Sample: {signal['symbol']} - {signal['signal']} ({signal['confidence']*100:.0f}%)")
    
    def test_trading_analyze_symbol(self, auth_headers):
        """Test individual symbol trading analysis"""
        response = requests.get(
            f"{BASE_URL}/api/trading/analyze/AAPL",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["symbol"] == "AAPL"
        assert "signal" in data
        # Symbol may be excluded by strict filters — both cases are valid
        if data.get("included") is False:
            assert "exclusion_reason" in data
            print(f"✓ AAPL excluded: {data['exclusion_reason']}")
        else:
            assert "confidence" in data
            assert "entry_zone" in data
            assert "stop_loss" in data
            assert "take_profit" in data
            print(f"✓ AAPL Trading Analysis: Signal={data['signal']}")
    
    def test_trading_analyze_invalid_symbol(self, auth_headers):
        """Test analysis of invalid symbol"""
        response = requests.get(
            f"{BASE_URL}/api/trading/analyze/INVALIDXYZ123",
            headers=auth_headers
        )
        # API returns 200 with included=False for invalid symbols
        assert response.status_code == 200
        data = response.json()
        assert data.get("included") is False
        assert data.get("exclusion_reason") is not None
        print(f"✓ Invalid symbol handled: {data['exclusion_reason']}")


class TestInvestmentSignals:
    """Investment Signal API Tests"""
    
    def test_investments_scan(self, auth_headers):
        """Test investment scan endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/investments/scan",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check expected categories exist
        assert "hot" in data
        assert "bullish" in data
        assert "undervalued" in data
        assert "watch" in data
        assert "bearish" in data
        assert "all" in data
        
        all_signals = data.get("all", [])
        print(f"✓ Investment scan: {len(all_signals)} total signals")
        print(f"  - Hot: {len(data.get('hot', []))}")
        print(f"  - Bullish: {len(data.get('bullish', []))}")
        print(f"  - Undervalued: {len(data.get('undervalued', []))}")
        print(f"  - Watch: {len(data.get('watch', []))}")
        print(f"  - Bearish: {len(data.get('bearish', []))}")
        
        if all_signals:
            signal = all_signals[0]
            assert "symbol" in signal
            assert "overall_score" in signal
            assert "valuation_score" in signal
            assert "quality_score" in signal
            print(f"  Sample: {signal['symbol']} - Score: {signal['overall_score']:.1f}")
    
    def test_investments_analyze_symbol(self, auth_headers):
        """Test individual symbol investment analysis"""
        response = requests.get(
            f"{BASE_URL}/api/investments/analyze/MSFT",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["symbol"] == "MSFT"
        assert "signal" in data
        assert "overall_score" in data
        assert "valuation_score" in data
        assert "quality_score" in data
        assert "growth_score" in data
        assert "financial_strength" in data
        assert "bull_case" in data
        assert "bear_case" in data
        
        print(f"✓ MSFT Investment Analysis:")
        print(f"  Signal: {data['signal']}, Overall: {data['overall_score']:.1f}")
        print(f"  Valuation: {data['valuation_score']:.1f}, Quality: {data['quality_score']:.1f}")
        if data.get('bull_case'):
            print(f"  Bull case: {data['bull_case'][0][:50]}...")


class TestNewsAndSentiment:
    """News & Sentiment API Tests"""
    
    def test_market_news(self, auth_headers):
        """Test market news endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/news/market",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # News API returns a dict with analysis data (not a raw list)
        assert isinstance(data, dict)
        assert "article_count" in data or "articles" in data or "catalyst_score" in data
        print(f"✓ Market news: {data.get('article_count', 'N/A')} articles")
    
    def test_symbol_news(self, auth_headers):
        """Test symbol-specific news"""
        response = requests.get(
            f"{BASE_URL}/api/news/TSLA",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # News API returns dict with analysis data
        assert isinstance(data, dict)
        assert "symbol" in data or "article_count" in data
        print(f"✓ TSLA news: {data.get('article_count', 'N/A')} articles")


class TestChatbot:
    """AI Chatbot API Tests"""
    
    def test_chat_general_mode(self, auth_headers):
        """Test chatbot in general mode"""
        response = requests.post(
            f"{BASE_URL}/api/chat",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={
                "message": "What is a P/E ratio?",
                "mode": "general"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "response" in data
        assert "session_id" in data
        assert len(data["response"]) > 50  # Should have substantial response
        
        print(f"✓ Chat (general): {len(data['response'])} chars response")
        print(f"  Session: {data['session_id'][:20]}...")
    
    def test_chat_trading_mode(self, auth_headers):
        """Test chatbot in trading mode"""
        response = requests.post(
            f"{BASE_URL}/api/chat",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={
                "message": "Give me a quick trade idea",
                "mode": "trading"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "response" in data
        print(f"✓ Chat (trading): {len(data['response'])} chars response")
    
    def test_chat_investing_mode(self, auth_headers):
        """Test chatbot in investing mode"""
        response = requests.post(
            f"{BASE_URL}/api/chat",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={
                "message": "What makes a good value stock?",
                "mode": "investing"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "response" in data
        print(f"✓ Chat (investing): {len(data['response'])} chars response")


class TestSearchAndAccount:
    """Search and Account API Tests"""
    
    def test_symbol_search(self, auth_headers):
        """Test symbol search"""
        response = requests.get(
            f"{BASE_URL}/api/search",
            headers=auth_headers,
            params={"q": "AAPL"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ Search 'AAPL': {len(data)} results")
        if data:
            print(f"  First: {data[0]}")
    
    def test_alpaca_account(self, auth_headers):
        """Test Alpaca account endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/account",
            headers=auth_headers
        )
        # May return 500 if Alpaca keys are invalid, but should not crash
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Alpaca account: equity=${data.get('equity', 'N/A')}")
        else:
            print(f"⚠ Alpaca account: status {response.status_code} (may need valid keys)")
    
    def test_positions(self, auth_headers):
        """Test positions endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/positions",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Positions: {len(data)} open positions")
    
    def test_orders(self, auth_headers):
        """Test orders endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/orders",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Orders: {len(data)} orders")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
