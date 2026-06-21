"""
Test suite for ObaidTradez Watchlist API
Tests: CRUD operations, persistence, refresh, notes, and bulk operations
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8000')
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
    assert data["success"], f"Auth not successful: {data}"
    return data["token"]


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


@pytest.fixture(autouse=True)
def cleanup_test_stocks(api_client):
    """Clean up test stocks before and after each test"""
    test_symbols = ["TEST_AAPL", "TEST_MSFT", "TEST_GOOGL", "AAPL", "MSFT", "GOOGL", "NVDA"]
    
    # Cleanup before test
    for symbol in test_symbols:
        try:
            api_client.delete(f"{BASE_URL}/api/watchlist/{symbol}")
        except:
            pass
    
    yield
    
    # Cleanup after test
    for symbol in test_symbols:
        try:
            api_client.delete(f"{BASE_URL}/api/watchlist/{symbol}")
        except:
            pass


class TestWatchlistAPI:
    """Watchlist API endpoint tests"""
    
    def test_get_empty_watchlist(self, api_client):
        """Test getting watchlist when empty"""
        # First clear all
        api_client.delete(f"{BASE_URL}/api/watchlist/all")
        
        response = api_client.get(f"{BASE_URL}/api/watchlist")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Empty watchlist returns list: {len(data)} items")
    
    def test_add_stock_to_watchlist(self, api_client):
        """Test adding a stock to watchlist"""
        response = api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "AAPL", "source": "manual"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "AAPL" in data["message"]
        assert data["item"]["symbol"] == "AAPL"
        assert data["item"]["source"] == "manual"
        assert "id" in data["item"]
        assert "added_at" in data["item"]
        print(f"✓ Added AAPL to watchlist: {data['message']}")
    
    def test_add_duplicate_stock(self, api_client):
        """Test adding duplicate stock returns error"""
        # First add
        api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "MSFT", "source": "manual"}
        )
        
        # Try to add again
        response = api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "MSFT", "source": "manual"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == False
        assert "already in your watchlist" in data["message"]
        print(f"✓ Duplicate prevention works: {data['message']}")
    
    def test_add_invalid_stock(self, api_client):
        """Test adding invalid stock symbol"""
        response = api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "INVALIDXYZ123", "source": "manual"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == False
        assert "Could not find stock" in data["message"]
        print(f"✓ Invalid stock rejected: {data['message']}")
    
    def test_add_stock_from_trading(self, api_client):
        """Test adding stock with trading source"""
        response = api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "NVDA", "source": "trading"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["item"]["source"] == "trading"
        print(f"✓ Added NVDA from trading source")
    
    def test_add_stock_from_investments(self, api_client):
        """Test adding stock with investments source"""
        response = api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "GOOGL", "source": "investments"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["item"]["source"] == "investments"
        print(f"✓ Added GOOGL from investments source")
    
    def test_get_watchlist_with_items(self, api_client):
        """Test getting watchlist with items - verify enriched data"""
        # Add a stock first
        api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "AAPL", "source": "manual"}
        )
        
        response = api_client.get(f"{BASE_URL}/api/watchlist")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Find AAPL in the list
        aapl_item = next((item for item in data if item["symbol"] == "AAPL"), None)
        assert aapl_item is not None
        
        # Verify enriched fields
        assert "id" in aapl_item
        assert "symbol" in aapl_item
        assert "name" in aapl_item
        assert "price" in aapl_item
        assert "change_pct" in aapl_item
        assert "signal" in aapl_item
        assert "category" in aapl_item
        assert "sector" in aapl_item
        assert "added_at" in aapl_item
        
        print(f"✓ Watchlist returns enriched data: {aapl_item['symbol']} - ${aapl_item['price']}")
    
    def test_check_watchlist_exists(self, api_client):
        """Test checking if symbol is in watchlist"""
        # Add stock
        api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "AAPL", "source": "manual"}
        )
        
        # Check exists
        response = api_client.get(f"{BASE_URL}/api/watchlist/check/AAPL")
        assert response.status_code == 200
        
        data = response.json()
        assert data["in_watchlist"] == True
        print(f"✓ Check watchlist (exists): AAPL in_watchlist={data['in_watchlist']}")
    
    def test_check_watchlist_not_exists(self, api_client):
        """Test checking symbol not in watchlist"""
        response = api_client.get(f"{BASE_URL}/api/watchlist/check/NOTINLIST123")
        assert response.status_code == 200
        
        data = response.json()
        assert data["in_watchlist"] == False
        print(f"✓ Check watchlist (not exists): in_watchlist={data['in_watchlist']}")
    
    def test_remove_stock_from_watchlist(self, api_client):
        """Test removing stock from watchlist"""
        # Add first
        api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "AAPL", "source": "manual"}
        )
        
        # Remove
        response = api_client.delete(f"{BASE_URL}/api/watchlist/AAPL")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "removed from watchlist" in data["message"]
        
        # Verify removed
        check_response = api_client.get(f"{BASE_URL}/api/watchlist/check/AAPL")
        assert check_response.json()["in_watchlist"] == False
        print(f"✓ Removed AAPL from watchlist and verified")
    
    def test_remove_nonexistent_stock(self, api_client):
        """Test removing stock not in watchlist"""
        response = api_client.delete(f"{BASE_URL}/api/watchlist/NOTEXIST123")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == False
        assert "not found in watchlist" in data["message"]
        print(f"✓ Remove nonexistent handled: {data['message']}")
    
    def test_update_note(self, api_client):
        """Test updating note for watchlist item"""
        # Add stock
        api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "AAPL", "source": "manual"}
        )
        
        # Update note
        response = api_client.put(
            f"{BASE_URL}/api/watchlist/AAPL/note?note=Test%20note%20for%20AAPL"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        
        # Verify note in watchlist
        watchlist = api_client.get(f"{BASE_URL}/api/watchlist").json()
        aapl_item = next((item for item in watchlist if item["symbol"] == "AAPL"), None)
        assert aapl_item is not None
        assert aapl_item["note"] == "Test note for AAPL"
        print(f"✓ Note updated: '{aapl_item['note']}'")
    
    def test_refresh_watchlist(self, api_client):
        """Test refreshing watchlist data"""
        # Add stocks
        api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "AAPL", "source": "manual"}
        )
        api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "MSFT", "source": "manual"}
        )
        
        # Refresh
        response = api_client.post(f"{BASE_URL}/api/watchlist/refresh")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "count" in data
        assert data["count"] >= 2
        
        # Verify items have price data
        for item in data["items"]:
            assert "symbol" in item
            assert "price" in item
            assert "change_pct" in item
        
        print(f"✓ Refreshed {data['count']} watchlist items")
    
    def test_clear_all_watchlist(self, api_client):
        """Test clearing entire watchlist"""
        # Add multiple stocks
        api_client.post(f"{BASE_URL}/api/watchlist", json={"symbol": "AAPL", "source": "manual"})
        api_client.post(f"{BASE_URL}/api/watchlist", json={"symbol": "MSFT", "source": "manual"})
        api_client.post(f"{BASE_URL}/api/watchlist", json={"symbol": "GOOGL", "source": "manual"})
        
        # Clear all
        response = api_client.delete(f"{BASE_URL}/api/watchlist/all")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["removed"] >= 3
        
        # Verify empty
        watchlist = api_client.get(f"{BASE_URL}/api/watchlist").json()
        assert len(watchlist) == 0
        print(f"✓ Cleared all {data['removed']} items from watchlist")
    
    def test_watchlist_persistence(self, api_client):
        """Test that watchlist persists across requests"""
        # Clear first
        api_client.delete(f"{BASE_URL}/api/watchlist/all")
        
        # Add stock
        api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "AAPL", "source": "manual", "note": "Persistence test"}
        )
        
        # Get watchlist multiple times
        for i in range(3):
            response = api_client.get(f"{BASE_URL}/api/watchlist")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["symbol"] == "AAPL"
            assert data[0]["note"] == "Persistence test"
        
        print(f"✓ Watchlist persists across multiple requests")
    
    def test_case_insensitive_symbol(self, api_client):
        """Test that symbol handling is case insensitive"""
        # Add with lowercase
        response = api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "aapl", "source": "manual"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["item"]["symbol"] == "AAPL"  # Should be uppercase
        
        # Check with mixed case
        check_response = api_client.get(f"{BASE_URL}/api/watchlist/check/AaPl")
        assert check_response.json()["in_watchlist"] == True
        
        # Remove with uppercase
        remove_response = api_client.delete(f"{BASE_URL}/api/watchlist/AAPL")
        assert remove_response.json()["success"] == True
        
        print(f"✓ Case insensitive symbol handling works")


class TestWatchlistIntegration:
    """Integration tests for watchlist with other features"""
    
    def test_watchlist_with_investment_signals(self, api_client):
        """Test that watchlist items get investment signal data"""
        # Add a stock that likely has investment signals
        api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "AAPL", "source": "investments"}
        )
        
        # Get watchlist
        response = api_client.get(f"{BASE_URL}/api/watchlist")
        assert response.status_code == 200
        
        data = response.json()
        aapl_item = next((item for item in data if item["symbol"] == "AAPL"), None)
        assert aapl_item is not None
        
        # Check for signal-related fields
        assert "signal" in aapl_item
        assert "category" in aapl_item
        assert "score" in aapl_item
        assert "confidence" in aapl_item
        
        print(f"✓ Watchlist item has signal data: signal={aapl_item['signal']}, category={aapl_item['category']}")
    
    def test_full_watchlist_workflow(self, api_client):
        """Test complete watchlist workflow: add -> view -> update note -> refresh -> remove"""
        # Clear first
        api_client.delete(f"{BASE_URL}/api/watchlist/all")
        
        # 1. Add stock
        add_response = api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "NVDA", "source": "trading"}
        )
        assert add_response.json()["success"] == True
        print("  Step 1: Added NVDA")
        
        # 2. View watchlist
        view_response = api_client.get(f"{BASE_URL}/api/watchlist")
        assert len(view_response.json()) == 1
        print("  Step 2: Verified in watchlist")
        
        # 3. Update note
        note_response = api_client.put(
            f"{BASE_URL}/api/watchlist/NVDA/note?note=AI%20chip%20leader"
        )
        assert note_response.json()["success"] == True
        print("  Step 3: Updated note")
        
        # 4. Refresh
        refresh_response = api_client.post(f"{BASE_URL}/api/watchlist/refresh")
        assert refresh_response.json()["count"] == 1
        print("  Step 4: Refreshed data")
        
        # 5. Verify note persisted
        verify_response = api_client.get(f"{BASE_URL}/api/watchlist")
        nvda_item = verify_response.json()[0]
        assert nvda_item["note"] == "AI chip leader"
        print("  Step 5: Verified note persisted")
        
        # 6. Remove
        remove_response = api_client.delete(f"{BASE_URL}/api/watchlist/NVDA")
        assert remove_response.json()["success"] == True
        print("  Step 6: Removed from watchlist")
        
        # 7. Verify removed
        final_response = api_client.get(f"{BASE_URL}/api/watchlist")
        assert len(final_response.json()) == 0
        print("  Step 7: Verified removal")
        
        print(f"✓ Full watchlist workflow completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
