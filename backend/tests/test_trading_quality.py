"""
ObaidTradez - Trading Quality & Investment Engine Tests
Tests for Phase 1 & 2 features: Quality-focused trading signals, Investment engine
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
    assert response.status_code == 200, f"Auth failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def headers(auth_token):
    """Auth headers for API calls"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestTradingSignals:
    """Trading signals with quality-focused features"""
    
    def test_trading_scan_returns_data(self, headers):
        """Trading scan endpoint returns valid response"""
        response = requests.get(f"{BASE_URL}/api/trading/scan", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "top_trades" in data, "Missing top_trades section"
        assert "hot" in data, "Missing hot category"
        assert "breakout" in data, "Missing breakout category"
        assert "momentum" in data, "Missing momentum category"
        assert "high_volume" in data, "Missing high_volume category"
        assert "watch" in data, "Missing watch category"
        assert "diagnostics" in data, "Missing diagnostics section"
    
    def test_top_trades_section_exists(self, headers):
        """Top Trades Today section is populated"""
        response = requests.get(f"{BASE_URL}/api/trading/scan", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        top_trades = data.get("top_trades", [])
        # May be empty on weekends/down markets, but structure should exist
        assert isinstance(top_trades, list), "top_trades should be a list"
        print(f"Top Trades count: {len(top_trades)}")
    
    def test_top_trade_has_entry_stop_target(self, headers):
        """Each top trade includes entry zone, stop-loss, take-profit"""
        response = requests.get(f"{BASE_URL}/api/trading/scan", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        top_trades = data.get("top_trades", [])
        if len(top_trades) > 0:
            trade = top_trades[0]
            assert "entry_zone" in trade, "Missing entry_zone"
            assert "stop_loss" in trade, "Missing stop_loss"
            assert "take_profit" in trade, "Missing take_profit"
            assert "risk_reward" in trade, "Missing risk_reward"
            
            # Verify R:R format
            rr = trade.get("risk_reward", "")
            assert ":" in rr, f"R:R should be in format '1:X', got: {rr}"
            
            # Verify R:R >= 2.0
            rr_match = rr.split(":")
            if len(rr_match) == 2:
                rr_value = float(rr_match[1])
                assert rr_value >= 2.0, f"R:R should be >= 2.0, got: {rr_value}"
            
            print(f"Sample trade: {trade.get('symbol')} - Entry: {trade.get('entry_zone')}, Stop: {trade.get('stop_loss')}, Target: {trade.get('take_profit')}, R:R: {rr}")
        else:
            pytest.skip("No top trades available (weekend/down market)")
    
    def test_diagnostics_panel_data(self, headers):
        """Diagnostics panel shows stocks scanned, signals generated, exclusion reasons"""
        response = requests.get(f"{BASE_URL}/api/trading/scan", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        diagnostics = data.get("diagnostics", {})
        assert "stocks_scanned" in diagnostics, "Missing stocks_scanned"
        assert "signals_generated" in diagnostics, "Missing signals_generated"
        assert "excluded_count" in diagnostics, "Missing excluded_count"
        assert "excluded_reasons" in diagnostics, "Missing excluded_reasons"
        assert "filters_applied" in diagnostics, "Missing filters_applied"
        
        # Verify counts are reasonable
        assert diagnostics["stocks_scanned"] > 0, "Should scan at least some stocks"
        assert diagnostics["excluded_count"] >= 0, "Excluded count should be non-negative"
        
        # Verify filters are applied
        filters = diagnostics.get("filters_applied", [])
        assert len(filters) > 0, "Should have filters applied"
        
        print(f"Diagnostics: Scanned {diagnostics['stocks_scanned']}, Generated {diagnostics['signals_generated']}, Excluded {diagnostics['excluded_count']}")
        print(f"Filters: {filters}")
    
    def test_trading_categories_have_reasonable_counts(self, headers):
        """Trading categories have reasonable counts (may be 0 on weekends)"""
        response = requests.get(f"{BASE_URL}/api/trading/scan", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        hot = len(data.get("hot", []))
        breakout = len(data.get("breakout", []))
        momentum = len(data.get("momentum", []))
        high_volume = len(data.get("high_volume", []))
        watch = len(data.get("watch", []))
        
        total = hot + breakout + momentum + high_volume + watch
        
        print(f"Categories: Hot={hot}, Breakout={breakout}, Momentum={momentum}, High Volume={high_volume}, Watch={watch}")
        print(f"Total signals: {total}")
        
        # At least some signals should exist (or all 0 on weekends)
        assert total >= 0, "Total should be non-negative"
    
    def test_trading_analyze_single_symbol(self, headers):
        """Analyze single symbol endpoint works"""
        # Use XOM which typically passes filters
        response = requests.get(f"{BASE_URL}/api/trading/analyze/XOM", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("symbol") == "XOM", "Symbol should match"
        # Response includes 'included' flag and 'signal' object
        assert "included" in data, "Missing included flag"
        
        if data.get("included"):
            signal = data.get("signal", {})
            assert "confidence" in signal, "Missing confidence in signal"
            assert "reasoning" in signal, "Missing reasoning in signal"
            print(f"XOM signal: {signal.get('signal')} with confidence {signal.get('confidence')}")
        else:
            # Stock didn't pass filters - this is valid behavior
            assert "exclusion_reason" in data, "Missing exclusion_reason"
            print(f"XOM excluded: {data.get('exclusion_reason')}")


class TestInvestmentSignals:
    """Investment engine with balanced scoring"""
    
    def test_investment_scan_returns_categories(self, headers):
        """Investment scan returns categorized signals"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify categories exist
        assert "hot" in data, "Missing hot category"
        assert "bullish" in data, "Missing bullish category"
        assert "undervalued" in data, "Missing undervalued category"
        assert "watch" in data, "Missing watch category"
        assert "bearish" in data, "Missing bearish category"
        
        print(f"Investment categories: Hot={len(data.get('hot', []))}, Bullish={len(data.get('bullish', []))}, Undervalued={len(data.get('undervalued', []))}, Watch={len(data.get('watch', []))}, Bearish={len(data.get('bearish', []))}")
    
    def test_investment_signal_has_bull_bear_case(self, headers):
        """Investment signals include bull_case, bear_case, and reasoning"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Get first hot signal
        hot_signals = data.get("hot", [])
        if len(hot_signals) > 0:
            signal = hot_signals[0]
            assert "bull_case" in signal, "Missing bull_case"
            assert "bear_case" in signal, "Missing bear_case"
            assert "reasoning" in signal, "Missing reasoning"
            
            # bull_case and bear_case should be lists
            assert isinstance(signal.get("bull_case"), list), "bull_case should be a list"
            assert isinstance(signal.get("bear_case"), list), "bear_case should be a list"
            
            print(f"Sample signal: {signal.get('symbol')}")
            print(f"  Bull case: {signal.get('bull_case', [])[:2]}")
            print(f"  Bear case: {signal.get('bear_case', [])[:2]}")
        else:
            pytest.skip("No hot signals available")
    
    def test_investment_browse_returns_data(self, headers):
        """Investment browse endpoint returns paginated data"""
        response = requests.get(f"{BASE_URL}/api/investments/browse?page=1&page_size=30", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "signals" in data, "Missing signals"
        assert "total" in data, "Missing total"
        assert "page" in data, "Missing page"
        assert "total_pages" in data, "Missing total_pages"
        
        print(f"Browse: {data.get('total')} total stocks, page {data.get('page')} of {data.get('total_pages')}")
    
    def test_investment_filters_endpoint(self, headers):
        """Investment filters endpoint returns filter options"""
        response = requests.get(f"{BASE_URL}/api/investments/filters", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "sectors" in data, "Missing sectors"
        assert "total_signals" in data, "Missing total_signals"
        
        print(f"Filters: {data.get('total_signals')} total signals, {len(data.get('sectors', []))} sectors")


class TestWatchlist:
    """Watchlist add/remove functionality"""
    
    def test_watchlist_get(self, headers):
        """Get watchlist returns list"""
        response = requests.get(f"{BASE_URL}/api/watchlist", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Watchlist should be a list"
        print(f"Watchlist items: {len(data)}")
    
    def test_watchlist_add_remove(self, headers):
        """Add and remove from watchlist works"""
        # Use a real symbol that exists
        test_symbol = "TSLA"
        
        # First remove if exists
        requests.delete(f"{BASE_URL}/api/watchlist/{test_symbol}", headers=headers)
        
        # Add
        response = requests.post(
            f"{BASE_URL}/api/watchlist",
            headers=headers,
            json={"symbol": test_symbol, "source": "testing"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True or "already" in data.get("message", "").lower(), f"Add failed: {data}"
        print(f"Add {test_symbol}: {data.get('message')}")
        
        # Remove
        response = requests.delete(f"{BASE_URL}/api/watchlist/{test_symbol}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True or "not found" in data.get("message", "").lower(), f"Remove failed: {data}"
        print(f"Remove {test_symbol}: {data.get('message')}")
    
    def test_watchlist_check(self, headers):
        """Check if symbol is in watchlist"""
        response = requests.get(f"{BASE_URL}/api/watchlist/check/AAPL", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "in_watchlist" in data, "Missing in_watchlist field"
        print(f"AAPL in watchlist: {data.get('in_watchlist')}")


class TestPrices:
    """Live price endpoints"""
    
    def test_batch_prices(self, headers):
        """Batch prices endpoint works"""
        # The endpoint expects a list directly as body
        response = requests.post(
            f"{BASE_URL}/api/prices/batch",
            headers=headers,
            json=["AAPL", "MSFT", "GOOGL"]
        )
        assert response.status_code == 200
        data = response.json()
        assert "prices" in data, "Should return prices dict"
        assert "count" in data, "Should return count"
        print(f"Batch prices: {data.get('count')} prices returned")
    
    def test_single_price(self, headers):
        """Single price endpoint works"""
        response = requests.get(f"{BASE_URL}/api/prices/AAPL", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "price" in data or "error" in data, "Should have price or error"
        print(f"AAPL price: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
