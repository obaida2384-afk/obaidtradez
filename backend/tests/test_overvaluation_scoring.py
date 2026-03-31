"""
Test Overvaluation Scoring Fix - Iteration 31
Tests that MRVL and other overvalued stocks are correctly categorized as 'Overpriced' with 'Hold' signal
instead of 'Hot/Bullish' with 'Buy' signal.

Key fixes tested:
1. Overvaluation penalty in investment scoring (upside < -25% gets penalty)
2. Entry status includes STALE_SETUP (>10% drift) and BLOWN_STOP (price at/below stop)
3. Investments scan overrides 'Buy' to 'Hold/Overpriced' for overvalued stocks
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestOvervaluationScoringFix:
    """Tests for the overvaluation scoring fix - MRVL should be Overpriced/Hold, not Hot/Buy"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for API calls"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": "Bullishalmarkhan7.7"})
        assert response.status_code == 200, f"Auth failed: {response.text}"
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_mrvl_not_in_hot_category(self):
        """MRVL should NOT be in 'hot' category due to -76% upside"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=self.headers)
        assert response.status_code == 200, f"Investments scan failed: {response.text}"
        
        data = response.json()
        hot_stocks = data.get("hot", [])
        hot_symbols = [s.get("symbol") for s in hot_stocks]
        
        assert "MRVL" not in hot_symbols, f"MRVL should NOT be in hot category, but found in: {hot_symbols[:10]}"
        print(f"PASS: MRVL not in hot category (hot has {len(hot_stocks)} stocks)")
    
    def test_mrvl_not_in_bullish_category(self):
        """MRVL should NOT be in 'bullish' category due to -76% upside"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        bullish_stocks = data.get("bullish", [])
        bullish_symbols = [s.get("symbol") for s in bullish_stocks]
        
        assert "MRVL" not in bullish_symbols, f"MRVL should NOT be in bullish category"
        print(f"PASS: MRVL not in bullish category (bullish has {len(bullish_stocks)} stocks)")
    
    def test_mrvl_in_overpriced_category(self):
        """MRVL should be in 'overpriced' category with 'Hold' signal"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        overpriced_stocks = data.get("overpriced", [])
        
        # Find MRVL in overpriced
        mrvl = None
        for stock in overpriced_stocks:
            if stock.get("symbol") == "MRVL":
                mrvl = stock
                break
        
        assert mrvl is not None, f"MRVL should be in overpriced category. Overpriced has {len(overpriced_stocks)} stocks"
        assert mrvl.get("signal") in ("Hold", "Sell"), f"MRVL signal should be Hold/Sell, got: {mrvl.get('signal')}"
        print(f"PASS: MRVL in overpriced category with signal={mrvl.get('signal')}")
    
    def test_hot_stocks_have_reasonable_upside(self):
        """Hot stocks should NOT have deeply negative upside (< -25%)"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        hot_stocks = data.get("hot", [])
        
        overvalued_in_hot = []
        for stock in hot_stocks:
            val_summary = stock.get("valuation_summary", {}) or {}
            upside_str = val_summary.get("upside_potential", "") or stock.get("upside_potential", "")
            if upside_str:
                try:
                    upside_val = float(str(upside_str).replace("%", "").replace("+", ""))
                    if upside_val < -25:
                        overvalued_in_hot.append({
                            "symbol": stock.get("symbol"),
                            "upside": upside_val,
                            "signal": stock.get("signal")
                        })
                except (ValueError, TypeError):
                    pass
        
        assert len(overvalued_in_hot) == 0, f"Found {len(overvalued_in_hot)} overvalued stocks in hot: {overvalued_in_hot[:5]}"
        print(f"PASS: No overvalued stocks (upside < -25%) in hot category ({len(hot_stocks)} hot stocks)")
    
    def test_bullish_stocks_have_reasonable_upside(self):
        """Bullish stocks should NOT have deeply negative upside (< -25%)"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        bullish_stocks = data.get("bullish", [])
        
        overvalued_in_bullish = []
        for stock in bullish_stocks:
            val_summary = stock.get("valuation_summary", {}) or {}
            upside_str = val_summary.get("upside_potential", "") or stock.get("upside_potential", "")
            if upside_str:
                try:
                    upside_val = float(str(upside_str).replace("%", "").replace("+", ""))
                    if upside_val < -25:
                        overvalued_in_bullish.append({
                            "symbol": stock.get("symbol"),
                            "upside": upside_val,
                            "signal": stock.get("signal")
                        })
                except (ValueError, TypeError):
                    pass
        
        assert len(overvalued_in_bullish) == 0, f"Found {len(overvalued_in_bullish)} overvalued stocks in bullish: {overvalued_in_bullish[:5]}"
        print(f"PASS: No overvalued stocks (upside < -25%) in bullish category ({len(bullish_stocks)} bullish stocks)")
    
    def test_overpriced_category_exists_and_populated(self):
        """Overpriced category should exist and have stocks"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        overpriced_stocks = data.get("overpriced", [])
        
        assert len(overpriced_stocks) > 0, "Overpriced category should have stocks"
        print(f"PASS: Overpriced category has {len(overpriced_stocks)} stocks")
        
        # Check that overpriced stocks have Hold/Sell signals
        for stock in overpriced_stocks[:10]:
            signal = stock.get("signal")
            assert signal in ("Hold", "Sell", None), f"Overpriced stock {stock.get('symbol')} has unexpected signal: {signal}"
    
    def test_mrvl_price_integrity(self):
        """MRVL price integrity check - should show correct price ~$87"""
        response = requests.get(f"{BASE_URL}/api/debug/price_integrity/MRVL", headers=self.headers)
        assert response.status_code == 200, f"Price integrity check failed: {response.text}"
        
        data = response.json()
        # Price is nested under 'validated' object
        validated = data.get("validated", {})
        price = validated.get("price", 0)
        
        # MRVL should be around $87 (not $94 entry price)
        assert 70 < price < 110, f"MRVL price should be ~$87, got: {price}"
        assert validated.get("stale") == False, f"MRVL should not be stale"
        assert data.get("mismatch") == False, f"MRVL should have no price mismatch"
        print(f"PASS: MRVL price integrity OK - price=${price}, source={validated.get('source')}")


class TestEntryStatusClassification:
    """Tests for entry_status classification including STALE_SETUP and BLOWN_STOP"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for API calls"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": "Bullishalmarkhan7.7"})
        assert response.status_code == 200
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_auto_trade_scan_has_entry_status(self):
        """All candidates should have entry_status field"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=self.headers)
        assert response.status_code == 200, f"Auto trade scan failed: {response.text}"
        
        data = response.json()
        candidates = data.get("candidates", [])
        
        valid_statuses = {"TRADE_NOW", "WATCHLIST", "MISSED", "STALE_SETUP", "BLOWN_STOP", "NO_LEVELS", "UNKNOWN"}
        
        missing_status = []
        invalid_status = []
        for c in candidates:
            status = c.get("entry_status")
            if not status:
                missing_status.append(c.get("symbol"))
            elif status not in valid_statuses:
                invalid_status.append({"symbol": c.get("symbol"), "status": status})
        
        assert len(missing_status) == 0, f"Candidates missing entry_status: {missing_status[:10]}"
        assert len(invalid_status) == 0, f"Candidates with invalid entry_status: {invalid_status[:10]}"
        print(f"PASS: All {len(candidates)} candidates have valid entry_status")
    
    def test_auto_trade_scan_has_price_data(self):
        """All candidates should have price_data block"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        candidates = data.get("candidates", [])
        
        missing_price_data = []
        for c in candidates:
            price_data = c.get("price_data")
            if not price_data:
                missing_price_data.append(c.get("symbol"))
            else:
                # Check required fields
                if "price" not in price_data or "source" not in price_data:
                    missing_price_data.append(c.get("symbol"))
        
        assert len(missing_price_data) == 0, f"Candidates missing price_data: {missing_price_data[:10]}"
        print(f"PASS: All {len(candidates)} candidates have price_data block")
    
    def test_entry_status_distribution(self):
        """Check distribution of entry_status values (may be empty if market closed)"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        candidates = data.get("candidates", [])
        
        # Market may be closed, so 0 candidates is acceptable
        if len(candidates) == 0:
            print(f"PASS: No candidates (market likely closed) - entry_status check skipped")
            return
        
        status_counts = {}
        for c in candidates:
            status = c.get("entry_status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"Entry status distribution: {status_counts}")
        
        # At least some status types should be present when candidates exist
        assert len(status_counts) > 0, "Should have at least one entry_status type"


class TestTickerMappings:
    """Tests for ticker mappings endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for API calls"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": "Bullishalmarkhan7.7"})
        assert response.status_code == 200
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_ticker_mappings_returns_known_renames(self):
        """Should return 14 known renames"""
        response = requests.get(f"{BASE_URL}/api/debug/ticker_mappings", headers=self.headers)
        assert response.status_code == 200, f"Ticker mappings failed: {response.text}"
        
        data = response.json()
        ticker_mappings = data.get("ticker_mappings", {})
        
        assert len(ticker_mappings) >= 14, f"Expected 14+ known renames, got {len(ticker_mappings)}"
        print(f"PASS: {len(ticker_mappings)} known renames (expected 14+)")
    
    def test_ticker_mappings_returns_dead_tickers(self):
        """Should return 165+ dead tickers"""
        response = requests.get(f"{BASE_URL}/api/debug/ticker_mappings", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        dead_tickers = data.get("dead_tickers", [])
        
        assert len(dead_tickers) >= 165, f"Expected 165+ dead tickers, got {len(dead_tickers)}"
        print(f"PASS: {len(dead_tickers)} dead tickers (expected 165+)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
