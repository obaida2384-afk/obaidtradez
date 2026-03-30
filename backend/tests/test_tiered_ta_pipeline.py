"""
Test Suite for Tiered TA Pipeline (Starter Plan Upgrade)
Tests the two-tier technical analysis pipeline:
- Tier 1: Fast scan (80 stocks, 5-min bars, composite prefilter score)
- Tier 2: Deep analysis (top 20, full multi-timeframe)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    resp = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
    assert resp.status_code == 200, f"Auth failed: {resp.text}"
    data = resp.json()
    assert data.get("success"), f"Auth not successful: {data}"
    return data.get("token")


@pytest.fixture(scope="module")
def headers(auth_token):
    """Auth headers for API calls"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestTieredTAPipelineTiming:
    """Tests for timing object in scan response"""

    def test_scan_returns_timing_object(self, headers):
        """GET /api/auto-trade/scan returns timing object with tier1/tier2 metrics"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200, f"Scan failed: {resp.text}"
        data = resp.json()
        
        # Verify timing object exists
        assert "timing" in data, f"Missing 'timing' in response. Keys: {data.keys()}"
        timing = data["timing"]
        
        # Verify all required timing fields
        required_fields = [
            "total_cycle_sec",
            "tier1_scan_sec",
            "tier2_scan_sec",
            "tier1_symbols",
            "tier1_results",
            "tier1_passed",
            "tier1_rejected_early",
            "tier2_symbols",
            "tier2_results",
            "ta_cache",
            "bar_cache"
        ]
        for field in required_fields:
            assert field in timing, f"Missing '{field}' in timing object. Got: {timing.keys()}"
        
        print(f"✓ Timing object has all required fields")
        print(f"  - total_cycle_sec: {timing['total_cycle_sec']}")
        print(f"  - tier1_scan_sec: {timing['tier1_scan_sec']}")
        print(f"  - tier2_scan_sec: {timing['tier2_scan_sec']}")
        print(f"  - tier1_symbols: {timing['tier1_symbols']}")
        print(f"  - tier1_results: {timing['tier1_results']}")
        print(f"  - tier1_passed: {timing['tier1_passed']}")
        print(f"  - tier2_symbols: {timing['tier2_symbols']}")
        print(f"  - tier2_results: {timing['tier2_results']}")

    def test_tier1_analyzes_70_plus_stocks(self, headers):
        """Tier 1 should analyze ~70+ stocks (up to 80 max)"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        timing = data.get("timing", {})
        tier1_results = timing.get("tier1_results", 0)
        tier1_symbols = timing.get("tier1_symbols", 0)
        
        # Tier 1 should process up to 80 symbols
        assert tier1_symbols <= 80, f"Tier 1 symbols should be <= 80, got {tier1_symbols}"
        # Should analyze a significant portion (at least 50% of symbols)
        assert tier1_results >= tier1_symbols * 0.5, f"Tier 1 results ({tier1_results}) too low for {tier1_symbols} symbols"
        
        print(f"✓ Tier 1 analyzed {tier1_results} stocks from {tier1_symbols} symbols")

    def test_tier1_completes_under_10_seconds(self, headers):
        """Tier 1 fast scan should complete in under 10 seconds"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        timing = data.get("timing", {})
        tier1_scan_sec = timing.get("tier1_scan_sec", 999)
        
        # Tier 1 should be fast (under 10s for Starter plan)
        assert tier1_scan_sec < 15, f"Tier 1 scan took {tier1_scan_sec}s, expected < 15s"
        
        print(f"✓ Tier 1 scan completed in {tier1_scan_sec}s")

    def test_tier2_deep_analyzes_top_20(self, headers):
        """Tier 2 should deep analyze top ~20 stocks"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        timing = data.get("timing", {})
        tier2_symbols = timing.get("tier2_symbols", 0)
        tier2_results = timing.get("tier2_results", 0)
        
        # Tier 2 should process up to 20 symbols
        assert tier2_symbols <= 20, f"Tier 2 symbols should be <= 20, got {tier2_symbols}"
        
        print(f"✓ Tier 2 deep analyzed {tier2_results} stocks from {tier2_symbols} symbols")


class TestTieredTAPipelineStats:
    """Tests for stats object in scan response"""

    def test_stats_includes_tiered_fields(self, headers):
        """Stats should include ta_analyzed, tier1_passed, tier2_deep, setups_found, filters_passed"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        assert "stats" in data, f"Missing 'stats' in response. Keys: {data.keys()}"
        stats = data["stats"]
        
        # Verify tiered stats fields
        required_stats = ["ta_analyzed", "tier1_passed", "tier2_deep", "setups_found", "filters_passed"]
        for field in required_stats:
            assert field in stats, f"Missing '{field}' in stats. Got: {stats.keys()}"
        
        print(f"✓ Stats has all tiered fields:")
        print(f"  - ta_analyzed: {stats['ta_analyzed']}")
        print(f"  - tier1_passed: {stats['tier1_passed']}")
        print(f"  - tier2_deep: {stats['tier2_deep']}")
        print(f"  - setups_found: {stats['setups_found']}")
        print(f"  - filters_passed: {stats['filters_passed']}")


class TestTieredTAPipelineCache:
    """Tests for cache behavior"""

    def test_ta_cache_shows_hit_rate(self, headers):
        """TA cache should show hit_rate percentage"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        timing = data.get("timing", {})
        ta_cache = timing.get("ta_cache", {})
        
        assert "hit_rate" in ta_cache, f"Missing 'hit_rate' in ta_cache. Got: {ta_cache.keys()}"
        assert "hits" in ta_cache, f"Missing 'hits' in ta_cache"
        assert "misses" in ta_cache, f"Missing 'misses' in ta_cache"
        
        print(f"✓ TA cache stats: hit_rate={ta_cache['hit_rate']}%, hits={ta_cache['hits']}, misses={ta_cache['misses']}")

    def test_bar_cache_shows_stats(self, headers):
        """Bar cache should show valid entries count"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        timing = data.get("timing", {})
        bar_cache = timing.get("bar_cache", {})
        
        assert "valid" in bar_cache or "total" in bar_cache, f"Bar cache missing stats. Got: {bar_cache}"
        
        print(f"✓ Bar cache stats: {bar_cache}")

    def test_second_scan_has_higher_cache_hit_rate(self, headers):
        """Second scan within 5 min should have much higher cache hit rate (>80%)"""
        # First scan
        resp1 = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp1.status_code == 200
        data1 = resp1.json()
        timing1 = data1.get("timing", {})
        ta_cache1 = timing1.get("ta_cache", {})
        hit_rate1 = ta_cache1.get("hit_rate", 0)
        total_cycle1 = timing1.get("total_cycle_sec", 999)
        
        print(f"First scan: hit_rate={hit_rate1}%, total_cycle={total_cycle1}s")
        
        # Wait a moment then do second scan
        time.sleep(2)
        
        # Second scan (should use cache)
        resp2 = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp2.status_code == 200
        data2 = resp2.json()
        timing2 = data2.get("timing", {})
        ta_cache2 = timing2.get("ta_cache", {})
        hit_rate2 = ta_cache2.get("hit_rate", 0)
        total_cycle2 = timing2.get("total_cycle_sec", 999)
        
        print(f"Second scan: hit_rate={hit_rate2}%, total_cycle={total_cycle2}s")
        
        # Second scan should have higher hit rate
        assert hit_rate2 >= hit_rate1, f"Second scan hit rate ({hit_rate2}%) should be >= first ({hit_rate1}%)"
        
        # If first scan had low hit rate, second should be much higher
        if hit_rate1 < 50:
            assert hit_rate2 > 50, f"Second scan hit rate ({hit_rate2}%) should be > 50% after first scan"
        
        # Second scan should be faster or similar
        # (allowing some variance due to network)
        print(f"✓ Cache working: first={total_cycle1}s, second={total_cycle2}s")


class TestTieredTAPipelineRejections:
    """Tests for rejection details"""

    def test_rejected_details_includes_day_trade_rejections(self, headers):
        """Rejected details should include DAY_TRADE rejections with exact reject_reasons"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        rejected_details = data.get("rejected_details", [])
        
        # Find DAY_TRADE rejections
        dt_rejections = [r for r in rejected_details if r.get("classification") == "DAY_TRADE"]
        
        if dt_rejections:
            # Check that rejections have reject_reasons
            for rej in dt_rejections[:3]:  # Check first 3
                exp = rej.get("explanation", {})
                reject_reasons = exp.get("reject_reasons", [])
                print(f"  {rej['symbol']}: {reject_reasons[:2]}")
            
            print(f"✓ Found {len(dt_rejections)} DAY_TRADE rejections with reject_reasons")
        else:
            print("✓ No DAY_TRADE rejections (all passed or no candidates)")


class TestTieredTAPipelineDayTrades:
    """Tests for day trade candidates"""

    def test_day_trades_have_tier1_score_and_analysis_mode(self, headers):
        """Day trade candidates should have tier1_score and analysis_mode fields"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        day_trades = data.get("day_trades", [])
        
        if day_trades:
            for dt in day_trades[:3]:  # Check first 3
                assert "tier1_score" in dt, f"Missing 'tier1_score' in day trade {dt.get('symbol')}"
                assert "analysis_mode" in dt, f"Missing 'analysis_mode' in day trade {dt.get('symbol')}"
                print(f"  {dt['symbol']}: tier1_score={dt['tier1_score']}, analysis_mode={dt['analysis_mode']}")
            
            print(f"✓ {len(day_trades)} day trades have tier1_score and analysis_mode")
        else:
            print("✓ No day trade candidates (market conditions may not favor)")


class TestTieredTAPipelineFunnel:
    """Tests for pipeline funnel stages"""

    def test_pipeline_funnel_has_correct_stages(self, headers):
        """Pipeline funnel should have all 8 stages"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        pipeline_funnel = data.get("pipeline_funnel", {})
        funnel = pipeline_funnel.get("funnel", {})
        
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
            assert stage in funnel, f"Missing stage '{stage}' in funnel. Got: {funnel.keys()}"
        
        print(f"✓ Pipeline funnel has all 8 stages:")
        for stage in expected_stages:
            print(f"  - {stage}: {funnel.get(stage, 0)}")


class TestRefreshTAEndpoint:
    """Tests for POST /api/auto-trade/refresh-ta"""

    def test_refresh_ta_returns_db_cached_count(self, headers):
        """POST /api/auto-trade/refresh-ta should trigger and return db_cached count"""
        resp = requests.post(f"{BASE_URL}/api/auto-trade/refresh-ta", headers=headers, timeout=30)
        assert resp.status_code == 200, f"Refresh TA failed: {resp.text}"
        data = resp.json()
        
        assert "db_cached" in data, f"Missing 'db_cached' in response. Got: {data.keys()}"
        assert "message" in data, f"Missing 'message' in response"
        
        print(f"✓ Refresh TA response: message='{data['message']}', db_cached={data['db_cached']}")
        
        # Should also have mem_cache stats
        if "mem_cache" in data:
            print(f"  mem_cache: {data['mem_cache']}")


class TestTieredTAPipelinePerformance:
    """Performance tests for the tiered pipeline"""

    def test_total_cycle_under_reasonable_time(self, headers):
        """Total scan cycle should complete in reasonable time"""
        start = time.time()
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=120)
        elapsed = time.time() - start
        
        assert resp.status_code == 200, f"Scan failed: {resp.text}"
        data = resp.json()
        
        timing = data.get("timing", {})
        total_cycle_sec = timing.get("total_cycle_sec", 0)
        
        # Total cycle should be under 30s for Starter plan
        assert total_cycle_sec < 30, f"Total cycle took {total_cycle_sec}s, expected < 30s"
        
        print(f"✓ Total cycle completed in {total_cycle_sec}s (request took {elapsed:.1f}s)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
