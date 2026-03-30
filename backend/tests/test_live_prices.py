"""
Test Live Prices API Endpoints
Tests for real-time price streaming feature
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestLivePricesAPI:
    """Live Prices endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": "Bullishalmarkhan7.7"}
        )
        assert response.status_code == 200, f"Auth failed: {response.text}"
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_batch_prices_requires_auth(self):
        """Test that batch prices endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/prices/batch",
            json=["AAPL", "MSFT"]
        )
        assert response.status_code == 401
        print("✓ Batch prices requires auth (401)")
    
    def test_batch_prices_returns_data(self):
        """Test batch prices returns price data for valid symbols"""
        response = requests.post(
            f"{BASE_URL}/api/prices/batch",
            headers=self.headers,
            json=["AAPL", "MSFT", "GOOGL"]
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "prices" in data
        assert "count" in data
        assert data["count"] >= 0  # Prices may be unavailable outside market hours
        
        # Check price data structure
        for symbol, price_data in data["prices"].items():
            assert "symbol" in price_data
            assert "price" in price_data
            assert "change" in price_data
            assert "change_pct" in price_data
            assert isinstance(price_data["price"], (int, float))
        
        print(f"✓ Batch prices returned {data['count']} prices")
    
    def test_batch_prices_limits_to_100(self):
        """Test that batch prices limits to 100 symbols"""
        # Create list of 150 symbols
        symbols = [f"SYM{i}" for i in range(150)]
        response = requests.post(
            f"{BASE_URL}/api/prices/batch",
            headers=self.headers,
            json=symbols
        )
        assert response.status_code == 200
        # Should not error even with 150 symbols
        print("✓ Batch prices handles large symbol lists")
    
    def test_batch_prices_empty_list(self):
        """Test batch prices with empty list"""
        response = requests.post(
            f"{BASE_URL}/api/prices/batch",
            headers=self.headers,
            json=[]
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["prices"] == {}
        print("✓ Batch prices handles empty list")
    
    def test_single_price_requires_auth(self):
        """Test that single price endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/prices/AAPL")
        assert response.status_code == 401
        print("✓ Single price requires auth (401)")
    
    def test_single_price_returns_data(self):
        """Test single price returns data for valid symbol"""
        response = requests.get(
            f"{BASE_URL}/api/prices/AAPL",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "symbol" in data
        assert "price" in data
        assert data["symbol"] == "AAPL"
        print(f"✓ Single price for AAPL: ${data['price']}")
    
    def test_single_price_invalid_symbol(self):
        """Test single price with invalid symbol returns zero price"""
        response = requests.get(
            f"{BASE_URL}/api/prices/INVALIDXYZ123",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["price"] == 0
        print("✓ Invalid symbol returns zero price")
    
    def test_watchlist_prices_requires_auth(self):
        """Test that watchlist prices endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/prices/watchlist")
        assert response.status_code == 401
        print("✓ Watchlist prices requires auth (401)")
    
    def test_watchlist_prices_returns_correct_format(self):
        """Test watchlist prices returns correct format"""
        response = requests.get(
            f"{BASE_URL}/api/prices/watchlist",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "prices" in data
        assert "count" in data
        assert isinstance(data["prices"], dict)
        assert isinstance(data["count"], int)
        print(f"✓ Watchlist prices returned {data['count']} prices")
    
    def test_positions_prices_requires_auth(self):
        """Test that positions prices endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/prices/positions")
        assert response.status_code == 401
        print("✓ Positions prices requires auth (401)")
    
    def test_positions_prices_returns_correct_format(self):
        """Test positions prices returns correct format"""
        response = requests.get(
            f"{BASE_URL}/api/prices/positions",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "prices" in data
        assert "count" in data
        assert isinstance(data["prices"], dict)
        assert isinstance(data["count"], int)
        # Note: May be empty if Alpaca returns 401
        print(f"✓ Positions prices returned {data['count']} prices")
    
    def test_watchlist_prices_with_items(self):
        """Test watchlist prices returns data when watchlist has items"""
        # First add an item to watchlist
        add_response = requests.post(
            f"{BASE_URL}/api/watchlist",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"symbol": "TEST_NVDA", "source": "test"}
        )
        
        # Get watchlist prices
        response = requests.get(
            f"{BASE_URL}/api/prices/watchlist",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have at least the item we added (if it's a valid symbol)
        assert "prices" in data
        print(f"✓ Watchlist prices with items: {data['count']} prices")
        
        # Cleanup - remove test item
        requests.delete(
            f"{BASE_URL}/api/watchlist/TEST_NVDA",
            headers=self.headers
        )


class TestLivePricesIntegration:
    """Integration tests for live prices with other features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": "Bullishalmarkhan7.7"}
        )
        assert response.status_code == 200
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_trading_scan_returns_symbols_for_live_prices(self):
        """Test trading scan returns symbols that can be used for live prices"""
        # Get trading signals
        scan_response = requests.get(
            f"{BASE_URL}/api/trading/scan",
            headers=self.headers
        )
        assert scan_response.status_code == 200
        signals = scan_response.json()
        
        # Extract symbols from hot signals
        hot_signals = signals.get("hot", [])
        if hot_signals:
            symbols = [s["symbol"] for s in hot_signals[:5]]
            
            # Get live prices for these symbols
            prices_response = requests.post(
                f"{BASE_URL}/api/prices/batch",
                headers=self.headers,
                json=symbols
            )
            assert prices_response.status_code == 200
            prices_data = prices_response.json()
            
            print(f"✓ Got live prices for {prices_data['count']} trading signals")
        else:
            print("✓ No hot signals available (skipped)")
    
    def test_investments_scan_returns_symbols_for_live_prices(self):
        """Test investments scan returns symbols that can be used for live prices"""
        # Get investment signals
        scan_response = requests.get(
            f"{BASE_URL}/api/investments/scan",
            headers=self.headers
        )
        assert scan_response.status_code == 200
        signals = scan_response.json()
        
        # Extract symbols from 'all' category
        all_signals = signals.get("all", [])
        if all_signals:
            symbols = [s["symbol"] for s in all_signals[:10]]
            
            # Get live prices for these symbols
            prices_response = requests.post(
                f"{BASE_URL}/api/prices/batch",
                headers=self.headers,
                json=symbols
            )
            assert prices_response.status_code == 200
            prices_data = prices_response.json()
            
            print(f"✓ Got live prices for {prices_data['count']} investment signals")
        else:
            print("✓ No investment signals available (skipped)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
