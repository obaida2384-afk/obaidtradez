"""
Test suite for ObaidTradez TA-First Day Trading Engine Refactor
Tests the Technical Analysis-first approach where:
- TA (Polygon OHLCV) is the PRIMARY driver for day trades
- News is used ONLY as a confidence boost, never as a gate
- Pipeline has NO 'catalyst_passed' stage
- Stats include ta_analyzed, setups_found, filters_passed
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    def test_auth_access_with_valid_code(self):
        """Test POST /api/auth/access returns valid token with correct code"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={
            "code": "Bullishalmarkhan7.7"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Expected success=True, got {data}"
        assert "token" in data, f"Expected token in response, got {data}"
        assert len(data["token"]) > 0, "Token should not be empty"
        print(f"✓ Auth access successful, token length: {len(data['token'])}")


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for all tests"""
    response = requests.post(f"{BASE_URL}/api/auth/access", json={
        "code": "Bullishalmarkhan7.7"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestAutoTradeSettings:
    """Test auto-trade settings endpoint"""
    
    def test_settings_returns_dt_confidence_threshold_65(self, auth_headers):
        """Test GET /api/auto-trade/settings returns dt_confidence_threshold of 65"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/settings", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # The TA-first refactor lowered dt_confidence_threshold from 80 to 65
        assert "dt_confidence_threshold" in data, f"Expected dt_confidence_threshold in response, got {data.keys()}"
        assert data["dt_confidence_threshold"] == 65, f"Expected dt_confidence_threshold=65, got {data['dt_confidence_threshold']}"
        print(f"✓ Settings dt_confidence_threshold = {data['dt_confidence_threshold']}")


class TestAutoTradeScan:
    """Test auto-trade scan endpoint - TA-first refactor"""
    
    def test_scan_returns_required_fields(self, auth_headers):
        """Test GET /api/auto-trade/scan returns all required fields"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check required top-level fields
        required_fields = ["day_trades", "pipeline_funnel", "stats", "rejected_details", "dynamic_thresholds"]
        for field in required_fields:
            assert field in data, f"Expected '{field}' in response, got {data.keys()}"
        
        print(f"✓ Scan returns all required fields: {required_fields}")
    
    def test_scan_pipeline_funnel_has_no_catalyst_passed_stage(self, auth_headers):
        """Test pipeline_funnel has NO 'catalyst_passed' stage (TA-first, no catalyst gate)"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        funnel = data.get("pipeline_funnel", {}).get("funnel", {})
        
        # Should NOT have catalyst_passed (removed in TA-first refactor)
        assert "catalyst_passed" not in funnel, f"catalyst_passed should NOT be in funnel (TA-first), got {funnel.keys()}"
        
        # Should have these stages instead
        expected_stages = [
            "universe_scanned",
            "prefilter_passed",
            "ta_analyzed",
            "setup_found",
            "filters_passed",
            "confidence_passed",
            "risk_approved",
            "executed"
        ]
        
        for stage in expected_stages:
            assert stage in funnel, f"Expected '{stage}' in funnel, got {funnel.keys()}"
        
        print(f"✓ Pipeline funnel has correct stages (no catalyst_passed): {list(funnel.keys())}")
    
    def test_scan_stats_includes_ta_fields(self, auth_headers):
        """Test stats includes ta_analyzed, setups_found, filters_passed counts"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        stats = data.get("stats", {})
        
        # TA-first stats fields
        ta_fields = ["ta_analyzed", "setups_found", "filters_passed"]
        for field in ta_fields:
            assert field in stats, f"Expected '{field}' in stats, got {stats.keys()}"
            assert isinstance(stats[field], int), f"Expected {field} to be int, got {type(stats[field])}"
        
        print(f"✓ Stats includes TA fields: ta_analyzed={stats['ta_analyzed']}, setups_found={stats['setups_found']}, filters_passed={stats['filters_passed']}")
    
    def test_scan_day_trades_have_ta_key_indicators(self, auth_headers):
        """Test day_trades candidates have explanation with key_indicators containing TA fields"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        day_trades = data.get("day_trades", [])
        
        # Expected key_indicators from TA-first engine
        expected_indicators = [
            "direction", "best_setup", "structure", "rel_vol", "spread_pct",
            "rsi", "macd_crossover", "vwap_distance_pct", "mtf_aligned",
            "news_boost", "momentum_mode", "rr_ratio"
        ]
        
        if len(day_trades) > 0:
            candidate = day_trades[0]
            explanation = candidate.get("explanation", {})
            key_indicators = explanation.get("key_indicators", {})
            
            for indicator in expected_indicators:
                assert indicator in key_indicators, f"Expected '{indicator}' in key_indicators, got {key_indicators.keys()}"
            
            print(f"✓ Day trade candidate has all TA key_indicators: {list(key_indicators.keys())}")
        else:
            # No day trades is acceptable (after hours, market conditions)
            print(f"✓ No day trade candidates (acceptable - may be after hours). Stats: {data.get('stats', {})}")
    
    def test_scan_rejected_details_includes_day_trade_rejections(self, auth_headers):
        """Test rejected_details includes DAY_TRADE rejections with exact reject_reasons"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        rejected_details = data.get("rejected_details", [])
        
        # Check structure of rejected items
        if len(rejected_details) > 0:
            dt_rejected = [r for r in rejected_details if r.get("classification") == "DAY_TRADE"]
            
            if len(dt_rejected) > 0:
                item = dt_rejected[0]
                assert "symbol" in item, f"Expected 'symbol' in rejected item"
                assert "classification" in item, f"Expected 'classification' in rejected item"
                assert "explanation" in item, f"Expected 'explanation' in rejected item"
                
                explanation = item.get("explanation", {})
                assert "reject_reasons" in explanation, f"Expected 'reject_reasons' in explanation"
                
                print(f"✓ Rejected DAY_TRADE items have proper structure. Sample: {item['symbol']} - {explanation.get('reject_reasons', [])[:2]}")
            else:
                print(f"✓ No DAY_TRADE rejections in rejected_details (all passed or no TA data)")
        else:
            print(f"✓ No rejected_details (acceptable)")
    
    def test_scan_dynamic_thresholds_structure(self, auth_headers):
        """Test dynamic_thresholds has correct structure"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        dynamic = data.get("dynamic_thresholds", {})
        
        expected_fields = ["dt_threshold", "lt_threshold", "risk_mode", "regime_adjustment"]
        for field in expected_fields:
            assert field in dynamic, f"Expected '{field}' in dynamic_thresholds, got {dynamic.keys()}"
        
        # DT threshold should be around 65 (base) with regime adjustments
        dt_thresh = dynamic.get("dt_threshold", 0)
        assert 55 <= dt_thresh <= 80, f"Expected dt_threshold between 55-80, got {dt_thresh}"
        
        print(f"✓ Dynamic thresholds: dt={dynamic['dt_threshold']}, lt={dynamic['lt_threshold']}, risk_mode={dynamic['risk_mode']}")


class TestRefreshTA:
    """Test TA refresh endpoint"""
    
    def test_refresh_ta_triggers_background_refresh(self, auth_headers):
        """Test POST /api/auto-trade/refresh-ta triggers background TA refresh"""
        response = requests.post(f"{BASE_URL}/api/auto-trade/refresh-ta", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should return message and db_cached count
        assert "message" in data, f"Expected 'message' in response, got {data.keys()}"
        assert "db_cached" in data, f"Expected 'db_cached' in response, got {data.keys()}"
        assert isinstance(data["db_cached"], int), f"Expected db_cached to be int, got {type(data['db_cached'])}"
        
        print(f"✓ TA refresh triggered: {data['message']}, db_cached={data['db_cached']}")


class TestDynamicThresholdManager:
    """Test dynamic threshold behavior based on market regime"""
    
    def test_thresholds_adjust_based_on_regime(self, auth_headers):
        """Test that thresholds adjust based on market regime"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        dynamic = data.get("dynamic_thresholds", {})
        regime = data.get("market_regime", {}).get("regime", "neutral")
        
        dt_thresh = dynamic.get("dt_threshold", 65)
        
        # Verify threshold adjustments based on regime
        # Base is 65, bearish adds +5, bullish subtracts -5
        if regime == "bearish":
            assert dt_thresh >= 70, f"Expected dt_threshold >= 70 in bearish regime, got {dt_thresh}"
        elif regime == "bullish":
            assert dt_thresh <= 65, f"Expected dt_threshold <= 65 in bullish regime, got {dt_thresh}"
        
        print(f"✓ Regime '{regime}' -> dt_threshold={dt_thresh} (base=65)")


class TestPipelineFunnelStages:
    """Detailed tests for pipeline funnel stages"""
    
    def test_funnel_stages_are_ordered_correctly(self, auth_headers):
        """Test that funnel stages follow the correct order"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        funnel = data.get("pipeline_funnel", {}).get("funnel", {})
        
        # Expected stages (TA-first, no catalyst gate)
        expected_stages = [
            "universe_scanned",
            "prefilter_passed",
            "ta_analyzed",
            "setup_found",
            "filters_passed",
            "confidence_passed",
            "risk_approved",
            "executed"
        ]
        
        # Verify all stages exist
        for stage in expected_stages:
            assert stage in funnel, f"Missing stage '{stage}' in funnel"
        
        # Verify counts are non-negative integers
        for stage in expected_stages:
            count = funnel.get(stage, 0)
            assert isinstance(count, int), f"Stage '{stage}' should be int, got {type(count)}"
            assert count >= 0, f"Stage '{stage}' should be >= 0, got {count}"
        
        print(f"✓ Funnel has all expected stages: {list(funnel.keys())}")
    
    def test_funnel_has_bottleneck_detection(self, auth_headers):
        """Test that funnel includes bottleneck detection"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        pipeline_funnel = data.get("pipeline_funnel", {})
        
        # Should have bottleneck field
        assert "bottleneck" in pipeline_funnel, f"Expected 'bottleneck' in pipeline_funnel"
        
        # Should have top_rejections
        assert "top_rejections" in pipeline_funnel, f"Expected 'top_rejections' in pipeline_funnel"
        
        print(f"✓ Funnel has bottleneck='{pipeline_funnel.get('bottleneck')}' and top_rejections")


class TestTAEngineIntegration:
    """Test TA engine integration with scan"""
    
    def test_scan_uses_ta_signals_from_db(self, auth_headers):
        """Test that scan reads from ta_signals DB cache"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        stats = data.get("stats", {})
        ta_analyzed = stats.get("ta_analyzed", 0)
        
        # If we have cached TA signals, ta_analyzed should be > 0
        # (Note: may be 0 if no TA refresh has been run)
        print(f"✓ TA analyzed count: {ta_analyzed} (from DB cache)")
        
        # Check that day trades have TA-derived fields
        day_trades = data.get("day_trades", [])
        if len(day_trades) > 0:
            candidate = day_trades[0]
            signal = candidate.get("signal", {})
            
            # TA-derived fields
            assert "direction" in signal or "direction" in candidate, "Expected 'direction' from TA"
            assert "best_setup" in signal or "best_setup" in candidate, "Expected 'best_setup' from TA"
            
            print(f"✓ Day trade candidate has TA-derived fields: direction={candidate.get('direction')}, best_setup={candidate.get('best_setup')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
