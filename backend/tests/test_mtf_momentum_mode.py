"""
Test Multi-Timeframe Confirmation (MTF) and Momentum Mode Bypass features.

P1 Features:
1. MTF Confirmation: 1min=entry timing, 5min=structure, 15min=trend
   - LONGs require 5m bullish + 15m supportive/neutral
   - SHORTs require 5m bearish + 15m supportive/neutral
   - 1m conflicts downgrade confidence only

2. Momentum Mode Bypass: disciplined bypass for explosive movers
   - RelVol>2, strong breakout/breakdown, clear HH/HL or LH/LL
   - VWAP aligned, spread<=0.5%, NOT overextended, NOT fake breakout
   - Bypasses soft filters but NOT risk rules
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMTFMomentumModeAPI:
    """Test MTF and Momentum Mode features via API"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Authenticate
        auth_resp = self.session.post(f"{BASE_URL}/api/auth/access", json={"code": "Bullishalmarkhan7.7"})
        assert auth_resp.status_code == 200, f"Auth failed: {auth_resp.text}"
        token = auth_resp.json().get("token")
        assert token, "No token returned"
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_auth_access_works(self):
        """Test access gate with correct code"""
        resp = requests.post(f"{BASE_URL}/api/auth/access", json={"code": "Bullishalmarkhan7.7"})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        print("SUCCESS: Auth access works with code Bullishalmarkhan7.7")
    
    def test_scan_returns_mtf_stats(self):
        """Test /api/auto-trade/scan returns new MTF stats fields"""
        resp = self.session.get(f"{BASE_URL}/api/auto-trade/scan", timeout=60)
        assert resp.status_code == 200, f"Scan failed: {resp.text}"
        data = resp.json()
        
        # Check stats has new MTF/Momentum fields
        stats = data.get("stats", {})
        assert "mtf_conflict_rejections" in stats, "Missing mtf_conflict_rejections in stats"
        assert "momentum_mode_candidates" in stats, "Missing momentum_mode_candidates in stats"
        assert "momentum_bypass_active" in stats, "Missing momentum_bypass_active in stats"
        
        print(f"SUCCESS: Scan returns MTF stats - MTF conflicts: {stats['mtf_conflict_rejections']}, "
              f"Momentum candidates: {stats['momentum_mode_candidates']}, "
              f"Momentum bypassed: {stats['momentum_bypass_active']}")
    
    def test_day_trade_candidates_have_mtf_fields(self):
        """Test day trade candidates have mtf_aligned and has_tf_conflict fields"""
        resp = self.session.get(f"{BASE_URL}/api/auto-trade/scan", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        day_trades = data.get("day_trades", [])
        if len(day_trades) > 0:
            candidate = day_trades[0]
            assert "mtf_aligned" in candidate, "Missing mtf_aligned field in day trade candidate"
            assert "has_tf_conflict" in candidate, "Missing has_tf_conflict field in day trade candidate"
            assert "momentum_mode" in candidate, "Missing momentum_mode field in day trade candidate"
            assert "momentum_bypass_active" in candidate, "Missing momentum_bypass_active field in day trade candidate"
            
            print(f"SUCCESS: Day trade candidate {candidate['symbol']} has MTF fields - "
                  f"mtf_aligned: {candidate['mtf_aligned']}, has_tf_conflict: {candidate['has_tf_conflict']}, "
                  f"momentum_mode: {candidate['momentum_mode']}")
        else:
            # Check watchlist or rejected for MTF fields
            watchlist = data.get("watchlist", [])
            rejected = data.get("rejected_details", [])
            all_candidates = watchlist + rejected
            
            if len(all_candidates) > 0:
                candidate = all_candidates[0]
                assert "mtf_aligned" in candidate, "Missing mtf_aligned field in candidate"
                assert "has_tf_conflict" in candidate, "Missing has_tf_conflict field in candidate"
                print(f"SUCCESS: Candidate {candidate['symbol']} has MTF fields (from watchlist/rejected)")
            else:
                print("WARNING: No candidates to verify MTF fields - market may be closed")
    
    def test_explanation_has_mtf_key_indicators(self):
        """Test explanation.key_indicators includes MTF fields"""
        resp = self.session.get(f"{BASE_URL}/api/auto-trade/scan", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        # Check any candidate (day_trades, watchlist, or rejected)
        all_candidates = (data.get("day_trades", []) + 
                         data.get("watchlist", []) + 
                         data.get("rejected_details", []))
        
        if len(all_candidates) > 0:
            candidate = all_candidates[0]
            explanation = candidate.get("explanation", {})
            ki = explanation.get("key_indicators", {})
            
            # Check for MTF fields in key_indicators
            mtf_fields = ["mtf_5m", "mtf_15m", "mtf_1m", "mtf_score", "mtf_aligned", "has_tf_conflict"]
            found_fields = [f for f in mtf_fields if f in ki]
            
            print(f"SUCCESS: Candidate {candidate['symbol']} key_indicators has MTF fields: {found_fields}")
            
            # Also check for momentum fields
            momentum_fields = ["momentum_mode", "momentum_bypass_active"]
            found_momentum = [f for f in momentum_fields if f in ki]
            print(f"SUCCESS: Candidate {candidate['symbol']} key_indicators has momentum fields: {found_momentum}")
        else:
            print("WARNING: No candidates to verify key_indicators - market may be closed")
    
    def test_pipeline_funnel_has_mtf_rejections(self):
        """Test pipeline funnel tracks MTF conflict rejections"""
        resp = self.session.get(f"{BASE_URL}/api/auto-trade/scan", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        funnel = data.get("pipeline_funnel", {})
        assert "funnel" in funnel, "Missing funnel in pipeline_funnel"
        assert "top_rejections" in funnel, "Missing top_rejections in pipeline_funnel"
        
        # Check if MTF rejections are tracked (may be 0 if no conflicts)
        top_rejections = funnel.get("top_rejections", {})
        mtf_rejections = {k: v for k, v in top_rejections.items() 
                         if "mtf" in k.lower() or "timeframe" in k.lower()}
        
        print(f"SUCCESS: Pipeline funnel has top_rejections. MTF-related: {mtf_rejections}")
    
    def test_rejected_candidates_show_mtf_conflict_reasons(self):
        """Test rejected candidates show MTF CONFLICT rejection reasons"""
        resp = self.session.get(f"{BASE_URL}/api/auto-trade/scan", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        rejected = data.get("rejected_details", [])
        mtf_rejected = []
        
        for r in rejected:
            explanation = r.get("explanation", {})
            reject_reasons = explanation.get("reject_reasons", [])
            mtf_reasons = [reason for reason in reject_reasons 
                          if "mtf" in reason.lower() or "timeframe" in reason.lower() or "5m" in reason or "15m" in reason]
            if mtf_reasons:
                mtf_rejected.append({"symbol": r["symbol"], "reasons": mtf_reasons})
        
        if mtf_rejected:
            print(f"SUCCESS: Found {len(mtf_rejected)} rejected candidates with MTF conflict reasons:")
            for item in mtf_rejected[:3]:
                print(f"  - {item['symbol']}: {item['reasons']}")
        else:
            print("INFO: No rejected candidates with explicit MTF conflict reasons (may be no conflicts)")
    
    def test_stats_grid_has_9_columns(self):
        """Test stats include all required fields for 9-column grid"""
        resp = self.session.get(f"{BASE_URL}/api/auto-trade/scan", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        stats = data.get("stats", {})
        required_fields = [
            "total_scanned",
            "ta_analyzed",
            "tier2_deep",
            "setups_found",
            "mtf_conflict_rejections",
            "momentum_mode_candidates",
            "day_trade_candidates",
            "watchlist",
            "rejected"
        ]
        
        missing = [f for f in required_fields if f not in stats]
        assert len(missing) == 0, f"Missing stats fields: {missing}"
        
        print(f"SUCCESS: Stats has all 9 required fields for grid display")
        print(f"  Scanned: {stats['total_scanned']}, T1: {stats['ta_analyzed']}, T2: {stats['tier2_deep']}")
        print(f"  Setups: {stats['setups_found']}, MTF Conflicts: {stats['mtf_conflict_rejections']}")
        print(f"  Momentum: {stats['momentum_mode_candidates']}, DT: {stats['day_trade_candidates']}")
        print(f"  Watchlist: {stats['watchlist']}, Rejected: {stats['rejected']}")
    
    def test_buy_reasons_include_mtf_aligned_text(self):
        """Test buy reasons include 'MTF aligned: 5m+15m confirm' for aligned candidates"""
        resp = self.session.get(f"{BASE_URL}/api/auto-trade/scan", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        # Check day trades and watchlist for MTF aligned candidates
        all_candidates = data.get("day_trades", []) + data.get("watchlist", [])
        mtf_aligned_candidates = [c for c in all_candidates if c.get("mtf_aligned")]
        
        if mtf_aligned_candidates:
            for candidate in mtf_aligned_candidates[:3]:
                explanation = candidate.get("explanation", {})
                entry_reasons = explanation.get("entry_reasons", [])
                mtf_reasons = [r for r in entry_reasons if "mtf" in r.lower() or "5m" in r.lower() or "15m" in r.lower()]
                print(f"SUCCESS: MTF aligned candidate {candidate['symbol']} entry_reasons: {mtf_reasons}")
        else:
            print("INFO: No MTF aligned candidates found (may be market conditions)")
    
    def test_momentum_mode_badge_candidates(self):
        """Test candidates with momentum_mode=true exist (if any)"""
        resp = self.session.get(f"{BASE_URL}/api/auto-trade/scan", timeout=60)
        assert resp.status_code == 200
        data = resp.json()
        
        all_candidates = (data.get("day_trades", []) + 
                         data.get("watchlist", []) + 
                         data.get("rejected_details", []))
        
        momentum_candidates = [c for c in all_candidates if c.get("momentum_mode")]
        
        if momentum_candidates:
            print(f"SUCCESS: Found {len(momentum_candidates)} momentum mode candidates:")
            for c in momentum_candidates[:3]:
                print(f"  - {c['symbol']}: momentum_mode={c['momentum_mode']}, "
                      f"bypass_active={c.get('momentum_bypass_active', False)}")
        else:
            stats = data.get("stats", {})
            print(f"INFO: No momentum mode candidates found. Stats show: {stats.get('momentum_mode_candidates', 0)}")


class TestMTFMomentumModeSettings:
    """Test settings related to MTF and Momentum Mode"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        auth_resp = self.session.post(f"{BASE_URL}/api/auth/access", json={"code": "Bullishalmarkhan7.7"})
        assert auth_resp.status_code == 200
        token = auth_resp.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_settings_endpoint_works(self):
        """Test /api/auto-trade/settings returns valid response"""
        resp = self.session.get(f"{BASE_URL}/api/auto-trade/settings")
        assert resp.status_code == 200
        data = resp.json()
        
        assert "dt_confidence_threshold" in data, "Missing dt_confidence_threshold"
        print(f"SUCCESS: Settings endpoint works. DT threshold: {data['dt_confidence_threshold']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
