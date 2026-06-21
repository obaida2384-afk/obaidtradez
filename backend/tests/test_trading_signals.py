"""
Test Trading Signals API - Full Universe Scan with MongoDB Caching
Tests: /api/trading/scan, /api/trading/refresh, /api/trading/analyze/{symbol}
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestTradingSignals:
    """Trading Signals API tests for full universe scan feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": "Bullishalmarkhan7.7"})
        assert response.status_code == 200, f"Auth failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        self.token = data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_trading_scan_returns_signals(self):
        """Test /api/trading/scan returns trading signals with diagnostics"""
        response = requests.get(f"{BASE_URL}/api/trading/scan", headers=self.headers)
        assert response.status_code == 200, f"Scan failed: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "top_trades" in data, "Missing top_trades in response"
        assert "hot" in data, "Missing hot category"
        assert "breakout" in data, "Missing breakout category"
        assert "momentum" in data, "Missing momentum category"
        assert "high_volume" in data, "Missing high_volume category"
        assert "watch" in data, "Missing watch category"
        assert "all" in data, "Missing all signals"
        assert "diagnostics" in data, "Missing diagnostics"
        
        # Verify diagnostics structure
        diagnostics = data["diagnostics"]
        assert "stocks_scanned" in diagnostics, "Missing stocks_scanned in diagnostics"
        assert "signals_generated" in diagnostics, "Missing signals_generated in diagnostics"
        assert "source" in diagnostics, "Missing source in diagnostics"
        assert "filters_applied" in diagnostics, "Missing filters_applied in diagnostics"
        
        print(f"Stocks scanned: {diagnostics['stocks_scanned']}")
        print(f"Signals generated: {diagnostics['signals_generated']}")
        print(f"Source: {diagnostics['source']}")
    
    def test_trading_scan_has_cached_signals(self):
        """Test that scan returns cached signals from full universe"""
        response = requests.get(f"{BASE_URL}/api/trading/scan", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        diagnostics = data["diagnostics"]
        
        # Should have cached signals from background scan
        assert diagnostics["stocks_scanned"] >= 100, f"Expected 100+ stocks scanned, got {diagnostics['stocks_scanned']}"
        assert diagnostics["signals_generated"] >= 10, f"Expected 10+ signals, got {diagnostics['signals_generated']}"
        
        # Source should be 'cached' if background scan completed
        print(f"Source: {diagnostics['source']}")
        print(f"Hot: {len(data.get('hot', []))}")
        print(f"Breakout: {len(data.get('breakout', []))}")
        print(f"Momentum: {len(data.get('momentum', []))}")
        print(f"High Volume: {len(data.get('high_volume', []))}")
        print(f"Watch: {len(data.get('watch', []))}")
        print(f"All: {len(data.get('all', []))}")
    
    def test_trading_scan_signal_structure(self):
        """Test that trading signals have correct structure"""
        response = requests.get(f"{BASE_URL}/api/trading/scan", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        all_signals = data.get("all", [])
        
        if len(all_signals) > 0:
            signal = all_signals[0]
            
            # Required fields
            assert "symbol" in signal, "Missing symbol"
            assert "name" in signal, "Missing name"
            assert "signal" in signal, "Missing signal type"
            assert "confidence" in signal, "Missing confidence"
            assert "category" in signal, "Missing category"
            
            # Trading setup fields
            assert "entry_zone" in signal, "Missing entry_zone"
            assert "stop_loss" in signal, "Missing stop_loss"
            assert "take_profit" in signal, "Missing take_profit"
            assert "risk_reward" in signal, "Missing risk_reward"
            
            # Indicators
            assert "indicators" in signal, "Missing indicators"
            
            print(f"Sample signal: {signal['symbol']} - {signal['signal']} ({signal['category']})")
            print(f"Entry: {signal['entry_zone']}, SL: {signal['stop_loss']}, TP: {signal['take_profit']}")
    
    def test_trading_refresh_triggers_background_task(self):
        """Test /api/trading/refresh triggers background scan"""
        response = requests.post(f"{BASE_URL}/api/trading/refresh?limit=100", headers=self.headers)
        assert response.status_code == 200, f"Refresh failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Missing message in response"
        assert "status" in data, "Missing status in response"
        assert data["status"] == "processing", f"Expected processing status, got {data['status']}"
        
        print(f"Refresh response: {data['message']}")
    
    def test_trading_analyze_symbol(self):
        """Test /api/trading/analyze/{symbol} for individual stock analysis"""
        # Test with a common stock
        response = requests.get(f"{BASE_URL}/api/trading/analyze/MSFT", headers=self.headers)
        assert response.status_code == 200, f"Analyze failed: {response.text}"
        
        data = response.json()
        assert "symbol" in data, "Missing symbol in response"
        assert data["symbol"] == "MSFT", f"Expected MSFT, got {data['symbol']}"
        
        # Either included with signal or excluded with reason
        if data.get("included"):
            assert "signal" in data, "Missing signal for included stock"
            signal = data["signal"]
            assert "entry_zone" in signal, "Missing entry_zone in signal"
            print(f"MSFT included: {signal.get('signal')} - {signal.get('category')}")
        else:
            assert "exclusion_reason" in data, "Missing exclusion_reason for excluded stock"
            print(f"MSFT excluded: {data['exclusion_reason']}")
    
    def test_trading_analyze_invalid_symbol(self):
        """Test analyze with invalid symbol returns 404"""
        response = requests.get(f"{BASE_URL}/api/trading/analyze/INVALIDXYZ123", headers=self.headers)
        # Should return 404 or error for invalid symbol
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            # Should be excluded or have no signal
            assert data.get("included") == False or data.get("signal") is None
    
    def test_trading_scan_categories_match_all(self):
        """Test that category counts match 'all' signals"""
        response = requests.get(f"{BASE_URL}/api/trading/scan", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        
        hot_count = len(data.get("hot", []))
        breakout_count = len(data.get("breakout", []))
        momentum_count = len(data.get("momentum", []))
        high_volume_count = len(data.get("high_volume", []))
        watch_count = len(data.get("watch", []))
        all_count = len(data.get("all", []))
        
        category_total = hot_count + breakout_count + momentum_count + high_volume_count + watch_count
        
        print(f"Category total: {category_total}, All: {all_count}")
        
        # All signals should be categorized
        assert category_total == all_count, f"Category total ({category_total}) != all ({all_count})"
    
    def test_trading_scan_unauthorized(self):
        """Test scan without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/trading/scan")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_trading_refresh_unauthorized(self):
        """Test refresh without auth returns 401"""
        response = requests.post(f"{BASE_URL}/api/trading/refresh")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
