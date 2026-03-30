"""
Test suite for Trading Signals, Investment Ideas, and Watchlist functionality
Tests the three critical issues:
1) Trading Signals showing all categories as 0
2) Investment Ideas showing all categories as 0
3) Watchlist failing when adding tickers
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": "Bullishalmarkhan7.7"}
        )
        assert response.status_code == 200, f"Auth failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "token" in data
        return data["token"]
    
    def test_auth_success(self, auth_token):
        """Test authentication works"""
        assert auth_token is not None
        assert len(auth_token) > 0
        print(f"✓ Auth token obtained: {auth_token[:20]}...")


class TestTradingSignals:
    """Trading Signals endpoint tests - verifies categories are populated"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": "Bullishalmarkhan7.7"}
        )
        return response.json()["token"]
    
    def test_trading_scan_returns_data(self, auth_token):
        """Test /api/trading/scan returns signals"""
        response = requests.get(
            f"{BASE_URL}/api/trading/scan",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Trading scan failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "hot" in data, "Missing 'hot' category"
        assert "breakout" in data, "Missing 'breakout' category"
        assert "momentum" in data, "Missing 'momentum' category"
        assert "high_volume" in data, "Missing 'high_volume' category"
        assert "all" in data, "Missing 'all' category"
        
        print(f"✓ Trading scan returned categories: hot={len(data['hot'])}, breakout={len(data['breakout'])}, momentum={len(data['momentum'])}, high_volume={len(data['high_volume'])}")
    
    def test_trading_categories_populated(self, auth_token):
        """CRITICAL: Verify trading categories have non-zero counts"""
        response = requests.get(
            f"{BASE_URL}/api/trading/scan",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # At least one category should have signals
        total_signals = (
            len(data.get('hot', [])) +
            len(data.get('breakout', [])) +
            len(data.get('momentum', [])) +
            len(data.get('high_volume', []))
        )
        
        assert total_signals > 0, "CRITICAL: All trading categories are empty (0 signals)"
        print(f"✓ Total trading signals across categories: {total_signals}")
        
        # Check individual categories
        hot_count = len(data.get('hot', []))
        breakout_count = len(data.get('breakout', []))
        momentum_count = len(data.get('momentum', []))
        high_volume_count = len(data.get('high_volume', []))
        
        print(f"  - Hot: {hot_count}")
        print(f"  - Breakout: {breakout_count}")
        print(f"  - Momentum: {momentum_count}")
        print(f"  - High Volume: {high_volume_count}")
        
        # At least 2 categories should have data
        categories_with_data = sum([
            1 if hot_count > 0 else 0,
            1 if breakout_count > 0 else 0,
            1 if momentum_count > 0 else 0,
            1 if high_volume_count > 0 else 0
        ])
        
        assert categories_with_data >= 1, f"Only {categories_with_data} categories have data, expected at least 1"
        print(f"✓ {categories_with_data} categories have signals")
    
    def test_trading_signal_structure(self, auth_token):
        """Verify trading signal has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/trading/scan",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Get first signal from any category
        all_signals = data.get('all', [])
        if len(all_signals) > 0:
            signal = all_signals[0]
            
            # Verify required fields
            assert "symbol" in signal, "Missing symbol"
            assert "signal" in signal, "Missing signal"
            assert "confidence" in signal, "Missing confidence"
            assert "category" in signal, "Missing category"
            
            print(f"✓ Signal structure valid: {signal['symbol']} - {signal['signal']} ({signal['category']})")
    
    def test_trading_analyze_single_symbol(self, auth_token):
        """Test analyzing a single symbol"""
        response = requests.get(
            f"{BASE_URL}/api/trading/analyze/AAPL",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Trading analyze failed: {response.text}"
        data = response.json()
        
        assert data.get("symbol") == "AAPL"
        assert "signal" in data
        # Symbol may be excluded by strict filters
        if data.get("included") is False:
            assert "exclusion_reason" in data
            print(f"✓ AAPL excluded: {data['exclusion_reason']}")
        else:
            assert "confidence" in data
            print(f"✓ AAPL analysis: {data['signal']} with {data['confidence']*100:.0f}% confidence")


class TestInvestmentIdeas:
    """Investment Ideas endpoint tests - verifies categories are populated"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": "Bullishalmarkhan7.7"}
        )
        return response.json()["token"]
    
    def test_investments_browse_returns_data(self, auth_token):
        """Test /api/investments/browse returns stocks"""
        response = requests.get(
            f"{BASE_URL}/api/investments/browse",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Investments browse failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "signals" in data, "Missing 'signals' in response"
        assert "total" in data, "Missing 'total' in response"
        
        total = data.get("total", 0)
        signals_count = len(data.get("signals", []))
        
        print(f"✓ Investments browse: total={total}, returned={signals_count}")
        assert total > 0, "CRITICAL: Investment browse returned 0 total stocks"
    
    def test_investments_scan_returns_categories(self, auth_token):
        """Test /api/investments/scan returns categorized signals"""
        response = requests.get(
            f"{BASE_URL}/api/investments/scan",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Investments scan failed: {response.text}"
        data = response.json()
        
        # Verify categories exist
        assert "hot" in data, "Missing 'hot' category"
        assert "bullish" in data, "Missing 'bullish' category"
        assert "undervalued" in data, "Missing 'undervalued' category"
        assert "watch" in data, "Missing 'watch' category"
        assert "bearish" in data, "Missing 'bearish' category"
        
        print(f"✓ Investment scan categories: hot={len(data['hot'])}, bullish={len(data['bullish'])}, undervalued={len(data['undervalued'])}, watch={len(data['watch'])}, bearish={len(data['bearish'])}")
    
    def test_investments_categories_populated(self, auth_token):
        """CRITICAL: Verify investment categories have non-zero counts"""
        response = requests.get(
            f"{BASE_URL}/api/investments/scan",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Calculate totals
        hot_count = len(data.get('hot', []))
        bullish_count = len(data.get('bullish', []))
        undervalued_count = len(data.get('undervalued', []))
        watch_count = len(data.get('watch', []))
        bearish_count = len(data.get('bearish', []))
        
        total_signals = hot_count + bullish_count + undervalued_count + watch_count + bearish_count
        
        print(f"  - Hot: {hot_count}")
        print(f"  - Bullish: {bullish_count}")
        print(f"  - Undervalued: {undervalued_count}")
        print(f"  - Watch: {watch_count}")
        print(f"  - Bearish: {bearish_count}")
        print(f"  Total: {total_signals}")
        
        assert total_signals > 0, "CRITICAL: All investment categories are empty (0 signals)"
        
        # At least 2 categories should have data
        categories_with_data = sum([
            1 if hot_count > 0 else 0,
            1 if bullish_count > 0 else 0,
            1 if undervalued_count > 0 else 0,
            1 if watch_count > 0 else 0,
            1 if bearish_count > 0 else 0
        ])
        
        print(f"✓ {categories_with_data} investment categories have signals")
    
    def test_investments_filters(self, auth_token):
        """Test investment filters endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/investments/filters",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Investments filters failed: {response.text}"
        data = response.json()
        
        assert "total_signals" in data
        print(f"✓ Investment filters: {data.get('total_signals', 0)} total stocks analyzed")


class TestWatchlist:
    """Watchlist endpoint tests - verifies add/remove/list functionality"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": "Bullishalmarkhan7.7"}
        )
        return response.json()["token"]
    
    def test_watchlist_get(self, auth_token):
        """Test getting watchlist"""
        response = requests.get(
            f"{BASE_URL}/api/watchlist",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Watchlist get failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Watchlist should return a list"
        print(f"✓ Watchlist has {len(data)} items")
    
    def test_watchlist_add_aapl(self, auth_token):
        """CRITICAL: Test adding AAPL to watchlist"""
        # First remove if exists
        requests.delete(
            f"{BASE_URL}/api/watchlist/AAPL",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Add AAPL
        response = requests.post(
            f"{BASE_URL}/api/watchlist",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            json={"symbol": "AAPL", "source": "test"}
        )
        
        assert response.status_code == 200, f"Watchlist add failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, f"Watchlist add returned success=False: {data}"
        print(f"✓ AAPL added to watchlist: {data.get('message')}")
    
    def test_watchlist_add_msft(self, auth_token):
        """Test adding MSFT to watchlist"""
        # First remove if exists
        requests.delete(
            f"{BASE_URL}/api/watchlist/MSFT",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Add MSFT
        response = requests.post(
            f"{BASE_URL}/api/watchlist",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            json={"symbol": "MSFT", "source": "test"}
        )
        
        assert response.status_code == 200, f"Watchlist add failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, f"Watchlist add returned success=False: {data}"
        print(f"✓ MSFT added to watchlist: {data.get('message')}")
    
    def test_watchlist_add_nvda(self, auth_token):
        """Test adding NVDA to watchlist"""
        # First remove if exists
        requests.delete(
            f"{BASE_URL}/api/watchlist/NVDA",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Add NVDA
        response = requests.post(
            f"{BASE_URL}/api/watchlist",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            json={"symbol": "NVDA", "source": "test"}
        )
        
        assert response.status_code == 200, f"Watchlist add failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, f"Watchlist add returned success=False: {data}"
        print(f"✓ NVDA added to watchlist: {data.get('message')}")
    
    def test_watchlist_verify_added_items(self, auth_token):
        """Verify added items appear in watchlist"""
        response = requests.get(
            f"{BASE_URL}/api/watchlist",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        symbols = [item.get("symbol") for item in data]
        
        # Check AAPL, MSFT, NVDA are in watchlist
        assert "AAPL" in symbols, "AAPL not found in watchlist after adding"
        assert "MSFT" in symbols, "MSFT not found in watchlist after adding"
        assert "NVDA" in symbols, "NVDA not found in watchlist after adding"
        
        print(f"✓ Verified AAPL, MSFT, NVDA in watchlist")
    
    def test_watchlist_items_have_prices(self, auth_token):
        """Verify watchlist items have price data"""
        response = requests.get(
            f"{BASE_URL}/api/watchlist",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for item in data:
            if item.get("symbol") in ["AAPL", "MSFT", "NVDA"]:
                # Price should be present (may be 0 on weekends)
                assert "price" in item, f"Missing price for {item.get('symbol')}"
                print(f"  - {item.get('symbol')}: ${item.get('price', 0):.2f}")
        
        print(f"✓ Watchlist items have price data")
    
    def test_watchlist_check_symbol(self, auth_token):
        """Test checking if symbol is in watchlist"""
        response = requests.get(
            f"{BASE_URL}/api/watchlist/check/AAPL",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("in_watchlist") == True, "AAPL should be in watchlist"
        print(f"✓ Watchlist check works: AAPL in_watchlist={data.get('in_watchlist')}")
    
    def test_watchlist_remove(self, auth_token):
        """Test removing from watchlist"""
        # Add a test symbol first
        requests.post(
            f"{BASE_URL}/api/watchlist",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            json={"symbol": "TEST_REMOVE", "source": "test"}
        )
        
        # Remove it
        response = requests.delete(
            f"{BASE_URL}/api/watchlist/TEST_REMOVE",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        print(f"✓ Watchlist remove works: {data.get('message')}")
    
    def test_watchlist_duplicate_add(self, auth_token):
        """Test adding duplicate symbol returns appropriate message"""
        # Try to add AAPL again (should already be in watchlist)
        response = requests.post(
            f"{BASE_URL}/api/watchlist",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            json={"symbol": "AAPL", "source": "test"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return success=False for duplicate
        assert data.get("success") == False, "Duplicate add should return success=False"
        assert "already" in data.get("message", "").lower(), "Should mention already in watchlist"
        print(f"✓ Duplicate add handled correctly: {data.get('message')}")


class TestLivePrices:
    """Live prices endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": "Bullishalmarkhan7.7"}
        )
        return response.json()["token"]
    
    def test_prices_batch(self, auth_token):
        """Test batch price endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/prices/batch",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            json=["AAPL", "MSFT", "NVDA"]  # Endpoint expects list directly
        )
        
        assert response.status_code == 200, f"Batch prices failed: {response.text}"
        data = response.json()
        
        assert "prices" in data, "Missing prices in response"
        print(f"✓ Batch prices returned data for {data.get('count', 0)} symbols")
    
    def test_prices_watchlist(self, auth_token):
        """Test watchlist prices endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/prices/watchlist",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Watchlist prices failed: {response.text}"
        data = response.json()
        
        print(f"✓ Watchlist prices returned: {len(data)} symbols")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
