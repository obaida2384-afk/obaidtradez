"""
Test MTF Heatmap Feature
Tests the Multi-Timeframe Heatmap implementation:
- /api/auto-trade/scan returns mtf_heatmap array and mtf_heatmap_distribution object
- /api/auto-trade/mtf-heatmap dedicated endpoint
- MTFClassifier classification categories
- Heatmap entry fields validation
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    resp = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
    assert resp.status_code == 200, f"Auth failed: {resp.text}"
    data = resp.json()
    assert data.get("success") is True, f"Auth not successful: {data}"
    return data.get("token")


@pytest.fixture(scope="module")
def headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestMTFHeatmapBackend:
    """Backend API tests for MTF Heatmap feature"""

    def test_scan_returns_mtf_heatmap_array(self, headers):
        """Test /api/auto-trade/scan returns mtf_heatmap array"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200, f"Scan failed: {resp.text}"
        data = resp.json()
        
        # Check mtf_heatmap exists and is a list
        assert "mtf_heatmap" in data, "mtf_heatmap not in scan response"
        assert isinstance(data["mtf_heatmap"], list), "mtf_heatmap should be a list"
        print(f"SUCCESS: mtf_heatmap array found with {len(data['mtf_heatmap'])} entries")

    def test_scan_returns_mtf_heatmap_distribution(self, headers):
        """Test /api/auto-trade/scan returns mtf_heatmap_distribution object"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        # Check mtf_heatmap_distribution exists and is a dict
        assert "mtf_heatmap_distribution" in data, "mtf_heatmap_distribution not in scan response"
        dist = data["mtf_heatmap_distribution"]
        assert isinstance(dist, dict), "mtf_heatmap_distribution should be a dict"
        print(f"SUCCESS: mtf_heatmap_distribution found: {dist}")

    def test_distribution_has_all_six_categories(self, headers):
        """Test mtf_heatmap_distribution has all 6 categories"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        dist = data.get("mtf_heatmap_distribution", {})
        required_categories = [
            "BULLISH_ALIGNED", "BEARISH_ALIGNED", "MOMENTUM_CANDIDATE",
            "NEAR_MISS", "MIXED", "CONFLICT"
        ]
        
        for cat in required_categories:
            assert cat in dist, f"Category {cat} missing from distribution"
            assert isinstance(dist[cat], int), f"Category {cat} should be an integer count"
        
        print(f"SUCCESS: All 6 categories present in distribution: {dist}")

    def test_heatmap_entries_have_required_fields(self, headers):
        """Test mtf_heatmap entries have all required fields"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        heatmap = data.get("mtf_heatmap", [])
        if len(heatmap) == 0:
            pytest.skip("No heatmap entries to validate (market may be closed)")
        
        required_fields = [
            "symbol", "category", "direction", "trend_15m", "structure_5m",
            "timing_1m", "timing_status", "confidence", "rel_vol", "above_vwap",
            "setup_type", "reject_reasons"
        ]
        
        # Check first 5 entries
        for entry in heatmap[:5]:
            for field in required_fields:
                assert field in entry, f"Field {field} missing from heatmap entry {entry.get('symbol', 'unknown')}"
        
        print(f"SUCCESS: Heatmap entries have all required fields. Sample: {heatmap[0]['symbol']}")

    def test_category_classification_consistency(self, headers):
        """Test category classification is consistent with MTF data"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        heatmap = data.get("mtf_heatmap", [])
        if len(heatmap) == 0:
            pytest.skip("No heatmap entries to validate")
        
        conflict_entries = [e for e in heatmap if e["category"] == "CONFLICT"]
        aligned_entries = [e for e in heatmap if e["category"] in ("BULLISH_ALIGNED", "BEARISH_ALIGNED")]
        
        # CONFLICT entries should have has_tf_conflict=true
        for entry in conflict_entries[:3]:
            assert entry.get("has_tf_conflict") is True, \
                f"CONFLICT entry {entry['symbol']} should have has_tf_conflict=true"
        
        # Aligned entries should have mtf_aligned=true
        for entry in aligned_entries[:3]:
            assert entry.get("mtf_aligned") is True, \
                f"Aligned entry {entry['symbol']} should have mtf_aligned=true"
        
        print(f"SUCCESS: Category classification consistent. CONFLICT={len(conflict_entries)}, ALIGNED={len(aligned_entries)}")

    def test_direction_consistency(self, headers):
        """Test BULLISH_ALIGNED has direction=LONG, BEARISH_ALIGNED has direction=SHORT"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        heatmap = data.get("mtf_heatmap", [])
        if len(heatmap) == 0:
            pytest.skip("No heatmap entries to validate")
        
        bullish = [e for e in heatmap if e["category"] == "BULLISH_ALIGNED"]
        bearish = [e for e in heatmap if e["category"] == "BEARISH_ALIGNED"]
        
        # BULLISH_ALIGNED should have direction=LONG
        for entry in bullish[:3]:
            assert entry.get("direction") == "LONG", \
                f"BULLISH_ALIGNED {entry['symbol']} should have direction=LONG, got {entry.get('direction')}"
        
        # BEARISH_ALIGNED should have direction=SHORT
        for entry in bearish[:3]:
            assert entry.get("direction") == "SHORT", \
                f"BEARISH_ALIGNED {entry['symbol']} should have direction=SHORT, got {entry.get('direction')}"
        
        print(f"SUCCESS: Direction consistency verified. BULLISH_ALIGNED={len(bullish)}, BEARISH_ALIGNED={len(bearish)}")

    def test_dedicated_mtf_heatmap_endpoint(self, headers):
        """Test /api/auto-trade/mtf-heatmap dedicated endpoint returns 200"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/mtf-heatmap", headers=headers, timeout=60)
        assert resp.status_code == 200, f"MTF heatmap endpoint failed: {resp.text}"
        data = resp.json()
        
        # Should have heatmap and distribution
        assert "heatmap" in data, "heatmap not in dedicated endpoint response"
        assert "distribution" in data, "distribution not in dedicated endpoint response"
        assert isinstance(data["heatmap"], list), "heatmap should be a list"
        assert isinstance(data["distribution"], dict), "distribution should be a dict"
        
        print(f"SUCCESS: Dedicated MTF heatmap endpoint returns heatmap ({len(data['heatmap'])} entries) and distribution")

    def test_heatmap_sorted_by_confidence(self, headers):
        """Test heatmap entries are sorted by confidence descending"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        heatmap = data.get("mtf_heatmap", [])
        if len(heatmap) < 2:
            pytest.skip("Not enough heatmap entries to validate sorting")
        
        confidences = [e.get("confidence", 0) for e in heatmap]
        assert confidences == sorted(confidences, reverse=True), \
            "Heatmap should be sorted by confidence descending"
        
        print(f"SUCCESS: Heatmap sorted by confidence. Top: {confidences[0]}, Bottom: {confidences[-1]}")

    def test_timing_status_values(self, headers):
        """Test timing_status has valid values (entry_ready, early, weak)"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        heatmap = data.get("mtf_heatmap", [])
        if len(heatmap) == 0:
            pytest.skip("No heatmap entries to validate")
        
        valid_statuses = {"entry_ready", "early", "weak"}
        for entry in heatmap[:10]:
            status = entry.get("timing_status")
            assert status in valid_statuses, \
                f"Invalid timing_status '{status}' for {entry['symbol']}. Expected one of {valid_statuses}"
        
        print(f"SUCCESS: All timing_status values are valid")

    def test_timeframe_values(self, headers):
        """Test trend_15m, structure_5m, timing_1m have valid values"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers, timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        heatmap = data.get("mtf_heatmap", [])
        if len(heatmap) == 0:
            pytest.skip("No heatmap entries to validate")
        
        valid_structures = {"bullish", "bearish", "ranging", "unknown"}
        valid_timings = {"bullish", "bearish", "neutral", "mixed"}
        
        for entry in heatmap[:10]:
            assert entry.get("trend_15m") in valid_structures, \
                f"Invalid trend_15m '{entry.get('trend_15m')}' for {entry['symbol']}"
            assert entry.get("structure_5m") in valid_structures, \
                f"Invalid structure_5m '{entry.get('structure_5m')}' for {entry['symbol']}"
            assert entry.get("timing_1m") in valid_timings, \
                f"Invalid timing_1m '{entry.get('timing_1m')}' for {entry['symbol']}"
        
        print(f"SUCCESS: All timeframe values are valid")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
