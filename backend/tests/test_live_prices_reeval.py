"""
Test suite for Live Prices and Re-Evaluation features
Tests: Live price engine, WebSocket/REST fallback, Re-eval engine APIs
"""
import pytest
import requests
import os
import time

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    # Try to load from frontend .env
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    BASE_URL = line.split('=', 1)[1].strip().rstrip('/')
                    break
    except:
        pass

ACCESS_CODE = "Bullishalmarkhan7.7"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/access",
        json={"code": ACCESS_CODE}
    )
    assert response.status_code == 200, f"Auth failed: {response.text}"
    data = response.json()
    assert data.get("success") == True
    return data.get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestAuthAccess:
    """Test access gate authentication"""
    
    def test_access_with_valid_code(self):
        """Test access with correct code"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "token" in data
        assert len(data["token"]) > 0
    
    def test_access_with_invalid_code(self):
        """Test access with wrong code"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": "wrongcode"}
        )
        # API returns 200 with success=false for invalid codes
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == False
        assert data.get("token") is None


class TestLivePriceEngineStatus:
    """Test live price engine status endpoint"""
    
    def test_get_engine_status(self, auth_headers):
        """Test /api/live-prices/status/engine returns valid status"""
        response = requests.get(
            f"{BASE_URL}/api/live-prices/status/engine",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "running" in data
        assert "mode" in data
        assert "tracked_symbols" in data
        assert "live_count" in data
        assert "stale_count" in data
        assert "stats" in data
        
        # Verify mode is valid
        assert data["mode"] in ["websocket", "rest_fallback", "stopped", None]
        
        # Verify stats structure
        stats = data["stats"]
        assert "trades_received" in stats
        assert "quotes_received" in stats
        assert "rest_polls" in stats
    
    def test_engine_status_has_mode_field(self, auth_headers):
        """Verify mode field exists for UI badge display"""
        response = requests.get(
            f"{BASE_URL}/api/live-prices/status/engine",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "mode" in data, "mode field required for UI badge"


class TestLivePricesAll:
    """Test /api/live-prices/all endpoint"""
    
    def test_get_all_prices(self, auth_headers):
        """Test getting all live prices"""
        response = requests.get(
            f"{BASE_URL}/api/live-prices/all",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "prices" in data
        assert "engine" in data
        
        # Verify engine data
        engine = data["engine"]
        assert "running" in engine
        assert "mode" in engine
        assert "tracked_symbols" in engine
    
    def test_prices_have_required_fields(self, auth_headers):
        """Test that price data has all required fields for UI"""
        response = requests.get(
            f"{BASE_URL}/api/live-prices/all",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        prices = data.get("prices", {})
        if prices:
            # Check first price entry
            symbol = list(prices.keys())[0]
            price_data = prices[symbol]
            
            # Required fields for price table
            required_fields = [
                "display_price", "bid", "ask", "spread", 
                "spread_pct", "mid_price", "source", "stale"
            ]
            for field in required_fields:
                assert field in price_data, f"Missing field: {field}"


class TestLivePricesStartStop:
    """Test start/stop live price streaming"""
    
    def test_start_live_prices(self, auth_headers):
        """Test starting live price feed"""
        response = requests.post(
            f"{BASE_URL}/api/live-prices/start",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "started"
        assert "symbols" in data
    
    def test_stop_live_prices(self, auth_headers):
        """Test stopping live price feed"""
        response = requests.post(
            f"{BASE_URL}/api/live-prices/stop",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "stopped"


class TestReEvalStats:
    """Test re-evaluation stats endpoint"""
    
    def test_get_reeval_stats(self, auth_headers):
        """Test /api/reeval/stats returns valid stats"""
        response = requests.get(
            f"{BASE_URL}/api/reeval/stats",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify required stats fields
        required_fields = [
            "total_triggers", "throttled", "position_checks",
            "stop_loss_triggered", "take_profit_triggered",
            "setup_changes", "stale_blocked"
        ]
        for field in required_fields:
            assert field in data, f"Missing reeval stat: {field}"
        
        # Verify values are integers
        for field in required_fields:
            assert isinstance(data[field], int), f"{field} should be int"


class TestReEvalEvents:
    """Test re-evaluation events endpoint"""
    
    def test_get_reeval_events(self, auth_headers):
        """Test /api/reeval/events returns events array"""
        response = requests.get(
            f"{BASE_URL}/api/reeval/events?limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "events" in data
        assert isinstance(data["events"], list)
    
    def test_reeval_events_with_limit(self, auth_headers):
        """Test events endpoint respects limit parameter"""
        response = requests.get(
            f"{BASE_URL}/api/reeval/events?limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) <= 5


class TestReEvalHistory:
    """Test re-evaluation history endpoint"""
    
    def test_get_reeval_history(self, auth_headers):
        """Test /api/reeval/history returns persisted events"""
        response = requests.get(
            f"{BASE_URL}/api/reeval/history?limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "events" in data
        assert "count" in data
        assert isinstance(data["events"], list)


class TestLivePriceEngineIntegration:
    """Integration tests for live price engine flow"""
    
    def test_full_flow_start_check_stop(self, auth_headers):
        """Test complete flow: start -> check status -> stop"""
        # Start
        start_resp = requests.post(
            f"{BASE_URL}/api/live-prices/start",
            headers=auth_headers
        )
        assert start_resp.status_code == 200
        
        # Wait for engine to initialize
        time.sleep(2)
        
        # Check status
        status_resp = requests.get(
            f"{BASE_URL}/api/live-prices/status/engine",
            headers=auth_headers
        )
        assert status_resp.status_code == 200
        status = status_resp.json()
        assert status["running"] == True
        
        # Get prices
        prices_resp = requests.get(
            f"{BASE_URL}/api/live-prices/all",
            headers=auth_headers
        )
        assert prices_resp.status_code == 200
        prices_data = prices_resp.json()
        assert len(prices_data.get("prices", {})) > 0
        
        # Stop
        stop_resp = requests.post(
            f"{BASE_URL}/api/live-prices/stop",
            headers=auth_headers
        )
        assert stop_resp.status_code == 200


class TestUnauthorizedAccess:
    """Test endpoints require authentication"""
    
    def test_engine_status_requires_auth(self):
        """Test engine status requires auth token"""
        response = requests.get(f"{BASE_URL}/api/live-prices/status/engine")
        assert response.status_code == 401
    
    def test_reeval_stats_requires_auth(self):
        """Test reeval stats requires auth token"""
        response = requests.get(f"{BASE_URL}/api/reeval/stats")
        assert response.status_code == 401
    
    def test_start_requires_auth(self):
        """Test start endpoint requires auth token"""
        response = requests.post(f"{BASE_URL}/api/live-prices/start")
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
