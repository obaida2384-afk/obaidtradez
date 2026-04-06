"""
Long-Term Investing Market Overview Tests
Tests the new /api/lt-invest/market-overview endpoint and related LT features.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"


class TestAuth:
    """Authentication tests"""
    
    def test_auth_access_with_valid_code(self):
        """Test login with valid access code"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200, f"Auth failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "token" in data
        assert len(data["token"]) > 0
        print(f"✓ Auth successful, token received")
    
    def test_auth_access_with_invalid_code(self):
        """Test login with invalid access code"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": "wrongcode"})
        # API returns 200 with success=false for invalid code
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == False
        assert data.get("token") is None
        print(f"✓ Invalid code correctly rejected: {data.get('message')}")


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestMarketOverview:
    """Tests for /api/lt-invest/market-overview endpoint"""
    
    def test_market_overview_requires_auth(self):
        """Market overview requires authentication"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/market-overview")
        assert response.status_code == 401
        print(f"✓ Market overview requires auth")
    
    def test_market_overview_returns_companies(self, auth_headers):
        """Market overview returns list of companies"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/market-overview", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Check structure
        assert "companies" in data
        assert "total" in data
        assert "categories" in data
        assert "sources" in data
        
        print(f"✓ Market overview returned {data['total']} companies")
        print(f"  Sources: {data['sources']}")
        print(f"  Categories: {list(data['categories'].keys())}")
    
    def test_market_overview_company_fields(self, auth_headers):
        """Each company has required fields"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/market-overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if data["total"] == 0:
            pytest.skip("No companies in market overview")
        
        company = data["companies"][0]
        
        # Required fields
        required_fields = [
            "symbol", "name", "live_price", "rating_score", "rating_label",
            "trade_signal", "inv_signal", "entry_zone", "stop_loss", "take_profit",
            "bull_case", "bear_case", "quality_rating", "growth_trend"
        ]
        
        for field in required_fields:
            assert field in company, f"Missing field: {field}"
        
        print(f"✓ Company {company['symbol']} has all required fields")
        print(f"  Rating: {company['rating_score']} ({company['rating_label']})")
        print(f"  Live price: ${company['live_price']}")
        print(f"  Trade signal: {company['trade_signal']}")
        print(f"  Inv signal: {company['inv_signal']}")
    
    def test_market_overview_sorted_by_rating(self, auth_headers):
        """Companies are sorted by rating_score descending"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/market-overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if data["total"] < 2:
            pytest.skip("Not enough companies to test sorting")
        
        companies = data["companies"]
        for i in range(len(companies) - 1):
            assert companies[i]["rating_score"] >= companies[i+1]["rating_score"], \
                f"Not sorted: {companies[i]['symbol']} ({companies[i]['rating_score']}) < {companies[i+1]['symbol']} ({companies[i+1]['rating_score']})"
        
        print(f"✓ Companies sorted by rating_score descending")
        print(f"  Top 3: {[c['symbol'] for c in companies[:3]]}")
    
    def test_market_overview_categories(self, auth_headers):
        """Categories count matches companies"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/market-overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        categories = data["categories"]
        total_from_categories = sum(categories.values())
        
        assert total_from_categories == data["total"], \
            f"Category sum {total_from_categories} != total {data['total']}"
        
        print(f"✓ Categories sum matches total: {total_from_categories}")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:5]:
            print(f"  {cat}: {count}")


class TestPortfolio:
    """Tests for /api/lt-invest/portfolio endpoint"""
    
    def test_portfolio_requires_auth(self):
        """Portfolio requires authentication"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/portfolio")
        assert response.status_code == 401
        print(f"✓ Portfolio requires auth")
    
    def test_portfolio_returns_structure(self, auth_headers):
        """Portfolio returns proper structure"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/portfolio", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Check structure
        assert "summary" in data
        assert "positions" in data
        assert "bucket_breakdown" in data
        
        summary = data["summary"]
        assert "total_value" in summary
        assert "total_pnl_pct" in summary
        assert "position_count" in summary
        assert "diversification_score" in summary
        assert "needs_rebalance" in summary
        
        print(f"✓ Portfolio structure correct")
        print(f"  Total value: ${summary.get('total_value', 0)}")
        print(f"  Positions: {summary.get('position_count', 0)}")
        print(f"  Diversification: {summary.get('diversification_score', 0)}")
    
    def test_portfolio_bucket_breakdown(self, auth_headers):
        """Portfolio has bucket breakdown for all 3 buckets"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/portfolio", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        buckets = data["bucket_breakdown"]
        expected_buckets = ["core", "quality_growth", "opportunistic_value"]
        
        for bucket in expected_buckets:
            assert bucket in buckets, f"Missing bucket: {bucket}"
            bucket_data = buckets[bucket]
            assert "allocation_pct" in bucket_data
            assert "target_min" in bucket_data
            assert "target_max" in bucket_data
            assert "status" in bucket_data
        
        print(f"✓ All 3 buckets present in breakdown")
        for b in expected_buckets:
            print(f"  {b}: {buckets[b]['allocation_pct']}% (target: {buckets[b]['target_min']}-{buckets[b]['target_max']}%)")


class TestStageBuy:
    """Tests for /api/lt-invest/stage-buy endpoint"""
    
    def test_stage_buy_requires_auth(self):
        """Stage buy requires authentication"""
        response = requests.post(f"{BASE_URL}/api/lt-invest/stage-buy", json={
            "symbol": "VOO", "bucket": "core", "shares": 1, "price": 450
        })
        assert response.status_code == 401
        print(f"✓ Stage buy requires auth")
    
    def test_stage_buy_validates_fields(self, auth_headers):
        """Stage buy validates required fields"""
        # Missing all required fields - API returns error
        response = requests.post(f"{BASE_URL}/api/lt-invest/stage-buy", 
            headers=auth_headers, json={})
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        print(f"✓ Missing fields validation: {data.get('error')}")
        
        print(f"✓ Stage buy validates required fields")
    
    def test_stage_buy_creates_position(self, auth_headers):
        """Stage buy creates a position"""
        # First clean up any existing test position
        requests.post(f"{BASE_URL}/api/lt-invest/close", 
            headers=auth_headers, json={"symbol": "TEST_VOO", "reason": "Pre-test cleanup"})
        
        # Create position
        response = requests.post(f"{BASE_URL}/api/lt-invest/stage-buy", 
            headers=auth_headers, json={
                "symbol": "TEST_VOO",
                "bucket": "core",
                "shares": 2,
                "price": 450,
                "thesis": "Test position for automated testing"
            })
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Check for error first
        if "error" in data:
            pytest.fail(f"Stage buy failed: {data['error']}")
        
        # API returns {"success": true, "position": {...}}
        assert data.get("success") == True, f"Unexpected response: {data}"
        position = data.get("position", {})
        assert position.get("symbol") == "TEST_VOO"
        assert position.get("bucket") == "core"
        assert position.get("shares") == 2
        assert position.get("avg_cost") == 450
        assert position.get("stage") == 1
        
        print(f"✓ Stage buy created position: {position['symbol']}")
        print(f"  Shares: {position['shares']}, Avg cost: ${position['avg_cost']}, Stage: {position['stage']}")
        
        # Verify in portfolio
        response = requests.get(f"{BASE_URL}/api/lt-invest/portfolio", headers=auth_headers)
        assert response.status_code == 200
        portfolio = response.json()
        
        positions = portfolio["positions"]
        test_pos = next((p for p in positions if p["symbol"] == "TEST_VOO"), None)
        assert test_pos is not None, "Position not found in portfolio"
        
        print(f"✓ Position verified in portfolio")
        
        # Cleanup - close the position
        response = requests.post(f"{BASE_URL}/api/lt-invest/close", 
            headers=auth_headers, json={"symbol": "TEST_VOO", "reason": "Test cleanup"})
        assert response.status_code == 200
        print(f"✓ Test position cleaned up")


class TestRecommendations:
    """Tests for /api/lt-invest/recommendations endpoint"""
    
    def test_recommendations_requires_auth(self):
        """Recommendations requires authentication"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/recommendations")
        assert response.status_code == 401
        print(f"✓ Recommendations requires auth")
    
    def test_recommendations_returns_list(self, auth_headers):
        """Recommendations returns list"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/recommendations", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "recommendations" in data
        assert "count" in data
        assert isinstance(data["recommendations"], list)
        
        print(f"✓ Recommendations returned {data['count']} items")
        
        if data["count"] > 0:
            rec = data["recommendations"][0]
            assert "symbol" in rec
            assert "action" in rec
            assert "reason" in rec
            print(f"  First rec: {rec['action']} {rec['symbol']} - {rec['reason'][:50]}...")


class TestThesis:
    """Tests for /api/lt-invest/thesis/{symbol} endpoint"""
    
    def test_thesis_requires_auth(self):
        """Thesis requires authentication"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/thesis/VOO")
        assert response.status_code == 401
        print(f"✓ Thesis requires auth")
    
    def test_thesis_for_nonexistent_position(self, auth_headers):
        """Thesis for non-existent position returns error"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/thesis/NONEXISTENT123", headers=auth_headers)
        assert response.status_code == 200  # Returns 200 with error in body
        data = response.json()
        assert "error" in data
        print(f"✓ Thesis for non-existent position returns error")
    
    def test_thesis_for_held_position(self, auth_headers):
        """Thesis for held position returns health data"""
        # First create a position
        response = requests.post(f"{BASE_URL}/api/lt-invest/stage-buy", 
            headers=auth_headers, json={
                "symbol": "TEST_THESIS",
                "bucket": "quality_growth",
                "shares": 1,
                "price": 100,
                "thesis": "Testing thesis health endpoint"
            })
        assert response.status_code == 200
        
        # Get thesis
        response = requests.get(f"{BASE_URL}/api/lt-invest/thesis/TEST_THESIS", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "symbol" in data
        assert "health_score" in data
        assert "health_status" in data
        assert "recommendation" in data
        assert "original_thesis" in data
        
        print(f"✓ Thesis health returned for TEST_THESIS")
        print(f"  Health score: {data['health_score']}")
        print(f"  Status: {data['health_status']}")
        print(f"  Recommendation: {data['recommendation']}")
        
        # Cleanup
        response = requests.post(f"{BASE_URL}/api/lt-invest/close", 
            headers=auth_headers, json={"symbol": "TEST_THESIS", "reason": "Test cleanup"})
        assert response.status_code == 200
        print(f"✓ Test position cleaned up")


class TestClose:
    """Tests for /api/lt-invest/close endpoint"""
    
    def test_close_requires_auth(self):
        """Close requires authentication"""
        response = requests.post(f"{BASE_URL}/api/lt-invest/close", json={"symbol": "VOO"})
        assert response.status_code == 401
        print(f"✓ Close requires auth")
    
    def test_close_validates_symbol(self, auth_headers):
        """Close validates symbol field"""
        response = requests.post(f"{BASE_URL}/api/lt-invest/close", 
            headers=auth_headers, json={"reason": "test"})
        # API returns 200 with error in body
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        print(f"✓ Close validates symbol field: {data.get('error')}")
    
    def test_close_position_workflow(self, auth_headers):
        """Full workflow: create → verify → close → verify removed"""
        # Create
        response = requests.post(f"{BASE_URL}/api/lt-invest/stage-buy", 
            headers=auth_headers, json={
                "symbol": "TEST_CLOSE",
                "bucket": "opportunistic_value",
                "shares": 1,
                "price": 50
            })
        assert response.status_code == 200
        print(f"✓ Created TEST_CLOSE position")
        
        # Verify exists
        response = requests.get(f"{BASE_URL}/api/lt-invest/portfolio", headers=auth_headers)
        positions = response.json()["positions"]
        assert any(p["symbol"] == "TEST_CLOSE" for p in positions)
        print(f"✓ Position exists in portfolio")
        
        # Close
        response = requests.post(f"{BASE_URL}/api/lt-invest/close", 
            headers=auth_headers, json={"symbol": "TEST_CLOSE", "reason": "Test workflow"})
        assert response.status_code == 200
        print(f"✓ Position closed")
        
        # Verify removed
        response = requests.get(f"{BASE_URL}/api/lt-invest/portfolio", headers=auth_headers)
        positions = response.json()["positions"]
        assert not any(p["symbol"] == "TEST_CLOSE" for p in positions)
        print(f"✓ Position removed from portfolio")


class TestMarketOverviewDataQuality:
    """Data quality tests for market overview"""
    
    def test_companies_have_live_prices(self, auth_headers):
        """Most companies should have live prices"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/market-overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if data["total"] == 0:
            pytest.skip("No companies in market overview")
        
        companies_with_price = sum(1 for c in data["companies"] if c["live_price"] > 0)
        price_coverage = companies_with_price / data["total"] * 100
        
        print(f"✓ Price coverage: {companies_with_price}/{data['total']} ({price_coverage:.1f}%)")
        
        # At least 50% should have prices
        assert price_coverage >= 50, f"Low price coverage: {price_coverage:.1f}%"
    
    def test_companies_have_ratings(self, auth_headers):
        """Most companies should have ratings"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/market-overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if data["total"] == 0:
            pytest.skip("No companies in market overview")
        
        companies_with_rating = sum(1 for c in data["companies"] if c["rating_score"] > 0)
        rating_coverage = companies_with_rating / data["total"] * 100
        
        print(f"✓ Rating coverage: {companies_with_rating}/{data['total']} ({rating_coverage:.1f}%)")
        
        # At least 80% should have ratings
        assert rating_coverage >= 80, f"Low rating coverage: {rating_coverage:.1f}%"
    
    def test_companies_have_signals(self, auth_headers):
        """Companies should have either trade or investment signals"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/market-overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if data["total"] == 0:
            pytest.skip("No companies in market overview")
        
        with_trade = sum(1 for c in data["companies"] if c["has_trading_signal"])
        with_invest = sum(1 for c in data["companies"] if c["has_investment_signal"])
        
        print(f"✓ Signal sources:")
        print(f"  Trading signals: {with_trade}")
        print(f"  Investment signals: {with_invest}")
        
        # All companies should have at least one signal source
        for c in data["companies"]:
            assert c["has_trading_signal"] or c["has_investment_signal"], \
                f"{c['symbol']} has no signal source"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
