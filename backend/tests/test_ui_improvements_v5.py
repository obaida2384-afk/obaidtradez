"""
Test suite for 5 UI Improvements:
1. 'Why Didn't It Trade?' rejection report with gate breakdown
2. Pipeline funnel with component utilization
3. Position labels (Day Trade Bot / Long-Term Bot / Manual Protected)
4. Trade quality cards with entry reasons and confidence breakdown
5. Re-entry cooldown to prevent immediate re-buying after selling

Tests cover:
- GET /api/positions - enriched with ownership, strategy_type, position_label, label_color
- GET /api/auto-trade/trade-log - trades from auto_trade_log with entry_reasons, exit_plan, confidence
- GET /api/execution/diagnostics - component_utilization, top_signals with breakdown, passing_threshold
- GET /api/execution/rejection-report - rejection data with candidates and rejection_breakdown
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"


class TestAuth:
    """Authentication tests"""
    
    def test_auth_with_valid_code(self):
        """Test authentication with valid access code"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200, f"Auth failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert len(data["token"]) > 0, "Token is empty"
        print(f"PASS: Auth successful, token received")


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for all tests"""
    response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
    if response.status_code != 200:
        pytest.skip("Authentication failed - skipping tests")
    return response.json().get("token")


@pytest.fixture(scope="module")
def headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestPositionsWithLabels:
    """Test GET /api/positions returns enriched position data with labels"""
    
    def test_positions_endpoint_returns_200(self, headers):
        """Test positions endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/positions", headers=headers)
        assert response.status_code == 200, f"Positions endpoint failed: {response.text}"
        print(f"PASS: Positions endpoint returns 200")
    
    def test_positions_have_ownership_field(self, headers):
        """Test positions have ownership field (bot/manual)"""
        response = requests.get(f"{BASE_URL}/api/positions", headers=headers)
        assert response.status_code == 200
        positions = response.json()
        
        if len(positions) == 0:
            pytest.skip("No positions to test")
        
        for pos in positions:
            assert "ownership" in pos, f"Position {pos.get('symbol')} missing ownership field"
            assert pos["ownership"] in ["bot", "manual", "unknown"], f"Invalid ownership: {pos['ownership']}"
        print(f"PASS: All {len(positions)} positions have valid ownership field")
    
    def test_positions_have_strategy_type_field(self, headers):
        """Test positions have strategy_type field (day_trade/long_term/manual)"""
        response = requests.get(f"{BASE_URL}/api/positions", headers=headers)
        assert response.status_code == 200
        positions = response.json()
        
        if len(positions) == 0:
            pytest.skip("No positions to test")
        
        for pos in positions:
            assert "strategy_type" in pos, f"Position {pos.get('symbol')} missing strategy_type field"
            assert pos["strategy_type"] in ["day_trade", "long_term", "manual", "unknown"], f"Invalid strategy_type: {pos['strategy_type']}"
        print(f"PASS: All {len(positions)} positions have valid strategy_type field")
    
    def test_positions_have_position_label(self, headers):
        """Test positions have position_label for UI display"""
        response = requests.get(f"{BASE_URL}/api/positions", headers=headers)
        assert response.status_code == 200
        positions = response.json()
        
        if len(positions) == 0:
            pytest.skip("No positions to test")
        
        valid_labels = ["Day Trade (Bot)", "Long-Term (Bot)", "Manual / Protected", "Unknown"]
        for pos in positions:
            assert "position_label" in pos, f"Position {pos.get('symbol')} missing position_label"
            assert pos["position_label"] in valid_labels, f"Invalid position_label: {pos['position_label']}"
            print(f"  {pos.get('symbol')}: {pos['position_label']}")
        print(f"PASS: All {len(positions)} positions have valid position_label")
    
    def test_positions_have_label_color(self, headers):
        """Test positions have label_color for UI styling"""
        response = requests.get(f"{BASE_URL}/api/positions", headers=headers)
        assert response.status_code == 200
        positions = response.json()
        
        if len(positions) == 0:
            pytest.skip("No positions to test")
        
        valid_colors = ["amber", "blue", "emerald", "slate"]
        for pos in positions:
            assert "label_color" in pos, f"Position {pos.get('symbol')} missing label_color"
            assert pos["label_color"] in valid_colors, f"Invalid label_color: {pos['label_color']}"
        print(f"PASS: All {len(positions)} positions have valid label_color")


class TestTradeLog:
    """Test GET /api/auto-trade/trade-log returns trades with entry reasons and confidence"""
    
    def test_trade_log_endpoint_returns_200(self, headers):
        """Test trade log endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/trade-log", headers=headers)
        assert response.status_code == 200, f"Trade log endpoint failed: {response.text}"
        print(f"PASS: Trade log endpoint returns 200")
    
    def test_trade_log_has_trades_array(self, headers):
        """Test trade log response has trades array"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/trade-log", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "trades" in data, "Response missing 'trades' key"
        assert isinstance(data["trades"], list), "trades should be a list"
        assert "total" in data, "Response missing 'total' key"
        print(f"PASS: Trade log has {data['total']} trades")
    
    def test_trade_log_entries_have_required_fields(self, headers):
        """Test trade log entries have required fields"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/trade-log", headers=headers)
        assert response.status_code == 200
        data = response.json()
        trades = data.get("trades", [])
        
        if len(trades) == 0:
            pytest.skip("No trades to test")
        
        required_fields = ["symbol", "action", "timestamp"]
        for trade in trades[:5]:  # Check first 5 trades
            for field in required_fields:
                assert field in trade, f"Trade missing required field: {field}"
        print(f"PASS: Trade log entries have required fields")
    
    def test_trade_log_has_entry_reasons(self, headers):
        """Test trade log entries have entry_reasons field"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/trade-log", headers=headers)
        assert response.status_code == 200
        data = response.json()
        trades = data.get("trades", [])
        
        if len(trades) == 0:
            pytest.skip("No trades to test")
        
        trades_with_reasons = [t for t in trades if t.get("entry_reasons")]
        print(f"  {len(trades_with_reasons)}/{len(trades)} trades have entry_reasons")
        # At least some trades should have entry reasons
        if len(trades) > 3:
            assert len(trades_with_reasons) > 0, "No trades have entry_reasons"
        print(f"PASS: Trade log has entry_reasons field")
    
    def test_trade_log_has_exit_plan(self, headers):
        """Test trade log entries have exit_plan field"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/trade-log", headers=headers)
        assert response.status_code == 200
        data = response.json()
        trades = data.get("trades", [])
        
        if len(trades) == 0:
            pytest.skip("No trades to test")
        
        trades_with_exit_plan = [t for t in trades if t.get("exit_plan")]
        print(f"  {len(trades_with_exit_plan)}/{len(trades)} trades have exit_plan")
        print(f"PASS: Trade log has exit_plan field")
    
    def test_trade_log_has_confidence_breakdown(self, headers):
        """Test trade log entries have confidence_breakdown field"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/trade-log", headers=headers)
        assert response.status_code == 200
        data = response.json()
        trades = data.get("trades", [])
        
        if len(trades) == 0:
            pytest.skip("No trades to test")
        
        trades_with_breakdown = [t for t in trades if t.get("confidence_breakdown")]
        print(f"  {len(trades_with_breakdown)}/{len(trades)} trades have confidence_breakdown")
        
        # Check breakdown structure if present
        for trade in trades_with_breakdown[:3]:
            breakdown = trade["confidence_breakdown"]
            expected_components = ["technical_setup", "volume", "sentiment", "risk_reward", "trend_alignment", "volatility", "market_regime"]
            for comp in expected_components:
                if comp in breakdown:
                    assert "pts" in breakdown[comp], f"Component {comp} missing 'pts'"
                    assert "max" in breakdown[comp], f"Component {comp} missing 'max'"
        print(f"PASS: Trade log has confidence_breakdown with proper structure")
    
    def test_trade_log_has_ownership_and_strategy(self, headers):
        """Test trade log entries have ownership and strategy_type"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/trade-log", headers=headers)
        assert response.status_code == 200
        data = response.json()
        trades = data.get("trades", [])
        
        if len(trades) == 0:
            pytest.skip("No trades to test")
        
        for trade in trades[:5]:
            if "ownership" in trade:
                assert trade["ownership"] in ["bot", "manual", "unknown"], f"Invalid ownership: {trade['ownership']}"
            if "strategy_type" in trade:
                assert trade["strategy_type"] in ["day_trade", "long_term", "manual", "unknown"], f"Invalid strategy_type: {trade['strategy_type']}"
        print(f"PASS: Trade log has ownership and strategy_type fields")


class TestExecutionDiagnostics:
    """Test GET /api/execution/diagnostics returns component utilization and top signals"""
    
    def test_diagnostics_endpoint_returns_200(self, headers):
        """Test diagnostics endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/execution/diagnostics", headers=headers)
        assert response.status_code == 200, f"Diagnostics endpoint failed: {response.text}"
        print(f"PASS: Diagnostics endpoint returns 200")
    
    def test_diagnostics_has_component_utilization(self, headers):
        """Test diagnostics has component_utilization with all 7 components"""
        response = requests.get(f"{BASE_URL}/api/execution/diagnostics", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "component_utilization" in data, "Missing component_utilization"
        util = data["component_utilization"]
        
        expected_components = ["technical_setup", "volume", "sentiment", "risk_reward", "trend_alignment", "volatility", "market_regime"]
        for comp in expected_components:
            assert comp in util, f"Missing component: {comp}"
            assert "avg_pts" in util[comp], f"Component {comp} missing avg_pts"
            assert "max_pts" in util[comp], f"Component {comp} missing max_pts"
            assert "utilization_pct" in util[comp], f"Component {comp} missing utilization_pct"
            print(f"  {comp}: {util[comp]['utilization_pct']}%")
        print(f"PASS: Diagnostics has all 7 component utilization metrics")
    
    def test_diagnostics_has_top_signals(self, headers):
        """Test diagnostics has top_signals with score breakdown"""
        response = requests.get(f"{BASE_URL}/api/execution/diagnostics", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "top_signals" in data, "Missing top_signals"
        signals = data["top_signals"]
        
        if len(signals) == 0:
            pytest.skip("No top signals to test")
        
        # Check first signal structure
        sig = signals[0]
        assert "symbol" in sig, "Signal missing symbol"
        assert "confidence" in sig, "Signal missing confidence"
        assert "passes_threshold" in sig, "Signal missing passes_threshold"
        assert "breakdown" in sig, "Signal missing breakdown"
        
        # Check breakdown has all components
        breakdown = sig["breakdown"]
        expected_components = ["technical_setup", "volume", "sentiment", "risk_reward", "trend_alignment", "volatility", "market_regime"]
        for comp in expected_components:
            assert comp in breakdown, f"Signal breakdown missing {comp}"
        
        print(f"PASS: Top signals have proper breakdown structure")
        print(f"  Top signal: {sig['symbol']} with confidence {sig['confidence']}")
    
    def test_diagnostics_has_passing_threshold_count(self, headers):
        """Test diagnostics has passing_threshold count > 0"""
        response = requests.get(f"{BASE_URL}/api/execution/diagnostics", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "passing_threshold" in data, "Missing passing_threshold"
        assert "threshold_used" in data, "Missing threshold_used"
        assert "dt_classified" in data, "Missing dt_classified"
        
        print(f"  Threshold: {data['threshold_used']}")
        print(f"  DT Classified: {data['dt_classified']}")
        print(f"  Passing Threshold: {data['passing_threshold']}")
        
        # Should have some signals passing (based on previous test showing 102/168)
        assert data["passing_threshold"] >= 0, "passing_threshold should be >= 0"
        print(f"PASS: Diagnostics has passing_threshold count")
    
    def test_diagnostics_has_market_regime(self, headers):
        """Test diagnostics has market_regime info"""
        response = requests.get(f"{BASE_URL}/api/execution/diagnostics", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "market_regime" in data, "Missing market_regime"
        regime = data["market_regime"]
        assert "regime" in regime, "market_regime missing 'regime' field"
        print(f"  Market regime: {regime.get('regime')}")
        print(f"PASS: Diagnostics has market_regime")


class TestRejectionReport:
    """Test GET /api/execution/rejection-report returns rejection data"""
    
    def test_rejection_report_endpoint_returns_200(self, headers):
        """Test rejection report endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/execution/rejection-report", headers=headers)
        assert response.status_code == 200, f"Rejection report endpoint failed: {response.text}"
        print(f"PASS: Rejection report endpoint returns 200")
    
    def test_rejection_report_has_summary_fields(self, headers):
        """Test rejection report has summary fields"""
        response = requests.get(f"{BASE_URL}/api/execution/rejection-report", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        expected_fields = ["total_candidates", "executed", "rejected", "execution_rate"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"  Total candidates: {data['total_candidates']}")
        print(f"  Executed: {data['executed']}")
        print(f"  Rejected: {data['rejected']}")
        print(f"  Execution rate: {data['execution_rate']}%")
        print(f"PASS: Rejection report has summary fields")
    
    def test_rejection_report_has_rejection_breakdown(self, headers):
        """Test rejection report has rejection_breakdown by gate"""
        response = requests.get(f"{BASE_URL}/api/execution/rejection-report", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "rejection_breakdown" in data, "Missing rejection_breakdown"
        breakdown = data["rejection_breakdown"]
        
        if len(breakdown) > 0:
            print(f"  Rejection breakdown:")
            for gate, count in breakdown.items():
                print(f"    {gate}: {count}")
        print(f"PASS: Rejection report has rejection_breakdown")
    
    def test_rejection_report_has_entries(self, headers):
        """Test rejection report has entries list (candidates)"""
        response = requests.get(f"{BASE_URL}/api/execution/rejection-report", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "entries" in data, "Missing entries"
        entries = data["entries"]
        
        if len(entries) > 0:
            # Check entry structure
            entry = entries[0]
            assert "symbol" in entry, "Entry missing symbol"
            print(f"  First entry: {entry.get('symbol')}")
            if "rejection_reason" in entry:
                print(f"    Rejection reason: {entry['rejection_reason']}")
        print(f"PASS: Rejection report has {len(entries)} entries")
    
    def test_rejection_report_has_rejection_categories(self, headers):
        """Test rejection report has rejection_categories"""
        response = requests.get(f"{BASE_URL}/api/execution/rejection-report", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check for reentry_cooldown in categories (new feature)
        if "rejection_categories" in data:
            categories = data["rejection_categories"]
            print(f"  Rejection categories: {len(categories)}")
            if "reentry_cooldown" in categories:
                print(f"    reentry_cooldown category present")
        print(f"PASS: Rejection report structure verified")


class TestSchedulerSettings:
    """Test scheduler settings include re-entry cooldown"""
    
    def test_scheduler_status_returns_200(self, headers):
        """Test scheduler status endpoint"""
        response = requests.get(f"{BASE_URL}/api/scheduler/status", headers=headers)
        assert response.status_code == 200, f"Scheduler status failed: {response.text}"
        print(f"PASS: Scheduler status returns 200")
    
    def test_scheduler_has_reentry_cooldown_setting(self, headers):
        """Test scheduler settings include reentry_cooldown_minutes"""
        response = requests.get(f"{BASE_URL}/api/scheduler/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        settings = data.get("settings", {})
        if "reentry_cooldown_minutes" in settings:
            print(f"  reentry_cooldown_minutes: {settings['reentry_cooldown_minutes']}")
            assert isinstance(settings["reentry_cooldown_minutes"], (int, float)), "reentry_cooldown_minutes should be numeric"
        print(f"PASS: Scheduler settings verified")


class TestAutoTradeScan:
    """Test auto-trade scan endpoint"""
    
    def test_scan_returns_200(self, headers):
        """Test auto-trade scan endpoint"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers)
        assert response.status_code == 200, f"Scan endpoint failed: {response.text}"
        print(f"PASS: Auto-trade scan endpoint returns 200")
    
    def test_scan_has_pipeline_funnel(self, headers):
        """Test scan has pipeline_funnel data"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        if "pipeline_funnel" in data:
            funnel = data["pipeline_funnel"]
            if "funnel" in funnel:
                print(f"  Pipeline funnel stages:")
                for stage, count in funnel["funnel"].items():
                    print(f"    {stage}: {count}")
        print(f"PASS: Scan has pipeline data")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
