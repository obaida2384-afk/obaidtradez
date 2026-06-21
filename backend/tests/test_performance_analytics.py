"""
Performance Analytics API Tests
Tests the 7 new analytics endpoints under /api/analytics/
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPerformanceAnalytics:
    """Test suite for Performance Tracker analytics endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        resp = requests.post(f"{BASE_URL}/api/auth/access", json={"code": "Bullishalmarkhan7.7"})
        assert resp.status_code == 200, f"Auth failed: {resp.text}"
        data = resp.json()
        assert data.get("success") is True, f"Auth not successful: {data}"
        self.token = data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_session_summary_endpoint(self):
        """GET /api/analytics/session-summary returns valid JSON with date, total_trades, message fields"""
        resp = requests.get(f"{BASE_URL}/api/analytics/session-summary", headers=self.headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        # Must have date field
        assert "date" in data, f"Missing 'date' field in response: {data}"
        
        # Must have either total_trades or message (when no trades)
        has_total_trades = "total_trades" in data
        has_message = "message" in data
        assert has_total_trades or has_message, f"Missing 'total_trades' or 'message' field: {data}"
        
        print(f"Session Summary: date={data.get('date')}, total_trades={data.get('total_trades')}, message={data.get('message')}")
    
    def test_full_report_endpoint(self):
        """GET /api/analytics/full-report returns all 6 sections"""
        resp = requests.get(f"{BASE_URL}/api/analytics/full-report", headers=self.headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        # Must have all 6 sections
        required_sections = [
            "session_summary",
            "trade_quality", 
            "pipeline_efficiency",
            "best_worst_trades",
            "risk_compliance",
            "regime_performance"
        ]
        
        for section in required_sections:
            assert section in data, f"Missing '{section}' section in full report: {list(data.keys())}"
        
        # Also check for report metadata
        assert "report_date" in data, f"Missing 'report_date' in full report"
        assert "generated_at" in data, f"Missing 'generated_at' in full report"
        
        print(f"Full Report: date={data.get('report_date')}, sections={list(data.keys())}")
    
    def test_pipeline_efficiency_endpoint(self):
        """GET /api/analytics/pipeline-efficiency returns date, message or total_cycles"""
        resp = requests.get(f"{BASE_URL}/api/analytics/pipeline-efficiency", headers=self.headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        # Must have date field
        assert "date" in data, f"Missing 'date' field: {data}"
        
        # Must have either message (no data) or total_cycles
        has_message = "message" in data
        has_total_cycles = "total_cycles" in data
        assert has_message or has_total_cycles, f"Missing 'message' or 'total_cycles': {data}"
        
        print(f"Pipeline Efficiency: date={data.get('date')}, total_cycles={data.get('total_cycles')}, message={data.get('message')}")
    
    def test_trade_quality_endpoint(self):
        """GET /api/analytics/trade-quality returns date field"""
        resp = requests.get(f"{BASE_URL}/api/analytics/trade-quality", headers=self.headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        # Must have date field
        assert "date" in data, f"Missing 'date' field: {data}"
        
        print(f"Trade Quality: date={data.get('date')}, message={data.get('message')}")
    
    def test_best_worst_trades_endpoint(self):
        """GET /api/analytics/best-worst-trades returns date field"""
        resp = requests.get(f"{BASE_URL}/api/analytics/best-worst-trades", headers=self.headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        # Must have date field
        assert "date" in data, f"Missing 'date' field: {data}"
        
        print(f"Best/Worst Trades: date={data.get('date')}, message={data.get('message')}")
    
    def test_risk_compliance_endpoint(self):
        """GET /api/analytics/risk-compliance returns date field"""
        resp = requests.get(f"{BASE_URL}/api/analytics/risk-compliance", headers=self.headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        # Must have date field
        assert "date" in data, f"Missing 'date' field: {data}"
        
        print(f"Risk Compliance: date={data.get('date')}, message={data.get('message')}")
    
    def test_regime_performance_endpoint(self):
        """GET /api/analytics/regime-performance returns date field"""
        resp = requests.get(f"{BASE_URL}/api/analytics/regime-performance", headers=self.headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        # Must have date field
        assert "date" in data, f"Missing 'date' field: {data}"
        
        print(f"Regime Performance: date={data.get('date')}, message={data.get('message')}")
    
    def test_all_endpoints_require_auth(self):
        """All analytics endpoints should require authentication"""
        endpoints = [
            "/api/analytics/session-summary",
            "/api/analytics/full-report",
            "/api/analytics/pipeline-efficiency",
            "/api/analytics/trade-quality",
            "/api/analytics/best-worst-trades",
            "/api/analytics/risk-compliance",
            "/api/analytics/regime-performance"
        ]
        
        for endpoint in endpoints:
            resp = requests.get(f"{BASE_URL}{endpoint}")  # No auth header
            assert resp.status_code == 401, f"Expected 401 for {endpoint} without auth, got {resp.status_code}"
        
        print("All 7 analytics endpoints correctly require authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
