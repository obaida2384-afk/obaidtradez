"""
Test Historical Performance Feature for Investments
Tests the 30-year historical price data analysis feature
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token using access code"""
    response = requests.post(
        f"{BASE_URL}/api/auth/access",
        json={"code": ACCESS_CODE}
    )
    assert response.status_code == 200, f"Auth failed: {response.text}"
    data = response.json()
    assert data.get("success"), f"Auth not successful: {data}"
    token = data.get("token")
    assert token, "No token returned"
    print(f"✓ Authenticated successfully, token obtained")
    return token


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestHistoricalPerformance:
    """Tests for 30-year historical performance feature in investments"""
    
    def test_investments_scan_returns_signals(self, auth_headers):
        """Test that /api/investments/scan returns investment signals"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # API returns 'all' key with all signals
        assert "all" in data, "Response should contain 'all' field"
        assert isinstance(data["all"], list), "'all' should be a list"
        print(f"✓ Investments scan returned {len(data['all'])} signals")
        
        # Check category counts
        assert "category_counts" in data, "Response should have category_counts"
        print(f"  - Category counts: {data.get('category_counts')}")
        return data
    
    def test_signals_have_historical_performance_field(self, auth_headers):
        """Test that signals include historical_performance field"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        signals = data.get("all", [])
        
        # Check if any signals have historical_performance
        signals_with_hist = [s for s in signals if s.get("historical_performance") is not None]
        print(f"✓ {len(signals_with_hist)} out of {len(signals)} signals have historical_performance data")
        
        # At least some signals should have historical data (per main agent: ~100 stocks refreshed)
        assert len(signals_with_hist) > 0, "At least some signals should have historical_performance"
    
    def test_historical_performance_structure(self, auth_headers):
        """Test that historical_performance has correct structure"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        signals = data.get("all", [])
        
        # Find a signal with historical_performance
        signal_with_hist = None
        for s in signals:
            if s.get("historical_performance"):
                signal_with_hist = s
                break
        
        assert signal_with_hist is not None, "Should find at least one signal with historical_performance"
        
        hist = signal_with_hist["historical_performance"]
        symbol = signal_with_hist.get("symbol", "Unknown")
        
        # Check required fields exist
        expected_fields = [
            "years_of_data",
            "historical_rating",
            "max_drawdown_pct",
            "annualized_volatility",
            "positive_years",
            "negative_years"
        ]
        
        for field in expected_fields:
            assert field in hist, f"historical_performance should have '{field}' field"
        
        print(f"✓ {symbol} historical_performance structure validated")
        print(f"  - Years of data: {hist.get('years_of_data')}")
        print(f"  - Historical rating: {hist.get('historical_rating')}")
        
        # Check CAGR fields (at least some should be present)
        cagr_fields = ["cagr_1yr", "cagr_3yr", "cagr_5yr", "cagr_10yr", "cagr_20yr", "cagr_30yr"]
        cagr_present = [f for f in cagr_fields if hist.get(f) is not None]
        print(f"  - CAGR fields present: {cagr_present}")
        
        assert len(cagr_present) > 0, "At least one CAGR field should have data"
    
    def test_historical_performance_values_valid(self, auth_headers):
        """Test that historical_performance values are valid"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        signals = data.get("all", [])
        
        # Find AAPL or another well-known stock with long history
        target_symbols = ["AAPL", "MSFT", "JNJ", "PG", "KO"]
        signal_with_hist = None
        
        for s in signals:
            if s.get("symbol") in target_symbols and s.get("historical_performance"):
                signal_with_hist = s
                break
        
        if signal_with_hist is None:
            # Fallback to any signal with historical data
            for s in signals:
                if s.get("historical_performance"):
                    signal_with_hist = s
                    break
        
        assert signal_with_hist is not None, "Should find a signal with historical_performance"
        
        hist = signal_with_hist["historical_performance"]
        symbol = signal_with_hist.get("symbol")
        
        # Validate years_of_data
        years = hist.get("years_of_data", 0)
        assert years > 0, f"{symbol} should have positive years_of_data"
        print(f"✓ {symbol} has {years} years of historical data")
        
        # Validate historical_rating is one of expected values
        valid_ratings = ["Exceptional", "Strong", "Average", "Weak", "Poor", "N/A"]
        rating = hist.get("historical_rating")
        assert rating in valid_ratings, f"Invalid historical_rating: {rating}"
        print(f"  - Historical rating: {rating}")
        
        # Validate max_drawdown is negative (drawdowns are losses)
        max_dd = hist.get("max_drawdown_pct")
        if max_dd is not None:
            assert max_dd <= 0, f"Max drawdown should be negative or zero, got {max_dd}"
            print(f"  - Max drawdown: {max_dd}%")
        
        # Validate volatility is positive
        vol = hist.get("annualized_volatility")
        if vol is not None:
            assert vol >= 0, f"Volatility should be non-negative, got {vol}"
            print(f"  - Annualized volatility: {vol}%")
        
        # Validate win/loss years
        pos_years = hist.get("positive_years", 0)
        neg_years = hist.get("negative_years", 0)
        if pos_years > 0 or neg_years > 0:
            print(f"  - Win/Loss years: {pos_years}/{neg_years}")
    
    def test_aapl_has_long_history(self, auth_headers):
        """Test that AAPL specifically has 20+ years of data (as mentioned by main agent)"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        signals = data.get("all", [])
        
        # Find AAPL
        aapl = None
        for s in signals:
            if s.get("symbol") == "AAPL":
                aapl = s
                break
        
        if aapl is None:
            pytest.skip("AAPL not found in cached signals")
        
        hist = aapl.get("historical_performance")
        if hist is None:
            pytest.skip("AAPL doesn't have historical_performance yet")
        
        years = hist.get("years_of_data", 0)
        print(f"✓ AAPL has {years} years of historical data")
        
        # Main agent mentioned AAPL shows 29yr data
        assert years >= 20, f"AAPL should have 20+ years of data, got {years}"
        
        # Check 10Y CAGR (main agent mentioned 25.1%)
        cagr_10yr = hist.get("cagr_10yr")
        if cagr_10yr is not None:
            print(f"  - 10Y CAGR: {cagr_10yr}%")
            assert cagr_10yr > 0, "AAPL 10Y CAGR should be positive"
        
        # Check other metrics
        print(f"  - Total return: {hist.get('total_return_pct')}%")
        print(f"  - Max drawdown: {hist.get('max_drawdown_pct')}%")
        print(f"  - Win/Loss years: {hist.get('positive_years')}/{hist.get('negative_years')}")
        print(f"  - Historical rating: {hist.get('historical_rating')}")
    
    def test_investments_refresh_endpoint(self, auth_headers):
        """Test that /api/investments/refresh endpoint exists and triggers background task"""
        response = requests.post(f"{BASE_URL}/api/investments/refresh", headers=auth_headers)
        
        # Should return 200 or 202 (accepted for background processing)
        assert response.status_code in [200, 202], f"Expected 200/202, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"✓ Investments refresh response: {data}")
        
        # Should indicate background task started
        assert "status" in data or "message" in data, "Response should have status or message"
    
    def test_historical_performance_cagr_values(self, auth_headers):
        """Test CAGR values are computed correctly for different time periods"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        signals = data.get("all", [])
        
        # Find signals with historical data
        signals_with_hist = [s for s in signals if s.get("historical_performance")]
        
        for signal in signals_with_hist[:5]:  # Check first 5
            hist = signal["historical_performance"]
            symbol = signal.get("symbol")
            years = hist.get("years_of_data", 0)
            
            # Check that CAGR values are present based on years of data
            if years >= 1:
                assert hist.get("cagr_1yr") is not None, f"{symbol} should have 1Y CAGR"
            if years >= 3:
                assert hist.get("cagr_3yr") is not None, f"{symbol} should have 3Y CAGR"
            if years >= 5:
                assert hist.get("cagr_5yr") is not None, f"{symbol} should have 5Y CAGR"
            if years >= 10:
                assert hist.get("cagr_10yr") is not None, f"{symbol} should have 10Y CAGR"
            if years >= 20:
                assert hist.get("cagr_20yr") is not None, f"{symbol} should have 20Y CAGR"
            
            print(f"✓ {symbol}: {years}yr data, CAGRs validated")
    
    def test_historical_performance_best_worst_years(self, auth_headers):
        """Test best/worst year data is present"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        signals = data.get("all", [])
        
        # Find a signal with historical data
        signal_with_hist = None
        for s in signals:
            if s.get("historical_performance"):
                signal_with_hist = s
                break
        
        assert signal_with_hist is not None
        
        hist = signal_with_hist["historical_performance"]
        symbol = signal_with_hist.get("symbol")
        
        # Check best/worst year fields
        if hist.get("best_year"):
            assert hist.get("best_year_pct") is not None, "best_year_pct should be present"
            print(f"✓ {symbol} best year: {hist.get('best_year')} (+{hist.get('best_year_pct')}%)")
        
        if hist.get("worst_year"):
            assert hist.get("worst_year_pct") is not None, "worst_year_pct should be present"
            print(f"  Worst year: {hist.get('worst_year')} ({hist.get('worst_year_pct')}%)")


class TestInvestmentsAPIBasics:
    """Basic API tests for investments endpoints"""
    
    def test_auth_works(self):
        """Test authentication with access code"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "token" in data
        print("✓ Authentication with access code works")
    
    def test_investments_scan_response_structure(self, auth_headers):
        """Test investments scan response has expected structure"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check top-level fields
        assert "all" in data
        assert "category_counts" in data
        
        print(f"✓ Response structure valid")
        print(f"  - Total signals: {len(data.get('all', []))}")
        print(f"  - Category counts: {data.get('category_counts')}")
        
        if data.get("all"):
            signal = data["all"][0]
            # Check signal has basic fields
            assert "symbol" in signal
            assert "name" in signal
            assert "signal" in signal
            assert "confidence" in signal
            print(f"  - First signal: {signal.get('symbol')} - {signal.get('signal')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
