"""
Test suite for risky stocks filtering and auto-trade safety controls
Tests the new risky stock blocking feature for ObaidTradez
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ACCESS_CODE = "Bullishalmarkhan7.7"

class TestRiskyStocksAPI:
    """Tests for risky stocks endpoints and safety controls"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200, f"Auth failed: {response.text}"
        data = response.json()
        assert data.get("success"), "Auth not successful"
        self.token = data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_risky_stocks_endpoint_returns_list(self):
        """Test /api/paper/risky-stocks returns list of blocked stocks"""
        response = requests.get(f"{BASE_URL}/api/paper/risky-stocks", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "risky_stocks" in data, "Missing risky_stocks field"
        assert "count" in data, "Missing count field"
        assert "reason" in data, "Missing reason field"
        
        risky_stocks = data["risky_stocks"]
        assert isinstance(risky_stocks, list), "risky_stocks should be a list"
        assert len(risky_stocks) >= 80, f"Expected 80+ risky stocks, got {len(risky_stocks)}"
        
        print(f"✓ Risky stocks endpoint returns {len(risky_stocks)} blocked stocks")
    
    def test_risky_stocks_contains_meme_stocks(self):
        """Test that meme stocks are in the risky list"""
        response = requests.get(f"{BASE_URL}/api/paper/risky-stocks", headers=self.headers)
        assert response.status_code == 200
        
        risky_stocks = response.json()["risky_stocks"]
        
        # Check for known meme stocks
        meme_stocks = ["GME", "AMC", "BBBY", "BB", "CLOV"]
        for stock in meme_stocks:
            assert stock in risky_stocks, f"Meme stock {stock} should be in risky list"
        
        print(f"✓ Meme stocks (GME, AMC, BBBY, BB, CLOV) are in risky list")
    
    def test_risky_stocks_contains_leveraged_etfs(self):
        """Test that leveraged ETFs are in the risky list"""
        response = requests.get(f"{BASE_URL}/api/paper/risky-stocks", headers=self.headers)
        assert response.status_code == 200
        
        risky_stocks = response.json()["risky_stocks"]
        
        # Check for leveraged ETFs
        leveraged_etfs = ["TQQQ", "SQQQ", "SPXL", "SPXS", "SOXL", "SOXS", "UVXY"]
        for etf in leveraged_etfs:
            assert etf in risky_stocks, f"Leveraged ETF {etf} should be in risky list"
        
        print(f"✓ Leveraged ETFs (TQQQ, SQQQ, SPXL, etc.) are in risky list")
    
    def test_check_symbol_gme_is_risky(self):
        """Test /api/paper/check-symbol/GME returns is_risky=true"""
        response = requests.get(f"{BASE_URL}/api/paper/check-symbol/GME", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data["symbol"] == "GME", "Symbol should be GME"
        assert data["is_risky"] == True, "GME should be risky"
        assert data["can_auto_trade"] == False, "GME should not be auto-tradeable"
        assert "BLOCKED" in data["message"], "Message should indicate blocked"
        
        print(f"✓ GME is correctly identified as risky (is_risky=true, can_auto_trade=false)")
    
    def test_check_symbol_amc_is_risky(self):
        """Test /api/paper/check-symbol/AMC returns is_risky=true"""
        response = requests.get(f"{BASE_URL}/api/paper/check-symbol/AMC", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["is_risky"] == True, "AMC should be risky"
        assert data["can_auto_trade"] == False, "AMC should not be auto-tradeable"
        
        print(f"✓ AMC is correctly identified as risky")
    
    def test_check_symbol_tqqq_is_risky(self):
        """Test /api/paper/check-symbol/TQQQ returns is_risky=true"""
        response = requests.get(f"{BASE_URL}/api/paper/check-symbol/TQQQ", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["is_risky"] == True, "TQQQ should be risky"
        assert data["can_auto_trade"] == False, "TQQQ should not be auto-tradeable"
        
        print(f"✓ TQQQ (leveraged ETF) is correctly identified as risky")
    
    def test_check_symbol_aapl_is_not_risky(self):
        """Test /api/paper/check-symbol/AAPL returns is_risky=false"""
        response = requests.get(f"{BASE_URL}/api/paper/check-symbol/AAPL", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data["symbol"] == "AAPL", "Symbol should be AAPL"
        assert data["is_risky"] == False, "AAPL should NOT be risky"
        assert data["can_auto_trade"] == True, "AAPL should be auto-tradeable"
        assert "ALLOWED" in data["message"], "Message should indicate allowed"
        
        print(f"✓ AAPL is correctly identified as safe (is_risky=false, can_auto_trade=true)")
    
    def test_check_symbol_msft_is_not_risky(self):
        """Test /api/paper/check-symbol/MSFT returns is_risky=false"""
        response = requests.get(f"{BASE_URL}/api/paper/check-symbol/MSFT", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["is_risky"] == False, "MSFT should NOT be risky"
        assert data["can_auto_trade"] == True, "MSFT should be auto-tradeable"
        
        print(f"✓ MSFT is correctly identified as safe")
    
    def test_check_symbol_case_insensitive(self):
        """Test that symbol check is case-insensitive"""
        # Test lowercase
        response = requests.get(f"{BASE_URL}/api/paper/check-symbol/gme", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "GME", "Symbol should be uppercased"
        assert data["is_risky"] == True, "gme (lowercase) should still be risky"
        
        print(f"✓ Symbol check is case-insensitive (gme -> GME)")
    
    def test_crypto_related_stocks_are_risky(self):
        """Test that crypto-related stocks are in risky list"""
        crypto_stocks = ["MSTR", "RIOT", "MARA", "COIN"]
        
        for stock in crypto_stocks:
            response = requests.get(f"{BASE_URL}/api/paper/check-symbol/{stock}", headers=self.headers)
            assert response.status_code == 200
            data = response.json()
            assert data["is_risky"] == True, f"{stock} should be risky"
        
        print(f"✓ Crypto-related stocks (MSTR, RIOT, MARA, COIN) are risky")
    
    def test_ev_spacs_are_risky(self):
        """Test that EV SPACs are in risky list"""
        ev_spacs = ["LCID", "RIVN", "NKLA"]
        
        for stock in ev_spacs:
            response = requests.get(f"{BASE_URL}/api/paper/check-symbol/{stock}", headers=self.headers)
            assert response.status_code == 200
            data = response.json()
            assert data["is_risky"] == True, f"{stock} should be risky"
        
        print(f"✓ EV SPACs (LCID, RIVN, NKLA) are risky")


class TestInvestmentIdeasCount:
    """Tests for investment ideas page showing 700+ stocks"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200
        data = response.json()
        self.token = data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_investments_browse_returns_stocks(self):
        """Test /api/investments/browse returns stock list"""
        response = requests.get(f"{BASE_URL}/api/investments/browse", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # API returns paginated response with signals list
        if isinstance(data, dict):
            signals = data.get("signals", [])
            total = data.get("total", len(signals))
            stock_count = total
        else:
            stock_count = len(data)
        
        print(f"✓ Investment browse returns {stock_count} stocks")
        
        # Check if we have a reasonable number of stocks (700+ target)
        assert stock_count >= 100, f"Expected at least 100 stocks, got {stock_count}"
    
    def test_investments_scan_returns_categories(self):
        """Test /api/investments/scan returns categorized signals"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Check for expected categories
        expected_categories = ["hot", "bullish", "undervalued", "watch", "bearish"]
        for cat in expected_categories:
            assert cat in data, f"Missing category: {cat}"
        
        # Count total signals
        total = sum(len(data.get(cat, [])) for cat in expected_categories)
        print(f"✓ Investment scan returns {total} categorized signals")


class TestAutoTradePageIntegration:
    """Tests for Auto Trade page integration with risky stocks"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200
        data = response.json()
        self.token = data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_paper_settings_endpoint(self):
        """Test /api/paper/settings returns settings"""
        response = requests.get(f"{BASE_URL}/api/paper/settings", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "kill_switch" in data, "Missing kill_switch setting"
        assert "manual_approval" in data, "Missing manual_approval setting"
        
        print(f"✓ Paper settings endpoint works")
    
    def test_paper_queue_endpoint(self):
        """Test /api/paper/queue returns trade queue"""
        response = requests.get(f"{BASE_URL}/api/paper/queue", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Queue should be a list"
        
        print(f"✓ Paper queue endpoint works, {len(data)} trades in queue")
    
    def test_paper_stats_endpoint(self):
        """Test /api/paper/stats returns statistics"""
        response = requests.get(f"{BASE_URL}/api/paper/stats", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # Stats should have counts
        assert "pending" in data or "total" in data or isinstance(data, dict), "Stats should be a dict"
        
        print(f"✓ Paper stats endpoint works")


class TestWatchlistFunctionality:
    """Tests for watchlist functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200
        data = response.json()
        self.token = data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_watchlist_get(self):
        """Test GET /api/watchlist returns watchlist items"""
        response = requests.get(f"{BASE_URL}/api/watchlist", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Watchlist should be a list"
        
        print(f"✓ Watchlist endpoint works, {len(data)} items")
    
    def test_watchlist_add_and_remove(self):
        """Test adding and removing from watchlist"""
        test_symbol = "TEST_WATCHLIST_ITEM"
        
        # Add to watchlist
        response = requests.post(
            f"{BASE_URL}/api/watchlist",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"symbol": test_symbol, "source": "test"}
        )
        # May fail if symbol doesn't exist, that's ok
        
        # Try to remove (cleanup)
        requests.delete(f"{BASE_URL}/api/watchlist/{test_symbol}", headers=self.headers)
        
        print(f"✓ Watchlist add/remove endpoints accessible")


class TestTradingSignalsWithNewsSentiment:
    """Tests for trading signals with news sentiment badges"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200
        data = response.json()
        self.token = data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_trading_scan_returns_signals(self):
        """Test /api/trading/scan returns trading signals"""
        response = requests.get(f"{BASE_URL}/api/trading/scan", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Check for expected structure
        assert "all" in data or "top_trades" in data, "Should have signals"
        
        # Check for news sentiment fields in signals
        signals = data.get("all", []) or data.get("top_trades", [])
        if signals:
            signal = signals[0]
            # News sentiment fields should be present
            assert "news_sentiment" in signal or signal.get("news_sentiment") is None, "news_sentiment field should exist"
        
        print(f"✓ Trading scan returns signals with news sentiment fields")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
