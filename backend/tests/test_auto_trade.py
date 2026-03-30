"""
Auto-Trade AI System Tests
Tests for the dual-engine autonomous trading system with Day Trading + Long-Term Investment modes.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAutoTradeSystem:
    """Auto-Trade AI System endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": "Bullishalmarkhan7.7"}
        )
        assert response.status_code == 200, f"Auth failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        self.token = data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    # ============ STATUS ENDPOINT ============
    
    def test_auto_trade_status_returns_200(self):
        """Test /api/auto-trade/status returns 200 with correct structure"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/status", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        # Verify required fields
        assert "auto_enabled" in data
        assert "market_regime" in data
        assert "account" in data
        assert "positions" in data
        assert "settings" in data
        
        # Verify market regime structure
        regime = data["market_regime"]
        assert "regime" in regime
        assert "volatility" in regime
        assert "volatility_pct" in regime
        assert "trend" in regime
        assert "score" in regime
        
        # Verify account structure
        account = data["account"]
        assert "equity" in account
        assert "buying_power" in account
        
        # Verify settings structure
        settings = data["settings"]
        assert "dt_enabled" in settings
        assert "lt_enabled" in settings
        assert "dt_confidence_threshold" in settings
        assert "lt_confidence_threshold" in settings
        assert "max_daily_loss_pct" in settings
        
        print(f"✓ Status endpoint returns correct structure with regime: {regime['regime']}")
    
    def test_auto_trade_status_requires_auth(self):
        """Test /api/auto-trade/status requires authentication"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/status")
        assert response.status_code == 401
        print("✓ Status endpoint requires authentication")
    
    # ============ TOGGLE ENDPOINT ============
    
    def test_auto_trade_toggle_on(self):
        """Test toggling auto-trade ON"""
        response = requests.post(
            f"{BASE_URL}/api/auto-trade/toggle?enabled=true",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["auto_enabled"] == True
        assert "ENABLED" in data["message"]
        print("✓ Toggle ON works correctly")
    
    def test_auto_trade_toggle_off(self):
        """Test toggling auto-trade OFF"""
        response = requests.post(
            f"{BASE_URL}/api/auto-trade/toggle?enabled=false",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["auto_enabled"] == False
        assert "DISABLED" in data["message"]
        print("✓ Toggle OFF works correctly")
    
    def test_toggle_persists_state(self):
        """Test that toggle state persists"""
        # Toggle ON
        requests.post(f"{BASE_URL}/api/auto-trade/toggle?enabled=true", headers=self.headers)
        
        # Verify state
        status = requests.get(f"{BASE_URL}/api/auto-trade/status", headers=self.headers).json()
        assert status["auto_enabled"] == True
        
        # Toggle OFF
        requests.post(f"{BASE_URL}/api/auto-trade/toggle?enabled=false", headers=self.headers)
        
        # Verify state
        status = requests.get(f"{BASE_URL}/api/auto-trade/status", headers=self.headers).json()
        assert status["auto_enabled"] == False
        print("✓ Toggle state persists correctly")
    
    # ============ SCAN ENDPOINT ============
    
    def test_auto_trade_scan_returns_200(self):
        """Test /api/auto-trade/scan returns 200 with classification data"""
        response = requests.get(
            f"{BASE_URL}/api/auto-trade/scan",
            headers=self.headers,
            timeout=60  # Scan can take time
        )
        assert response.status_code == 200
        
        data = response.json()
        # Verify required fields
        assert "market_regime" in data
        assert "day_trades" in data
        assert "long_term" in data
        assert "watchlist" in data
        assert "stats" in data
        
        # Verify stats structure
        stats = data["stats"]
        assert "total_scanned" in stats
        assert "day_trade_candidates" in stats
        assert "long_term_candidates" in stats
        assert "watchlist" in stats
        assert "rejected" in stats
        
        print(f"✓ Scan returns {stats['total_scanned']} stocks scanned, {stats['long_term_candidates']} long-term candidates")
    
    def test_scan_long_term_candidates_have_explanation(self):
        """Test that long-term candidates have explanation data"""
        response = requests.get(
            f"{BASE_URL}/api/auto-trade/scan",
            headers=self.headers,
            timeout=60
        )
        assert response.status_code == 200
        
        data = response.json()
        long_term = data.get("long_term", [])
        
        if len(long_term) > 0:
            candidate = long_term[0]
            assert "symbol" in candidate
            assert "classification" in candidate
            assert "confidence" in candidate
            assert "action" in candidate
            assert "explanation" in candidate
            
            exp = candidate["explanation"]
            assert "entry_reasons" in exp
            assert "key_indicators" in exp
            print(f"✓ Long-term candidate {candidate['symbol']} has explanation with {len(exp['entry_reasons'])} entry reasons")
        else:
            print("⚠ No long-term candidates found (market conditions may not favor)")
    
    # ============ SETTINGS ENDPOINT ============
    
    def test_get_settings(self):
        """Test GET /api/auto-trade/settings"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/settings", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        # Day trading settings
        assert "dt_enabled" in data
        assert "dt_confidence_threshold" in data
        assert "dt_risk_per_trade_pct" in data
        assert "dt_max_positions" in data
        assert "dt_take_profit_pct" in data
        assert "dt_stop_loss_pct" in data
        
        # Long-term settings
        assert "lt_enabled" in data
        assert "lt_confidence_threshold" in data
        assert "lt_max_position_pct" in data
        assert "lt_max_positions" in data
        assert "lt_trailing_stop_pct" in data
        
        # Risk management
        assert "max_daily_loss_pct" in data
        assert "max_portfolio_drawdown_pct" in data
        assert "max_sector_concentration_pct" in data
        
        print("✓ Settings endpoint returns all required fields")
    
    def test_update_settings(self):
        """Test POST /api/auto-trade/settings updates values"""
        # Get current settings
        current = requests.get(f"{BASE_URL}/api/auto-trade/settings", headers=self.headers).json()
        original_threshold = current.get("dt_confidence_threshold", 60)
        
        # Update setting
        new_threshold = 75 if original_threshold != 75 else 70
        response = requests.post(
            f"{BASE_URL}/api/auto-trade/settings",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"dt_confidence_threshold": new_threshold}
        )
        assert response.status_code == 200
        
        # Verify update
        updated = requests.get(f"{BASE_URL}/api/auto-trade/settings", headers=self.headers).json()
        assert updated["dt_confidence_threshold"] == new_threshold
        
        # Restore original
        requests.post(
            f"{BASE_URL}/api/auto-trade/settings",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"dt_confidence_threshold": original_threshold}
        )
        
        print(f"✓ Settings update works (changed threshold to {new_threshold}, restored to {original_threshold})")
    
    def test_update_multiple_settings(self):
        """Test updating multiple settings at once"""
        response = requests.post(
            f"{BASE_URL}/api/auto-trade/settings",
            headers={**self.headers, "Content-Type": "application/json"},
            json={
                "dt_take_profit_pct": 3.0,
                "dt_stop_loss_pct": 1.0,
                "max_daily_loss_pct": 4.0
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["dt_take_profit_pct"] == 3.0
        assert data["dt_stop_loss_pct"] == 1.0
        assert data["max_daily_loss_pct"] == 4.0
        
        # Restore defaults
        requests.post(
            f"{BASE_URL}/api/auto-trade/settings",
            headers={**self.headers, "Content-Type": "application/json"},
            json={
                "dt_take_profit_pct": 2.5,
                "dt_stop_loss_pct": 0.8,
                "max_daily_loss_pct": 3.0
            }
        )
        
        print("✓ Multiple settings update works correctly")
    
    # ============ EMERGENCY PAUSE ENDPOINT ============
    
    def test_emergency_pause(self):
        """Test emergency pause functionality"""
        # Activate emergency pause
        response = requests.post(
            f"{BASE_URL}/api/auto-trade/emergency-pause?pause=true",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["emergency_pause"] == True
        assert "PAUSED" in data["message"]
        
        # Verify in status
        status = requests.get(f"{BASE_URL}/api/auto-trade/status", headers=self.headers).json()
        assert status["emergency_pause"] == True
        
        # Deactivate
        response = requests.post(
            f"{BASE_URL}/api/auto-trade/emergency-pause?pause=false",
            headers=self.headers
        )
        assert response.status_code == 200
        assert response.json()["emergency_pause"] == False
        
        print("✓ Emergency pause works correctly")
    
    # ============ HISTORY ENDPOINT ============
    
    def test_auto_trade_history(self):
        """Test /api/auto-trade/history returns list"""
        response = requests.get(
            f"{BASE_URL}/api/auto-trade/history?limit=30",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ History endpoint returns list with {len(data)} items")
    
    # ============ MARKET REGIME VALIDATION ============
    
    def test_market_regime_values(self):
        """Test market regime has valid values"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/status", headers=self.headers)
        assert response.status_code == 200
        
        regime = response.json()["market_regime"]
        
        # Regime should be one of expected values
        valid_regimes = ["bullish", "neutral_bullish", "neutral", "neutral_bearish", "bearish", "high_volatility"]
        assert regime["regime"] in valid_regimes, f"Invalid regime: {regime['regime']}"
        
        # Volatility should be one of expected values
        valid_volatility = ["low", "normal", "high", "extreme"]
        assert regime["volatility"] in valid_volatility, f"Invalid volatility: {regime['volatility']}"
        
        # Score should be 0-100
        assert 0 <= regime["score"] <= 100, f"Invalid score: {regime['score']}"
        
        # Volatility pct should be positive
        assert regime["volatility_pct"] >= 0, f"Invalid volatility_pct: {regime['volatility_pct']}"
        
        print(f"✓ Market regime values are valid: {regime['regime']}, vol={regime['volatility']}, score={regime['score']}")


class TestAutoTradeDataIntegrity:
    """Test data integrity and consistency"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": "Bullishalmarkhan7.7"}
        )
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_scan_stats_valid(self):
        """Test that scan stats are valid and arrays are populated"""
        response = requests.get(
            f"{BASE_URL}/api/auto-trade/scan",
            headers=self.headers,
            timeout=60
        )
        assert response.status_code == 200
        
        data = response.json()
        stats = data["stats"]
        
        # Verify stats are valid numbers
        assert stats["total_scanned"] > 0, "Should scan some stocks"
        assert stats["day_trade_candidates"] >= 0
        assert stats["long_term_candidates"] >= 0
        assert stats["watchlist"] >= 0
        
        # Arrays should be populated (may be paginated, so <= stats count)
        assert len(data["day_trades"]) <= stats["day_trade_candidates"]
        assert len(data["long_term"]) <= stats["long_term_candidates"]
        assert len(data["watchlist"]) <= stats["watchlist"]
        
        print(f"✓ Stats valid: Scanned={stats['total_scanned']}, DT={stats['day_trade_candidates']}, LT={stats['long_term_candidates']}, WL={stats['watchlist']}")
    
    def test_candidate_confidence_scores_valid(self):
        """Test that confidence scores are in valid range"""
        response = requests.get(
            f"{BASE_URL}/api/auto-trade/scan",
            headers=self.headers,
            timeout=60
        )
        assert response.status_code == 200
        
        data = response.json()
        
        for candidate in data.get("long_term", [])[:10]:
            conf = candidate.get("confidence", 0)
            assert 0 <= conf <= 100, f"Invalid confidence for {candidate['symbol']}: {conf}"
        
        for candidate in data.get("day_trades", [])[:10]:
            conf = candidate.get("confidence", 0)
            assert 0 <= conf <= 100, f"Invalid confidence for {candidate['symbol']}: {conf}"
        
        print("✓ All confidence scores are in valid range (0-100)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
