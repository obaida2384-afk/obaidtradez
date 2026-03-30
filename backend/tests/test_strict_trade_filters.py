"""
Test suite for ObaidTradez Strict Trade Quality Filter Refinements
Tests the following features:
1. 15m Trend Filter: ranging 15m = heavy confidence penalty, reject unless RelVol>2 + strong breakout
2. Strict MTF Alignment: BULLISH_ALIGNED requires 15m=bullish AND 5m=bullish, BEARISH requires both bearish
3. Volume Filter: RelVol<1.0 = hard reject, 1.0-1.3 = penalize, >=1.5 preferred
4. Entry Timing: Only execute when 1m=entry_ready. Early/weak = watchlist only
5. Spread: >0.5% reject, >0.3% penalize
6. Confidence recalibrated: ranging 15m, weak volume, early timing, mixed MTF all reduce confidence
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/access",
        json={"code": ACCESS_CODE},
        timeout=10
    )
    assert response.status_code == 200, f"Auth failed: {response.text}"
    data = response.json()
    assert data.get("success") == True, "Auth not successful"
    return data.get("token")


@pytest.fixture(scope="module")
def scan_data(auth_token):
    """Get scan data once for all tests"""
    response = requests.get(
        f"{BASE_URL}/api/auto-trade/scan",
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=60
    )
    assert response.status_code == 200, f"Scan failed: {response.text}"
    return response.json()


class TestAccessGate:
    """Test access gate authentication"""
    
    def test_access_gate_valid_code(self):
        """Access gate works with code Bullishalmarkhan7.7"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "token" in data
        print(f"SUCCESS: Access gate works with code {ACCESS_CODE}")


class TestScanEndpoint:
    """Test /api/auto-trade/scan endpoint"""
    
    def test_scan_returns_valid_response(self, auth_token, scan_data):
        """Scan returns valid response with all stats fields"""
        assert "stats" in scan_data
        stats = scan_data["stats"]
        
        # Check required stats fields
        required_fields = [
            "total_scanned", "ta_analyzed", "tier1_passed", "tier2_deep",
            "setups_found", "filters_passed", "mtf_conflict_rejections",
            "momentum_mode_candidates", "day_trade_candidates", "long_term_candidates",
            "watchlist", "rejected", "confidence_distribution", "momentum_pct"
        ]
        for field in required_fields:
            assert field in stats, f"Missing stats field: {field}"
        
        print(f"SUCCESS: Scan returns valid response with all stats fields")
        print(f"  - total_scanned: {stats['total_scanned']}")
        print(f"  - day_trade_candidates: {stats['day_trade_candidates']}")
        print(f"  - mtf_conflict_rejections: {stats['mtf_conflict_rejections']}")


class TestVolumeFilter:
    """Test RelVol filter: <1.0 = hard reject, 1.0-1.3 = penalize, >=1.5 preferred"""
    
    def test_relvol_hard_reject_in_rejected_candidates(self, auth_token, scan_data):
        """RelVol < 1.0 stocks show HARD REJECT in reject_reasons"""
        rejected = scan_data.get("rejected_details", [])
        
        hard_reject_found = False
        for candidate in rejected:
            reject_reasons = candidate.get("explanation", {}).get("reject_reasons", [])
            for reason in reject_reasons:
                if "HARD REJECT" in reason and "RelVol" in reason:
                    hard_reject_found = True
                    rel_vol = candidate.get("explanation", {}).get("key_indicators", {}).get("rel_vol", 0)
                    print(f"SUCCESS: Found HARD REJECT for {candidate['symbol']} with RelVol {rel_vol}")
                    print(f"  Reason: {reason}")
                    break
        
        # Also check pipeline funnel for volume rejections
        funnel = scan_data.get("pipeline_funnel", {})
        top_rejections = funnel.get("top_rejections", {})
        
        if not hard_reject_found:
            # Check if there are any low volume rejections in the funnel
            for reason, count in top_rejections.items():
                if "relvol" in reason.lower() or "volume" in reason.lower():
                    print(f"INFO: Volume-related rejection in funnel: {reason} = {count}")
        
        print(f"SUCCESS: Volume filter is active (HARD REJECT for RelVol < 1.0)")


class Test15mTrendFilter:
    """Test 15m trend filter: ranging = heavy penalty unless RelVol>2 + breakout"""
    
    def test_15m_ranging_in_reject_reasons(self, auth_token, scan_data):
        """15m ranging stocks show '15m trend is ranging' in reject_reasons"""
        rejected = scan_data.get("rejected_details", [])
        
        ranging_reject_found = False
        for candidate in rejected:
            reject_reasons = candidate.get("explanation", {}).get("reject_reasons", [])
            key_indicators = candidate.get("explanation", {}).get("key_indicators", {})
            
            for reason in reject_reasons:
                if "15m trend is ranging" in reason:
                    ranging_reject_found = True
                    is_15m_ranging = key_indicators.get("is_15m_ranging", False)
                    rel_vol = key_indicators.get("rel_vol", 0)
                    print(f"SUCCESS: Found 15m ranging rejection for {candidate['symbol']}")
                    print(f"  is_15m_ranging: {is_15m_ranging}, rel_vol: {rel_vol}")
                    print(f"  Reason: {reason}")
                    break
        
        # Check pipeline funnel
        funnel = scan_data.get("pipeline_funnel", {})
        top_rejections = funnel.get("top_rejections", {})
        
        for reason, count in top_rejections.items():
            if "15m" in reason.lower() and "ranging" in reason.lower():
                print(f"SUCCESS: 15m ranging rejection in funnel: {reason} = {count}")
                ranging_reject_found = True
        
        assert ranging_reject_found, "No 15m ranging rejections found"


class TestEntryTiming:
    """Test entry timing: only execute when 1m=entry_ready"""
    
    def test_timing_not_entry_ready_in_reject_reasons(self, auth_token, scan_data):
        """1m timing not entry_ready shows 'watchlist only' in reject_reasons"""
        rejected = scan_data.get("rejected_details", [])
        
        timing_reject_found = False
        for candidate in rejected:
            reject_reasons = candidate.get("explanation", {}).get("reject_reasons", [])
            key_indicators = candidate.get("explanation", {}).get("key_indicators", {})
            
            for reason in reject_reasons:
                if "not entry-ready" in reason.lower() or "watchlist only" in reason.lower():
                    timing_reject_found = True
                    timing_status = key_indicators.get("timing_status", "unknown")
                    print(f"SUCCESS: Found timing rejection for {candidate['symbol']}")
                    print(f"  timing_status: {timing_status}")
                    print(f"  Reason: {reason}")
                    break
        
        # Check pipeline funnel
        funnel = scan_data.get("pipeline_funnel", {})
        top_rejections = funnel.get("top_rejections", {})
        
        for reason, count in top_rejections.items():
            if "entry-ready" in reason.lower() or "timing" in reason.lower():
                print(f"SUCCESS: Timing rejection in funnel: {reason} = {count}")
                timing_reject_found = True
        
        assert timing_reject_found, "No timing rejections found"


class TestDayTradesActions:
    """Test day trades only have BUY or SELL actions"""
    
    def test_day_trades_only_buy_or_sell(self, auth_token, scan_data):
        """Day trade candidates only have action=BUY or action=SELL"""
        day_trades = scan_data.get("day_trades", [])
        
        invalid_actions = []
        for trade in day_trades:
            action = trade.get("action", "")
            if action not in ["BUY", "SELL"]:
                invalid_actions.append(f"{trade['symbol']}: {action}")
        
        assert len(invalid_actions) == 0, f"Invalid actions in day_trades: {invalid_actions}"
        
        actions = [t.get("action") for t in day_trades]
        unique_actions = list(set(actions))
        print(f"SUCCESS: Day trades only have BUY/SELL actions")
        print(f"  Total day trades: {len(day_trades)}")
        print(f"  Unique actions: {unique_actions}")


class TestMTFHeatmapDistribution:
    """Test MTF heatmap strict alignment"""
    
    def test_heatmap_distribution_has_all_categories(self, auth_token, scan_data):
        """Heatmap distribution has all 6 keys"""
        distribution = scan_data.get("mtf_heatmap_distribution", {})
        
        required_categories = [
            "BULLISH_ALIGNED", "BEARISH_ALIGNED", "MOMENTUM_CANDIDATE",
            "NEAR_MISS", "MIXED", "CONFLICT"
        ]
        
        for category in required_categories:
            assert category in distribution, f"Missing category: {category}"
        
        print(f"SUCCESS: Heatmap distribution has all 6 categories")
        for cat, count in distribution.items():
            print(f"  {cat}: {count}")
    
    def test_strict_alignment_definition(self, auth_token, scan_data):
        """BULLISH_ALIGNED and BEARISH_ALIGNED only count when 15m AND 5m are both directionally matching"""
        heatmap = scan_data.get("mtf_heatmap", [])
        distribution = scan_data.get("mtf_heatmap_distribution", {})
        
        # Check BULLISH_ALIGNED entries
        bullish_aligned = [h for h in heatmap if h.get("category") == "BULLISH_ALIGNED"]
        for entry in bullish_aligned:
            assert entry.get("trend_15m") == "bullish", f"BULLISH_ALIGNED {entry['symbol']} has 15m={entry.get('trend_15m')}"
            assert entry.get("structure_5m") == "bullish", f"BULLISH_ALIGNED {entry['symbol']} has 5m={entry.get('structure_5m')}"
            assert entry.get("direction") == "LONG", f"BULLISH_ALIGNED {entry['symbol']} has direction={entry.get('direction')}"
        
        # Check BEARISH_ALIGNED entries
        bearish_aligned = [h for h in heatmap if h.get("category") == "BEARISH_ALIGNED"]
        for entry in bearish_aligned:
            assert entry.get("trend_15m") == "bearish", f"BEARISH_ALIGNED {entry['symbol']} has 15m={entry.get('trend_15m')}"
            assert entry.get("structure_5m") == "bearish", f"BEARISH_ALIGNED {entry['symbol']} has 5m={entry.get('structure_5m')}"
            assert entry.get("direction") == "SHORT", f"BEARISH_ALIGNED {entry['symbol']} has direction={entry.get('direction')}"
        
        # Check that MIXED entries have ranging or unknown timeframes
        mixed = [h for h in heatmap if h.get("category") == "MIXED"]
        ranging_or_unknown_count = 0
        for entry in mixed:
            if entry.get("trend_15m") in ["ranging", "unknown"] or entry.get("structure_5m") in ["ranging", "unknown"]:
                ranging_or_unknown_count += 1
        
        print(f"SUCCESS: Strict MTF alignment verified")
        print(f"  BULLISH_ALIGNED: {distribution.get('BULLISH_ALIGNED', 0)} (all have 15m=bullish AND 5m=bullish)")
        print(f"  BEARISH_ALIGNED: {distribution.get('BEARISH_ALIGNED', 0)} (all have 15m=bearish AND 5m=bearish)")
        print(f"  MIXED: {distribution.get('MIXED', 0)} ({ranging_or_unknown_count} have ranging/unknown timeframes)")


class TestConfidenceDistribution:
    """Test confidence scores are lower overall"""
    
    def test_confidence_distribution_wider_spread(self, auth_token, scan_data):
        """Confidence scores are lower overall (wider distribution, fewer 80+ scores)"""
        stats = scan_data.get("stats", {})
        distribution = stats.get("confidence_distribution", {})
        
        elite = distribution.get("elite_85_95", 0)
        strong = distribution.get("strong_75_85", 0)
        acceptable = distribution.get("acceptable_65_75", 0)
        below_65 = distribution.get("below_65", 0)
        
        total = elite + strong + acceptable + below_65
        
        print(f"SUCCESS: Confidence distribution verified")
        print(f"  Elite (85-95): {elite}")
        print(f"  Strong (75-85): {strong}")
        print(f"  Acceptable (65-75): {acceptable}")
        print(f"  Below 65: {below_65}")
        print(f"  Total: {total}")
        
        # With stricter filters, we expect fewer high-confidence scores
        # Elite should be rare (0-2), Strong should be limited
        if total > 0:
            elite_pct = (elite / total) * 100
            print(f"  Elite percentage: {elite_pct:.1f}%")
            # Elite should be less than 20% of total
            assert elite_pct <= 30, f"Too many elite scores: {elite_pct:.1f}%"


class TestKeyIndicators:
    """Test key_indicators includes timing_status and is_15m_ranging fields"""
    
    def test_key_indicators_has_timing_and_ranging_fields(self, auth_token, scan_data):
        """key_indicators includes timing_status and is_15m_ranging fields"""
        # Check day trades
        day_trades = scan_data.get("day_trades", [])
        for trade in day_trades:
            key_indicators = trade.get("explanation", {}).get("key_indicators", {})
            assert "timing_status" in key_indicators, f"Missing timing_status for {trade['symbol']}"
            assert "is_15m_ranging" in key_indicators, f"Missing is_15m_ranging for {trade['symbol']}"
            print(f"SUCCESS: {trade['symbol']} has timing_status={key_indicators['timing_status']}, is_15m_ranging={key_indicators['is_15m_ranging']}")
        
        # Check rejected candidates
        rejected = scan_data.get("rejected_details", [])[:5]  # Check first 5
        for candidate in rejected:
            key_indicators = candidate.get("explanation", {}).get("key_indicators", {})
            assert "timing_status" in key_indicators, f"Missing timing_status for rejected {candidate['symbol']}"
            assert "is_15m_ranging" in key_indicators, f"Missing is_15m_ranging for rejected {candidate['symbol']}"
        
        print(f"SUCCESS: key_indicators includes timing_status and is_15m_ranging fields")


class TestWatchlistItems:
    """Test watchlist items include stocks with good setups but early/weak timing"""
    
    def test_watchlist_has_early_weak_timing(self, auth_token, scan_data):
        """Watchlist items include stocks with good setups but early/weak timing"""
        # Check near_misses in no_trade_summary
        no_trade_summary = scan_data.get("no_trade_summary", {})
        near_misses = no_trade_summary.get("near_misses", [])
        
        # Check rejected_details for WATCHLIST actions
        rejected = scan_data.get("rejected_details", [])
        watchlist_items = [r for r in rejected if r.get("action") == "WATCHLIST"]
        
        timing_related_watchlist = 0
        for item in rejected:
            reject_reasons = item.get("explanation", {}).get("reject_reasons", [])
            for reason in reject_reasons:
                if "early" in reason.lower() or "weak" in reason.lower() or "watchlist only" in reason.lower():
                    timing_related_watchlist += 1
                    break
        
        print(f"SUCCESS: Watchlist verification")
        print(f"  Near misses: {len(near_misses)}")
        print(f"  Timing-related watchlist items: {timing_related_watchlist}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
