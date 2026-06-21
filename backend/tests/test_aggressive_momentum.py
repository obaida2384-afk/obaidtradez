"""
Test Aggressive Momentum Strategy - Backend API Tests
Tests the new momentum prefilter, dynamic confidence thresholds, 
confidence-tiered position sizing, and strategy response structure.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"


class TestAggressiveMomentumStrategy:
    """Tests for the Aggressive Momentum Day Trading Strategy"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200, f"Auth failed: {response.text}"
        data = response.json()
        assert data.get("success") == True, f"Auth not successful: {data}"
        self.token = data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_auth_access(self):
        """Test authentication with access code"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "token" in data
        print(f"✓ Auth successful, token received")
    
    def test_scan_endpoint_returns_strategy_object(self):
        """Test /api/auto-trade/scan returns strategy object with aggressive momentum params"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=self.headers)
        assert response.status_code == 200, f"Scan failed: {response.text}"
        data = response.json()
        
        # Verify strategy object exists
        assert "strategy" in data, "Missing 'strategy' in response"
        strategy = data["strategy"]
        
        # Verify strategy name
        assert strategy.get("name") == "Aggressive Momentum", f"Expected 'Aggressive Momentum', got {strategy.get('name')}"
        print(f"✓ Strategy name: {strategy.get('name')}")
        
        # Verify price range contains $5 and $50
        price_range = strategy.get("price_range", "")
        assert "$5" in price_range, f"Price range should contain $5: {price_range}"
        assert "$50" in price_range, f"Price range should contain $50: {price_range}"
        print(f"✓ Price range: {price_range}")
        
        # Verify min_rel_vol is 1.5x
        min_rel_vol = strategy.get("min_rel_vol", "")
        assert "1.5" in min_rel_vol, f"Min RelVol should be 1.5x: {min_rel_vol}"
        print(f"✓ Min RelVol: {min_rel_vol}")
        
        # Verify min_atr_pct is 2.0%
        min_atr = strategy.get("min_atr_pct", "")
        assert "2" in min_atr, f"Min ATR should be 2%: {min_atr}"
        print(f"✓ Min ATR: {min_atr}")
        
        # Verify stop_loss is 1.5%
        stop_loss = strategy.get("stop_loss", "")
        assert "1.5" in stop_loss, f"Stop loss should be 1.5%: {stop_loss}"
        print(f"✓ Stop Loss: {stop_loss}")
        
        # Verify take_profit is 3.0%
        take_profit = strategy.get("take_profit", "")
        assert "3" in take_profit, f"Take profit should be 3%: {take_profit}"
        print(f"✓ Take Profit: {take_profit}")
        
        # Verify partial_profit contains 1.5%
        partial_profit = strategy.get("partial_profit", "")
        assert "1.5" in partial_profit, f"Partial profit should contain 1.5%: {partial_profit}"
        print(f"✓ Partial Profit: {partial_profit}")
        
        # Verify position_sizing tiers
        position_sizing = strategy.get("position_sizing", "")
        assert "60-70" in position_sizing or "10%" in position_sizing, f"Position sizing should have tiers: {position_sizing}"
        print(f"✓ Position Sizing: {position_sizing}")
        
        # Verify max_trades_per_day is 8
        max_trades = strategy.get("max_trades_per_day")
        assert max_trades == 8, f"Max trades should be 8: {max_trades}"
        print(f"✓ Max Trades/Day: {max_trades}")
        
        # Verify daily_loss_hard_stop is 3 losses
        hard_stop = strategy.get("daily_loss_hard_stop", "")
        assert "3" in hard_stop, f"Hard stop should be 3 losses: {hard_stop}"
        print(f"✓ Daily Loss Hard Stop: {hard_stop}")
        
        # Verify cooldown is 30min
        cooldown = strategy.get("cooldown", "")
        assert "30" in cooldown, f"Cooldown should be 30min: {cooldown}"
        print(f"✓ Cooldown: {cooldown}")
        
        # Verify max_daily_loss is 3%
        max_daily_loss = strategy.get("max_daily_loss", "")
        assert "3" in max_daily_loss, f"Max daily loss should be 3%: {max_daily_loss}"
        print(f"✓ Max Daily Loss: {max_daily_loss}")
    
    def test_scan_returns_prefilter_stats(self):
        """Test scan returns proper prefilter stats"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify stats object exists
        assert "stats" in data, "Missing 'stats' in response"
        stats = data["stats"]
        
        # Verify prefilter stats exist
        assert "total_scanned" in stats, "Missing total_scanned in stats"
        assert "prefilter_passed" in stats, "Missing prefilter_passed in stats"
        assert "ta_analyzed" in stats, "Missing ta_analyzed in stats"
        assert "setups_found" in stats, "Missing setups_found in stats"
        
        print(f"✓ Total Scanned: {stats.get('total_scanned')}")
        print(f"✓ Prefilter Passed: {stats.get('prefilter_passed')}")
        print(f"✓ TA Analyzed: {stats.get('ta_analyzed')}")
        print(f"✓ Setups Found: {stats.get('setups_found')}")
        print(f"✓ Day Trade Candidates: {stats.get('day_trade_candidates')}")
        print(f"✓ Long Term Candidates: {stats.get('long_term_candidates')}")
    
    def test_confidence_distribution_tiers(self):
        """Test confidence distribution uses new tiers"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        stats = data.get("stats", {})
        conf_dist = stats.get("confidence_distribution", {})
        
        # Verify new tier keys exist
        assert "elite_80_plus" in conf_dist, f"Missing elite_80_plus tier: {conf_dist}"
        assert "strong_70_80" in conf_dist, f"Missing strong_70_80 tier: {conf_dist}"
        assert "acceptable_60_70" in conf_dist, f"Missing acceptable_60_70 tier: {conf_dist}"
        assert "below_60" in conf_dist, f"Missing below_60 tier: {conf_dist}"
        
        print(f"✓ Confidence Distribution:")
        print(f"  - Elite (80+): {conf_dist.get('elite_80_plus')}")
        print(f"  - Strong (70-80): {conf_dist.get('strong_70_80')}")
        print(f"  - Acceptable (60-70): {conf_dist.get('acceptable_60_70')}")
        print(f"  - Below 60: {conf_dist.get('below_60')}")
    
    def test_dynamic_thresholds_in_response(self):
        """Test dynamic thresholds are returned"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify dynamic_thresholds exists
        assert "dynamic_thresholds" in data, "Missing dynamic_thresholds in response"
        thresholds = data["dynamic_thresholds"]
        
        assert "dt_threshold" in thresholds, "Missing dt_threshold"
        assert "lt_threshold" in thresholds, "Missing lt_threshold"
        assert "risk_mode" in thresholds, "Missing risk_mode"
        
        print(f"✓ DT Threshold: {thresholds.get('dt_threshold')}")
        print(f"✓ LT Threshold: {thresholds.get('lt_threshold')}")
        print(f"✓ Risk Mode: {thresholds.get('risk_mode')}")
    
    def test_pipeline_funnel_in_response(self):
        """Test pipeline funnel is returned"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify pipeline_funnel exists
        assert "pipeline_funnel" in data, "Missing pipeline_funnel in response"
        funnel = data["pipeline_funnel"]
        
        assert "funnel" in funnel, "Missing funnel stages"
        stages = funnel["funnel"]
        
        # Verify key stages exist
        assert "universe_scanned" in stages, "Missing universe_scanned stage"
        assert "prefilter_passed" in stages, "Missing prefilter_passed stage"
        assert "ta_analyzed" in stages, "Missing ta_analyzed stage"
        assert "setup_found" in stages, "Missing setup_found stage"
        
        print(f"✓ Pipeline Funnel Stages:")
        for stage, count in stages.items():
            print(f"  - {stage}: {count}")
    
    def test_market_session_in_response(self):
        """Test market session is returned"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "market_session" in data, "Missing market_session in response"
        session = data["market_session"]
        valid_sessions = ["pre_market", "regular", "closing", "after_hours", "closed"]
        assert session in valid_sessions, f"Invalid session: {session}"
        print(f"✓ Market Session: {session}")
    
    def test_risk_mode_in_response(self):
        """Test risk mode is returned"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "risk_mode" in data, "Missing risk_mode in response"
        risk_mode = data["risk_mode"]
        valid_modes = ["NORMAL", "CAUTIOUS", "DEFENSIVE", "AGGRESSIVE", "VOLATILE"]
        assert risk_mode in valid_modes, f"Invalid risk mode: {risk_mode}"
        print(f"✓ Risk Mode: {risk_mode}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
