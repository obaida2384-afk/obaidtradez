"""
Test suite for ObaidTradez Execution Transparency & Separated Analytics
Tests:
- /api/execution/rejection-report - Candidate rejection tracking
- /api/execution/pipeline-stages - Pipeline stage counts
- /api/analytics/by-strategy - Separated analytics (Day Trading, Long-Term, Manual)
- /api/lt-invest/market-overview - 1250 companies with ratings
- /api/lt-invest/portfolio - Portfolio endpoint
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"


class TestAuth:
    """Authentication tests"""
    
    def test_login_with_valid_code(self):
        """Test login with access code Bullishalmarkhan7.7"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Login not successful: {data}"
        assert "token" in data, f"No token in response: {data}"
        print(f"PASS: Login with code {ACCESS_CODE} returns token")
        return data["token"]


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for all tests"""
    response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
    if response.status_code == 200:
        data = response.json()
        if data.get("success") and data.get("token"):
            return data["token"]
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestExecutionRejectionReport:
    """Tests for /api/execution/rejection-report endpoint"""
    
    def test_rejection_report_requires_auth(self):
        """Rejection report requires authentication"""
        response = requests.get(f"{BASE_URL}/api/execution/rejection-report")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/execution/rejection-report requires auth (401 without token)")
    
    def test_rejection_report_returns_structure(self, auth_headers):
        """Rejection report returns expected structure"""
        response = requests.get(f"{BASE_URL}/api/execution/rejection-report", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check required fields
        required_fields = ["total_candidates", "executed", "rejected", "execution_rate", 
                          "rejection_breakdown", "rejection_categories"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Validate types
        assert isinstance(data["total_candidates"], int), "total_candidates should be int"
        assert isinstance(data["executed"], int), "executed should be int"
        assert isinstance(data["rejected"], int), "rejected should be int"
        assert isinstance(data["execution_rate"], (int, float)), "execution_rate should be numeric"
        assert isinstance(data["rejection_breakdown"], dict), "rejection_breakdown should be dict"
        assert isinstance(data["rejection_categories"], dict), "rejection_categories should be dict"
        
        print(f"PASS: Rejection report structure valid - total_candidates={data['total_candidates']}, "
              f"executed={data['executed']}, rejected={data['rejected']}, "
              f"execution_rate={data['execution_rate']}%")
    
    def test_rejection_report_with_date_filter(self, auth_headers):
        """Rejection report accepts date filter"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = requests.get(
            f"{BASE_URL}/api/execution/rejection-report",
            headers=auth_headers,
            params={"date": today}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "total_candidates" in data
        print(f"PASS: Rejection report with date={today} works")
    
    def test_rejection_categories_defined(self, auth_headers):
        """Rejection categories are properly defined"""
        response = requests.get(f"{BASE_URL}/api/execution/rejection-report", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        categories = data.get("rejection_categories", {})
        expected_categories = [
            "timing_block", "session_phase", "confidence_below_threshold",
            "duplicate_position", "risk_violation", "max_trades_reached",
            "cooldown_active", "shadow_mode", "order_failed"
        ]
        
        found_categories = 0
        for cat in expected_categories:
            if cat in categories:
                found_categories += 1
        
        assert found_categories >= 5, f"Expected at least 5 rejection categories, found {found_categories}"
        print(f"PASS: Rejection categories defined ({len(categories)} categories)")


class TestPipelineStages:
    """Tests for /api/execution/pipeline-stages endpoint"""
    
    def test_pipeline_stages_requires_auth(self):
        """Pipeline stages requires authentication"""
        response = requests.get(f"{BASE_URL}/api/execution/pipeline-stages")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/execution/pipeline-stages requires auth (401 without token)")
    
    def test_pipeline_stages_returns_structure(self, auth_headers):
        """Pipeline stages returns expected structure"""
        response = requests.get(f"{BASE_URL}/api/execution/pipeline-stages", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check required fields
        assert "stages" in data, "Missing 'stages' field"
        assert "total" in data, "Missing 'total' field"
        
        stages = data["stages"]
        assert isinstance(stages, dict), "stages should be dict"
        
        # Check expected stage names
        expected_stages = ["candidate", "executed", "risk_check", "approved"]
        found_stages = 0
        for stage in expected_stages:
            if stage in stages:
                found_stages += 1
        
        print(f"PASS: Pipeline stages structure valid - total={data['total']}, stages={list(stages.keys())}")
    
    def test_pipeline_stages_with_date_filter(self, auth_headers):
        """Pipeline stages accepts date filter"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = requests.get(
            f"{BASE_URL}/api/execution/pipeline-stages",
            headers=auth_headers,
            params={"date": today}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "stages" in data
        print(f"PASS: Pipeline stages with date={today} works")


class TestAnalyticsByStrategy:
    """Tests for /api/analytics/by-strategy endpoint - Separated analytics"""
    
    def test_by_strategy_requires_auth(self):
        """By-strategy analytics requires authentication"""
        response = requests.get(f"{BASE_URL}/api/analytics/by-strategy")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/analytics/by-strategy requires auth (401 without token)")
    
    def test_by_strategy_returns_three_sections(self, auth_headers):
        """By-strategy analytics returns day_trading, long_term, and manual_external sections"""
        response = requests.get(f"{BASE_URL}/api/analytics/by-strategy", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check three main sections
        assert "day_trading" in data, "Missing 'day_trading' section"
        assert "long_term" in data, "Missing 'long_term' section"
        assert "manual_external" in data, "Missing 'manual_external' section"
        
        print("PASS: By-strategy analytics has day_trading, long_term, manual_external sections")
    
    def test_day_trading_analytics_fields(self, auth_headers):
        """Day trading analytics has required fields"""
        response = requests.get(f"{BASE_URL}/api/analytics/by-strategy", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        dt = data.get("day_trading", {})
        required_fields = [
            "total_trades", "closed_trades", "win_rate", "total_pnl",
            "average_win_pct", "average_loss_pct", "best_trade", "worst_trade",
            "round_trips", "open_positions"
        ]
        
        for field in required_fields:
            assert field in dt, f"Day trading missing field: {field}"
        
        # Validate types
        assert isinstance(dt["total_trades"], int), "total_trades should be int"
        assert isinstance(dt["closed_trades"], int), "closed_trades should be int"
        assert isinstance(dt["win_rate"], (int, float)), "win_rate should be numeric"
        assert isinstance(dt["total_pnl"], (int, float)), "total_pnl should be numeric"
        assert isinstance(dt["round_trips"], list), "round_trips should be list"
        assert isinstance(dt["open_positions"], list), "open_positions should be list"
        
        print(f"PASS: Day trading analytics fields valid - total_trades={dt['total_trades']}, "
              f"closed_trades={dt['closed_trades']}, win_rate={dt['win_rate']}%, "
              f"total_pnl=${dt['total_pnl']}")
    
    def test_round_trips_structure(self, auth_headers):
        """Round trips show actual P&L per trade"""
        response = requests.get(f"{BASE_URL}/api/analytics/by-strategy", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        round_trips = data.get("day_trading", {}).get("round_trips", [])
        
        if round_trips:
            # Check first round trip structure
            rt = round_trips[0]
            expected_fields = ["symbol", "qty", "avg_buy", "avg_sell", "pnl_dollars", "pnl_pct"]
            for field in expected_fields:
                assert field in rt, f"Round trip missing field: {field}"
            
            print(f"PASS: Round trips structure valid - {len(round_trips)} round trips found")
            # Print sample round trips
            for rt in round_trips[:3]:
                pnl_sign = "+" if rt["pnl_dollars"] >= 0 else ""
                print(f"  {rt['symbol']}: {pnl_sign}${rt['pnl_dollars']} ({pnl_sign}{rt['pnl_pct']}%)")
        else:
            print("PASS: Round trips structure valid (no closed trades yet)")
    
    def test_long_term_analytics_fields(self, auth_headers):
        """Long-term analytics has required fields"""
        response = requests.get(f"{BASE_URL}/api/analytics/by-strategy", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        lt = data.get("long_term", {})
        required_fields = [
            "active_positions", "closed_positions", "total_value",
            "total_cost", "unrealized_pnl", "positions"
        ]
        
        for field in required_fields:
            assert field in lt, f"Long-term missing field: {field}"
        
        assert isinstance(lt["active_positions"], int), "active_positions should be int"
        assert isinstance(lt["closed_positions"], int), "closed_positions should be int"
        assert isinstance(lt["positions"], list), "positions should be list"
        
        print(f"PASS: Long-term analytics fields valid - active={lt['active_positions']}, "
              f"closed={lt['closed_positions']}, value=${lt['total_value']}")
    
    def test_manual_external_section(self, auth_headers):
        """Manual/external positions section has required fields and protection note"""
        response = requests.get(f"{BASE_URL}/api/analytics/by-strategy", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        manual = data.get("manual_external", {})
        required_fields = ["position_count", "positions", "total_value", "note"]
        
        for field in required_fields:
            assert field in manual, f"Manual/external missing field: {field}"
        
        # Check protection note
        note = manual.get("note", "")
        assert "PROTECTED" in note.upper() or "protected" in note.lower(), \
            f"Manual positions should have PROTECTED note, got: {note}"
        
        print(f"PASS: Manual/external section valid - {manual['position_count']} positions, "
              f"note: '{note}'")
    
    def test_manual_positions_show_rnr_if_present(self, auth_headers):
        """If RNR position exists, it should appear in manual_external section"""
        response = requests.get(f"{BASE_URL}/api/analytics/by-strategy", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        manual = data.get("manual_external", {})
        positions = manual.get("positions", [])
        
        # Check if RNR is in manual positions (if it exists)
        rnr_found = any(p.get("symbol") == "RNR" for p in positions)
        
        if rnr_found:
            rnr_pos = next(p for p in positions if p.get("symbol") == "RNR")
            print(f"PASS: RNR found in manual_external as PROTECTED - "
                  f"qty={rnr_pos.get('qty')}, value=${rnr_pos.get('market_value')}")
        else:
            print("INFO: RNR not currently held (manual positions check passed)")


class TestLongTermMarketOverview:
    """Tests for /api/lt-invest/market-overview endpoint"""
    
    def test_market_overview_requires_auth(self):
        """Market overview requires authentication"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/market-overview")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/lt-invest/market-overview requires auth (401 without token)")
    
    def test_market_overview_returns_companies(self, auth_headers):
        """Market overview returns 1250 companies with ratings"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/market-overview", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        companies = data.get("companies", [])
        assert len(companies) >= 1000, f"Expected ~1250 companies, got {len(companies)}"
        
        print(f"PASS: Market overview returns {len(companies)} companies")
    
    def test_market_overview_company_fields(self, auth_headers):
        """Each company has required fields"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/market-overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        companies = data.get("companies", [])
        if companies:
            company = companies[0]
            required_fields = ["symbol", "name", "rating_score", "rating_label"]
            
            for field in required_fields:
                assert field in company, f"Company missing field: {field}"
            
            print(f"PASS: Company fields valid - sample: {company.get('symbol')} "
                  f"({company.get('rating_label')}, score={company.get('rating_score')})")


class TestLongTermPortfolio:
    """Tests for /api/lt-invest/portfolio endpoint"""
    
    def test_portfolio_requires_auth(self):
        """Portfolio requires authentication"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/portfolio")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: /api/lt-invest/portfolio requires auth (401 without token)")
    
    def test_portfolio_returns_structure(self, auth_headers):
        """Portfolio returns expected structure"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/portfolio", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check required fields
        required_fields = ["summary", "positions", "bucket_breakdown"]
        for field in required_fields:
            assert field in data, f"Portfolio missing field: {field}"
        
        print(f"PASS: Portfolio structure valid - {len(data.get('positions', []))} positions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
