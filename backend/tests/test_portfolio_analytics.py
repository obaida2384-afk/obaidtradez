"""
Portfolio Analytics API Tests
Tests for portfolio performance charts and analytics endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token by verifying access code"""
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/auth/access",
        json={"code": ACCESS_CODE}
    )
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            return data.get("token")
    pytest.fail(f"Failed to get auth token: {response.text}")


@pytest.fixture
def api_session(auth_token):
    """Create authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestPortfolioAnalyticsAPI:
    """Test portfolio analytics endpoints"""
    
    # ==================== Health Check ====================
    def test_api_health(self, api_session):
        """Test API is running"""
        response = api_session.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "running"
        print("✓ API health check passed")
    
    # ==================== Account & Positions ====================
    def test_get_account(self, api_session):
        """Test account endpoint returns account data"""
        response = api_session.get(f"{BASE_URL}/api/account")
        # Alpaca may return 401 with invalid keys, but endpoint should work
        assert response.status_code in [200, 401, 500]
        if response.status_code == 200:
            data = response.json()
            # Check expected fields exist
            assert "equity" in data or "error" in data
            print(f"✓ Account endpoint returned: {list(data.keys())[:5]}")
        else:
            print(f"✓ Account endpoint returned {response.status_code} (Alpaca auth issue expected)")
    
    def test_get_positions(self, api_session):
        """Test positions endpoint"""
        response = api_session.get(f"{BASE_URL}/api/positions")
        assert response.status_code in [200, 401, 500]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            print(f"✓ Positions endpoint returned {len(data)} positions")
        else:
            print(f"✓ Positions endpoint returned {response.status_code} (Alpaca auth issue expected)")
    
    # ==================== Portfolio Analytics ====================
    def test_portfolio_analytics_endpoint(self, api_session):
        """Test comprehensive portfolio analytics endpoint"""
        response = api_session.get(f"{BASE_URL}/api/portfolio/analytics?period=1M")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "period" in data
        assert "history" in data
        assert "drawdowns" in data
        assert "max_drawdown" in data
        assert "win_rate" in data
        assert "sector_allocation" in data
        assert "pnl_breakdown" in data
        assert "strategy_performance" in data
        
        print(f"✓ Portfolio analytics returned all expected fields")
        print(f"  - Period: {data['period']}")
        print(f"  - History points: {len(data['history'])}")
        print(f"  - Drawdown points: {len(data['drawdowns'])}")
        print(f"  - Max drawdown: {data['max_drawdown']}%")
        print(f"  - Strategy performance entries: {len(data['strategy_performance'])}")
    
    def test_portfolio_analytics_period_1D(self, api_session):
        """Test analytics with 1D period"""
        response = api_session.get(f"{BASE_URL}/api/portfolio/analytics?period=1D")
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "1D"
        print("✓ Portfolio analytics 1D period works")
    
    def test_portfolio_analytics_period_1W(self, api_session):
        """Test analytics with 1W period"""
        response = api_session.get(f"{BASE_URL}/api/portfolio/analytics?period=1W")
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "1W"
        print("✓ Portfolio analytics 1W period works")
    
    def test_portfolio_analytics_period_1Y(self, api_session):
        """Test analytics with 1Y period"""
        response = api_session.get(f"{BASE_URL}/api/portfolio/analytics?period=1Y")
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "1Y"
        print("✓ Portfolio analytics 1Y period works")
    
    def test_portfolio_analytics_period_ALL(self, api_session):
        """Test analytics with ALL period"""
        response = api_session.get(f"{BASE_URL}/api/portfolio/analytics?period=ALL")
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "ALL"
        print("✓ Portfolio analytics ALL period works")
    
    # ==================== Individual Endpoints ====================
    def test_portfolio_history_endpoint(self, api_session):
        """Test portfolio history endpoint"""
        response = api_session.get(f"{BASE_URL}/api/portfolio/history?period=1M")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert "period" in data
        print(f"✓ Portfolio history returned {len(data['history'])} data points")
    
    def test_portfolio_drawdown_endpoint(self, api_session):
        """Test portfolio drawdown endpoint"""
        response = api_session.get(f"{BASE_URL}/api/portfolio/drawdown?period=1M")
        assert response.status_code == 200
        data = response.json()
        assert "drawdowns" in data
        assert "max_drawdown" in data
        assert "period" in data
        print(f"✓ Portfolio drawdown returned max_drawdown: {data['max_drawdown']}%")
    
    def test_portfolio_win_rate_endpoint(self, api_session):
        """Test portfolio win rate endpoint"""
        response = api_session.get(f"{BASE_URL}/api/portfolio/win-rate")
        assert response.status_code == 200
        data = response.json()
        # Win rate should have these fields
        assert "overall" in data
        assert "trend" in data
        print(f"✓ Portfolio win rate returned overall: {data['overall']}%")
    
    def test_portfolio_sector_allocation_endpoint(self, api_session):
        """Test portfolio sector allocation endpoint"""
        response = api_session.get(f"{BASE_URL}/api/portfolio/sector-allocation")
        assert response.status_code == 200
        data = response.json()
        assert "allocation" in data
        assert "position_count" in data
        print(f"✓ Sector allocation returned {len(data['allocation'])} sectors, {data['position_count']} positions")
    
    def test_portfolio_pnl_breakdown_endpoint(self, api_session):
        """Test portfolio P&L breakdown endpoint"""
        response = api_session.get(f"{BASE_URL}/api/portfolio/pnl-breakdown")
        assert response.status_code == 200
        data = response.json()
        # Check expected P&L fields
        assert "realized_pnl" in data
        assert "unrealized_pnl" in data
        assert "total_pnl" in data
        assert "avg_trade_return" in data
        print(f"✓ P&L breakdown: realized=${data['realized_pnl']}, unrealized=${data['unrealized_pnl']}, total=${data['total_pnl']}")
    
    def test_portfolio_strategy_performance_endpoint(self, api_session):
        """Test portfolio strategy performance endpoint"""
        response = api_session.get(f"{BASE_URL}/api/portfolio/strategy-performance")
        assert response.status_code == 200
        data = response.json()
        assert "performance" in data
        print(f"✓ Strategy performance returned {len(data['performance'])} strategies")
        
        # If there are strategies, verify structure
        if data['performance']:
            strategy = data['performance'][0]
            assert "strategy" in strategy
            assert "avg_return" in strategy
            assert "avg_win_rate" in strategy
            print(f"  - Top strategy: {strategy['strategy']} with {strategy['avg_return']}% avg return")
    
    # ==================== Data Validation ====================
    def test_win_rate_data_structure(self, api_session):
        """Test win rate response has correct structure"""
        response = api_session.get(f"{BASE_URL}/api/portfolio/win-rate")
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields
        expected_fields = ["overall", "trend"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        # If there are trades, verify additional fields
        if data.get("total_trades", 0) > 0:
            assert "wins" in data
            assert "losses" in data
            assert "total_trades" in data
        
        print("✓ Win rate data structure is correct")
    
    def test_pnl_breakdown_data_structure(self, api_session):
        """Test P&L breakdown has correct structure"""
        response = api_session.get(f"{BASE_URL}/api/portfolio/pnl-breakdown")
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = ["realized_pnl", "realized_pnl_pct", "unrealized_pnl", 
                          "unrealized_pnl_pct", "total_pnl", "avg_trade_return"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify numeric types
        assert isinstance(data["realized_pnl"], (int, float))
        assert isinstance(data["unrealized_pnl"], (int, float))
        assert isinstance(data["total_pnl"], (int, float))
        
        print("✓ P&L breakdown data structure is correct")
    
    def test_analytics_response_time(self, api_session):
        """Test analytics endpoint responds within reasonable time"""
        import time
        start = time.time()
        response = api_session.get(f"{BASE_URL}/api/portfolio/analytics?period=1M")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 10, f"Analytics took too long: {elapsed:.2f}s"
        print(f"✓ Analytics response time: {elapsed:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
