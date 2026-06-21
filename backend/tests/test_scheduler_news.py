"""
Test suite for Auto-Trade Scheduler and News & Sentiment APIs
Tests: Scheduler status, start/stop, emergency controls, deployment modes
       News breaking, overview, and AI-powered analysis endpoints
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE}
        )
        assert response.status_code == 200, f"Auth failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Auth not successful: {data}"
        assert "token" in data, f"No token in response: {data}"
        return data["token"]
    
    def test_auth_access(self, auth_token):
        """Test authentication endpoint"""
        assert auth_token is not None
        assert len(auth_token) > 10
        print(f"✓ Auth token obtained: {auth_token[:20]}...")


class TestSchedulerAPIs:
    """Scheduler API tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_scheduler_status(self, headers):
        """Test GET /api/scheduler/status returns proper status"""
        response = requests.get(f"{BASE_URL}/api/scheduler/status", headers=headers)
        assert response.status_code == 200, f"Status failed: {response.text}"
        
        data = response.json()
        # Verify required fields
        assert "status" in data, f"Missing 'status' field: {data}"
        assert "deployment_mode" in data, f"Missing 'deployment_mode' field: {data}"
        assert "market_session" in data, f"Missing 'market_session' field: {data}"
        assert "settings" in data, f"Missing 'settings' field: {data}"
        
        # Verify status is valid
        assert data["status"] in ["off", "running", "paused", "emergency_stop"], f"Invalid status: {data['status']}"
        
        # Verify deployment_mode is valid
        assert data["deployment_mode"] in ["paper", "shadow", "limited_live", "full_live"], f"Invalid deployment_mode: {data['deployment_mode']}"
        
        # Verify market_session is valid
        valid_sessions = ["pre_market", "regular", "closing", "after_hours", "closed"]
        assert data["market_session"] in valid_sessions, f"Invalid market_session: {data['market_session']}"
        
        print(f"✓ Scheduler status: {data['status']}, mode: {data['deployment_mode']}, session: {data['market_session']}")
    
    def test_scheduler_start(self, headers):
        """Test POST /api/scheduler/start starts the scheduler"""
        response = requests.post(f"{BASE_URL}/api/scheduler/start", headers=headers)
        assert response.status_code == 200, f"Start failed: {response.text}"
        
        data = response.json()
        # Should return status or already_running
        assert "status" in data, f"Missing 'status' field: {data}"
        assert data["status"] in ["started", "already_running", "emergency_stop"], f"Unexpected status: {data}"
        
        if data["status"] == "started":
            assert "deployment_mode" in data, f"Missing deployment_mode on start: {data}"
            print(f"✓ Scheduler started in {data.get('deployment_mode', 'unknown')} mode")
        else:
            print(f"✓ Scheduler start response: {data['status']}")
    
    def test_scheduler_stop(self, headers):
        """Test POST /api/scheduler/stop stops the scheduler"""
        response = requests.post(f"{BASE_URL}/api/scheduler/stop", headers=headers)
        assert response.status_code == 200, f"Stop failed: {response.text}"
        
        data = response.json()
        assert "status" in data, f"Missing 'status' field: {data}"
        assert data["status"] == "stopped", f"Unexpected status: {data}"
        print(f"✓ Scheduler stopped")
    
    def test_scheduler_emergency_stop(self, headers):
        """Test POST /api/scheduler/emergency-stop triggers emergency stop"""
        # First start the scheduler
        requests.post(f"{BASE_URL}/api/scheduler/start", headers=headers)
        
        # Then emergency stop
        response = requests.post(f"{BASE_URL}/api/scheduler/emergency-stop", headers=headers)
        assert response.status_code == 200, f"Emergency stop failed: {response.text}"
        
        data = response.json()
        assert "status" in data, f"Missing 'status' field: {data}"
        assert data["status"] == "emergency_stop", f"Unexpected status: {data}"
        assert "message" in data, f"Missing 'message' field: {data}"
        print(f"✓ Emergency stop activated: {data.get('message', '')}")
    
    def test_scheduler_clear_emergency(self, headers):
        """Test POST /api/scheduler/clear-emergency clears emergency state"""
        response = requests.post(f"{BASE_URL}/api/scheduler/clear-emergency", headers=headers)
        assert response.status_code == 200, f"Clear emergency failed: {response.text}"
        
        data = response.json()
        assert "status" in data, f"Missing 'status' field: {data}"
        # After clearing, status should be 'off'
        assert data["status"] == "off", f"Unexpected status after clear: {data}"
        print(f"✓ Emergency cleared, status: {data['status']}")
    
    def test_scheduler_notifications(self, headers):
        """Test GET /api/scheduler/notifications returns notifications"""
        response = requests.get(f"{BASE_URL}/api/scheduler/notifications?limit=30", headers=headers)
        assert response.status_code == 200, f"Notifications failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got: {type(data)}"
        
        # If there are notifications, verify structure
        if len(data) > 0:
            notif = data[0]
            assert "event" in notif, f"Missing 'event' in notification: {notif}"
            assert "message" in notif, f"Missing 'message' in notification: {notif}"
            assert "timestamp" in notif, f"Missing 'timestamp' in notification: {notif}"
            print(f"✓ Got {len(data)} notifications, latest: {notif.get('event', 'unknown')}")
        else:
            print(f"✓ Got 0 notifications (empty list)")
    
    def test_scheduler_execution_log(self, headers):
        """Test GET /api/scheduler/execution-log returns execution log"""
        response = requests.get(f"{BASE_URL}/api/scheduler/execution-log?limit=30", headers=headers)
        assert response.status_code == 200, f"Execution log failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got: {type(data)}"
        print(f"✓ Got {len(data)} execution log entries")


class TestNewsAPIs:
    """News & Sentiment API tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_news_breaking(self, headers):
        """Test GET /api/news/breaking returns array of breaking news"""
        response = requests.get(f"{BASE_URL}/api/news/breaking", headers=headers)
        assert response.status_code == 200, f"Breaking news failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got: {type(data)}"
        
        # If there are breaking news items, verify structure
        if len(data) > 0:
            item = data[0]
            assert "symbol" in item, f"Missing 'symbol' in breaking news: {item}"
            print(f"✓ Got {len(data)} breaking news items, first: {item.get('symbol', 'unknown')}")
        else:
            print(f"✓ Got 0 breaking news items (no catalysts detected)")
    
    def test_news_overview(self, headers):
        """Test GET /api/news/overview returns sentiment overview"""
        response = requests.get(f"{BASE_URL}/api/news/overview", headers=headers)
        assert response.status_code == 200, f"News overview failed: {response.text}"
        
        data = response.json()
        assert "total_analyzed" in data, f"Missing 'total_analyzed' field: {data}"
        
        # Verify structure
        assert isinstance(data["total_analyzed"], int), f"total_analyzed should be int: {data}"
        
        if "with_catalysts" in data:
            assert isinstance(data["with_catalysts"], int), f"with_catalysts should be int: {data}"
        
        if "distribution" in data:
            assert isinstance(data["distribution"], dict), f"distribution should be dict: {data}"
        
        print(f"✓ News overview: {data.get('total_analyzed', 0)} stocks analyzed")
    
    def test_news_analyze_aapl(self, headers):
        """Test GET /api/news/analyze/AAPL returns AI-powered analysis"""
        response = requests.get(f"{BASE_URL}/api/news/analyze/AAPL", headers=headers, timeout=60)
        assert response.status_code == 200, f"News analyze AAPL failed: {response.text}"
        
        data = response.json()
        
        # Verify required fields for AI analysis
        assert "symbol" in data, f"Missing 'symbol' field: {data}"
        assert data["symbol"] == "AAPL", f"Wrong symbol: {data['symbol']}"
        
        # Sentiment fields
        assert "sentiment_score" in data, f"Missing 'sentiment_score' field: {data}"
        assert "sentiment_label" in data, f"Missing 'sentiment_label' field: {data}"
        
        # Catalyst fields
        assert "catalyst_detected" in data, f"Missing 'catalyst_detected' field: {data}"
        
        # AI summary
        if "one_line_summary" in data:
            assert isinstance(data["one_line_summary"], str), f"one_line_summary should be string: {data}"
        
        # Top articles
        if "top_articles" in data:
            assert isinstance(data["top_articles"], list), f"top_articles should be list: {data}"
        
        print(f"✓ AAPL analysis: sentiment={data.get('sentiment_score', 'N/A')}, label={data.get('sentiment_label', 'N/A')}, catalyst={data.get('catalyst_detected', False)}")
    
    def test_news_analyze_nvda(self, headers):
        """Test GET /api/news/analyze/NVDA returns AI-powered analysis"""
        response = requests.get(f"{BASE_URL}/api/news/analyze/NVDA", headers=headers, timeout=60)
        assert response.status_code == 200, f"News analyze NVDA failed: {response.text}"
        
        data = response.json()
        assert "symbol" in data, f"Missing 'symbol' field: {data}"
        assert data["symbol"] == "NVDA", f"Wrong symbol: {data['symbol']}"
        assert "sentiment_score" in data, f"Missing 'sentiment_score' field: {data}"
        
        print(f"✓ NVDA analysis: sentiment={data.get('sentiment_score', 'N/A')}, label={data.get('sentiment_label', 'N/A')}")


class TestAutoTradeAPIs:
    """Auto-Trade API tests (existing functionality)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_auto_trade_status(self, headers):
        """Test GET /api/auto-trade/status returns status"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/status", headers=headers)
        assert response.status_code == 200, f"Auto-trade status failed: {response.text}"
        
        data = response.json()
        # Verify key fields exist
        assert "auto_enabled" in data or "settings" in data, f"Missing expected fields: {data}"
        print(f"✓ Auto-trade status retrieved")
    
    def test_auto_trade_scan(self, headers):
        """Test GET /api/auto-trade/scan returns scan results"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=120)
        assert response.status_code == 200, f"Auto-trade scan failed: {response.text}"
        
        data = response.json()
        # Should have day_trades and long_term arrays
        assert "day_trades" in data or "long_term" in data or "stats" in data, f"Missing expected fields: {data}"
        print(f"✓ Auto-trade scan completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
