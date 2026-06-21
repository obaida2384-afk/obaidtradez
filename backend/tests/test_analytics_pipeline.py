"""
Test suite for Trade Log Analytics, LT Pipeline Transparency, and Momentum Diagnostics.
Tests the new execution validation logging and analytics dashboard features.
"""
import pytest
import requests
import os

# Load URL from frontend/.env via conftest.py
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSetup:
    """Setup and authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        resp = requests.post(f"{BASE_URL}/api/auth/access", json={"code": "Bullishalmarkhan7.7"})
        assert resp.status_code == 200, f"Auth failed: {resp.text}"
        data = resp.json()
        assert data.get("success") is True
        return data.get("token")
    
    def test_auth_works(self, auth_token):
        """Verify authentication is working"""
        assert auth_token is not None
        assert len(auth_token) > 10


class TestTradeLogEndpoint:
    """Tests for /api/auto-trade/trade-log endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/access", json={"code": "Bullishalmarkhan7.7"})
        return resp.json().get("token")
    
    def test_trade_log_returns_200(self, auth_token):
        """Trade log endpoint returns 200"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/trade-log?limit=50",
                           headers={"Authorization": f"Bearer {auth_token}"})
        assert resp.status_code == 200
    
    def test_trade_log_returns_list(self, auth_token):
        """Trade log returns a list"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/trade-log?limit=50",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        assert isinstance(data, list)
    
    def test_trade_log_entry_has_new_fields(self, auth_token):
        """Trade log entries have new execution validation fields"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/trade-log?limit=50",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        # If there are entries, check the schema
        if len(data) > 0:
            entry = data[0]
            # New fields for execution validation
            expected_fields = [
                "executed", "skip_reason", "slippage", "slippage_pct",
                "signal_timestamp", "execution_timestamp", "time_elapsed_ms",
                "actual_entry_price", "actual_exit_reason"
            ]
            for field in expected_fields:
                assert field in entry, f"Missing field: {field}"


class TestAnalyticsEndpoint:
    """Tests for /api/auto-trade/analytics endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/access", json={"code": "Bullishalmarkhan7.7"})
        return resp.json().get("token")
    
    def test_analytics_returns_200(self, auth_token):
        """Analytics endpoint returns 200"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        assert resp.status_code == 200
    
    def test_analytics_has_summary_stats(self, auth_token):
        """Analytics has total_trades, win_rate, avg_win, avg_loss"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        assert "total_trades" in data
        assert "win_rate" in data
        assert "avg_win" in data
        assert "avg_loss" in data
    
    def test_analytics_has_r_multiple(self, auth_token):
        """Analytics has avg_r_multiple"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        assert "avg_r_multiple" in data
    
    def test_analytics_has_total_pnl(self, auth_token):
        """Analytics has total_pnl"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        assert "total_pnl" in data
    
    def test_analytics_has_max_drawdown(self, auth_token):
        """Analytics has max_drawdown"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        assert "max_drawdown" in data
    
    def test_analytics_has_long_vs_short(self, auth_token):
        """Analytics has long_vs_short breakdown"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        assert "long_vs_short" in data
        lvs = data["long_vs_short"]
        assert "long" in lvs
        assert "short" in lvs
    
    def test_analytics_has_by_setup_type(self, auth_token):
        """Analytics has by_setup_type breakdown"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        assert "by_setup_type" in data
    
    def test_analytics_has_by_confidence_band(self, auth_token):
        """Analytics has by_confidence_band breakdown"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        assert "by_confidence_band" in data
    
    def test_analytics_has_by_session(self, auth_token):
        """Analytics has by_session breakdown"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        assert "by_session" in data
    
    def test_analytics_has_pnl_curve(self, auth_token):
        """Analytics has pnl_curve"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        assert "pnl_curve" in data
        assert isinstance(data["pnl_curve"], list)
    
    def test_analytics_has_skip_reasons(self, auth_token):
        """Analytics has skip_reasons"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        assert "skip_reasons" in data
    
    def test_analytics_has_rejection_reasons(self, auth_token):
        """Analytics has rejection_reasons"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        assert "rejection_reasons" in data
    
    def test_analytics_has_slippage(self, auth_token):
        """Analytics has slippage stats"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        assert "slippage" in data
        slippage = data["slippage"]
        assert "avg_pct" in slippage
        assert "max_pct" in slippage
        assert "data_points" in slippage
    
    def test_analytics_has_execution_timing(self, auth_token):
        """Analytics has execution_timing stats"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        assert "execution_timing" in data
        timing = data["execution_timing"]
        assert "avg_ms" in timing
        assert "data_points" in timing


class TestScanLTPipeline:
    """Tests for lt_pipeline field in /api/auto-trade/scan"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/access", json={"code": "Bullishalmarkhan7.7"})
        return resp.json().get("token")
    
    @pytest.fixture(scope="class")
    def scan_data(self, auth_token):
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan",
                           headers={"Authorization": f"Bearer {auth_token}"})
        return resp.json()
    
    def test_scan_has_lt_pipeline(self, scan_data):
        """Scan response has lt_pipeline field"""
        assert "lt_pipeline" in scan_data
    
    def test_lt_pipeline_has_total_evaluated(self, scan_data):
        """lt_pipeline has total_evaluated"""
        lt = scan_data.get("lt_pipeline", {})
        assert "total_evaluated" in lt
    
    def test_lt_pipeline_has_fundamental_passed(self, scan_data):
        """lt_pipeline has fundamental_passed"""
        lt = scan_data.get("lt_pipeline", {})
        assert "fundamental_passed" in lt
    
    def test_lt_pipeline_has_valuation_passed(self, scan_data):
        """lt_pipeline has valuation_passed"""
        lt = scan_data.get("lt_pipeline", {})
        assert "valuation_passed" in lt
    
    def test_lt_pipeline_has_timing_passed(self, scan_data):
        """lt_pipeline has timing_passed"""
        lt = scan_data.get("lt_pipeline", {})
        assert "timing_passed" in lt
    
    def test_lt_pipeline_has_final_candidates(self, scan_data):
        """lt_pipeline has final_candidates"""
        lt = scan_data.get("lt_pipeline", {})
        assert "final_candidates" in lt
    
    def test_lt_pipeline_has_rejection_reasons(self, scan_data):
        """lt_pipeline has rejection_reasons"""
        lt = scan_data.get("lt_pipeline", {})
        assert "rejection_reasons" in lt
    
    def test_lt_pipeline_has_top_missed(self, scan_data):
        """lt_pipeline has top_missed opportunities"""
        lt = scan_data.get("lt_pipeline", {})
        assert "top_missed" in lt
        assert isinstance(lt["top_missed"], list)
    
    def test_lt_pipeline_has_confidence_distribution(self, scan_data):
        """lt_pipeline has confidence_distribution"""
        lt = scan_data.get("lt_pipeline", {})
        assert "confidence_distribution" in lt


class TestScanMomentumDiagnostics:
    """Tests for momentum_diagnostics field in /api/auto-trade/scan"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/access", json={"code": "Bullishalmarkhan7.7"})
        return resp.json().get("token")
    
    @pytest.fixture(scope="class")
    def scan_data(self, auth_token):
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan",
                           headers={"Authorization": f"Bearer {auth_token}"})
        return resp.json()
    
    def test_scan_has_momentum_diagnostics(self, scan_data):
        """Scan response has momentum_diagnostics field"""
        assert "momentum_diagnostics" in scan_data
    
    def test_momentum_diagnostics_has_total_momentum_candidates(self, scan_data):
        """momentum_diagnostics has total_momentum_candidates"""
        md = scan_data.get("momentum_diagnostics", {})
        assert "total_momentum_candidates" in md
    
    def test_momentum_diagnostics_has_total_momentum_bypassed(self, scan_data):
        """momentum_diagnostics has total_momentum_bypassed"""
        md = scan_data.get("momentum_diagnostics", {})
        assert "total_momentum_bypassed" in md
    
    def test_momentum_diagnostics_has_total_near_misses(self, scan_data):
        """momentum_diagnostics has total_near_misses"""
        md = scan_data.get("momentum_diagnostics", {})
        assert "total_near_misses" in md
    
    def test_momentum_diagnostics_has_top_near_misses(self, scan_data):
        """momentum_diagnostics has top_near_misses list"""
        md = scan_data.get("momentum_diagnostics", {})
        assert "top_near_misses" in md
        assert isinstance(md["top_near_misses"], list)
    
    def test_near_miss_entry_structure(self, scan_data):
        """Near miss entries have required fields"""
        md = scan_data.get("momentum_diagnostics", {})
        near_misses = md.get("top_near_misses", [])
        if len(near_misses) > 0:
            nm = near_misses[0]
            assert "symbol" in nm
            assert "rel_vol" in nm
            assert "spread_pct" in nm
            assert "vwap_above" in nm
            assert "blocked_conditions" in nm


class TestAnalyticsZeroedData:
    """Verify analytics returns zeroed data when no trades logged (expected behavior)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/access", json={"code": "Bullishalmarkhan7.7"})
        return resp.json().get("token")
    
    def test_analytics_returns_valid_structure_even_with_no_data(self, auth_token):
        """Analytics returns valid structure even with no logged trades"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        
        # All required fields should exist
        required_fields = [
            "total_trades", "total_executed", "total_skipped", "total_closed", "total_open",
            "win_rate", "avg_win", "avg_loss", "avg_r_multiple", "total_pnl", "max_drawdown",
            "long_vs_short", "by_setup_type", "by_confidence_band", "by_session",
            "pnl_curve", "skip_reasons", "rejection_reasons", "slippage", "execution_timing"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    def test_analytics_numeric_fields_are_numbers(self, auth_token):
        """Numeric fields are actual numbers (not None or strings)"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/analytics",
                           headers={"Authorization": f"Bearer {auth_token}"})
        data = resp.json()
        
        numeric_fields = ["total_trades", "win_rate", "avg_win", "avg_loss", 
                         "avg_r_multiple", "total_pnl", "max_drawdown"]
        for field in numeric_fields:
            assert isinstance(data[field], (int, float)), f"{field} should be numeric"
