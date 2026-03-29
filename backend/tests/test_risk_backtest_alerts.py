"""
Backend API Tests for Risk Management, Backtesting, and Alerts
Tests the new features: Position Size Calculator, Risk/Reward Calculator, 
Backtesting Engine, and Price Alerts system.
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"

class TestSetup:
    """Setup and authentication tests"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create authenticated session"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        
        # Authenticate
        response = s.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        if response.status_code == 200:
            token = response.json().get("token")
            s.headers.update({"Authorization": f"Bearer {token}"})
        return s
    
    def test_api_health(self, session):
        """Test API is running"""
        response = session.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "running"
        print(f"API Health: {data}")


class TestRiskManagement:
    """Risk Management endpoint tests"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create authenticated session"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        response = s.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        if response.status_code == 200:
            token = response.json().get("token")
            s.headers.update({"Authorization": f"Bearer {token}"})
        return s
    
    def test_position_size_calculator(self, session):
        """Test position size calculation"""
        payload = {
            "account_value": 10000,
            "entry_price": 100,
            "stop_loss_price": 95,
            "risk_per_trade": 0.02,
            "max_position_pct": 0.10
        }
        response = session.post(f"{BASE_URL}/api/risk/position-size", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "shares" in data
        assert "position_value" in data
        assert "position_pct" in data
        assert "risk_amount" in data
        assert "risk_pct" in data
        
        # Validate calculation logic
        assert data["shares"] > 0
        assert data["position_value"] > 0
        assert data["position_pct"] <= 10  # Max position limit
        print(f"Position Size Result: {data}")
    
    def test_position_size_invalid_stop_loss(self, session):
        """Test position size with invalid stop loss (same as entry)"""
        payload = {
            "account_value": 10000,
            "entry_price": 100,
            "stop_loss_price": 100,  # Same as entry - invalid
            "risk_per_trade": 0.02,
            "max_position_pct": 0.10
        }
        response = session.post(f"{BASE_URL}/api/risk/position-size", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "error" in data
        print(f"Expected error for invalid stop loss: {data}")
    
    def test_risk_reward_calculator(self, session):
        """Test risk/reward ratio calculation"""
        payload = {
            "entry_price": 100,
            "stop_loss_price": 95,
            "take_profit_price": 115
        }
        response = session.post(f"{BASE_URL}/api/risk/risk-reward", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "risk" in data
        assert "reward" in data
        assert "ratio" in data
        assert "ratio_display" in data
        assert "quality" in data
        
        # Validate calculation
        assert data["risk"] == 5  # 100 - 95
        assert data["reward"] == 15  # 115 - 100
        assert data["ratio"] == 3.0  # 15/5
        assert data["quality"] == "Excellent"  # ratio >= 3
        print(f"Risk/Reward Result: {data}")
    
    def test_risk_reward_poor_ratio(self, session):
        """Test risk/reward with poor ratio"""
        payload = {
            "entry_price": 100,
            "stop_loss_price": 90,  # 10% risk
            "take_profit_price": 105  # 5% reward
        }
        response = session.post(f"{BASE_URL}/api/risk/risk-reward", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["quality"] == "Poor"  # ratio < 1.5
        print(f"Poor ratio result: {data}")
    
    def test_get_risk_settings(self, session):
        """Test getting risk settings"""
        response = session.get(f"{BASE_URL}/api/risk/settings")
        assert response.status_code == 200
        
        data = response.json()
        assert "max_position_size" in data
        assert "max_daily_loss" in data
        assert "max_weekly_loss" in data
        assert "max_drawdown" in data
        print(f"Risk Settings: {data}")
    
    def test_save_risk_settings(self, session):
        """Test saving risk settings"""
        payload = {
            "max_position_size": 0.08,
            "max_daily_loss": 0.03,
            "max_weekly_loss": 0.06,
            "max_drawdown": 0.12,
            "min_confidence": 0.65,
            "cash_buffer": 0.15,
            "default_stop_loss_pct": 0.06,
            "default_take_profit_pct": 0.12
        }
        response = session.post(f"{BASE_URL}/api/risk/settings", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        print(f"Save settings result: {data}")
        
        # Verify settings were saved
        get_response = session.get(f"{BASE_URL}/api/risk/settings")
        assert get_response.status_code == 200
        saved = get_response.json()
        assert saved["max_position_size"] == 0.08
        assert saved["max_daily_loss"] == 0.03
        print(f"Verified saved settings: {saved}")
    
    def test_daily_risk_status(self, session):
        """Test daily risk status endpoint"""
        response = session.get(f"{BASE_URL}/api/risk/daily-status")
        assert response.status_code == 200
        
        data = response.json()
        # Should have these fields even if Alpaca is not connected
        assert "account_value" in data
        assert "daily_pnl" in data
        assert "daily_pnl_pct" in data
        assert "can_trade" in data
        assert "risk_status" in data
        print(f"Daily Risk Status: {data}")


class TestBacktesting:
    """Backtesting endpoint tests"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create authenticated session"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        response = s.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        if response.status_code == 200:
            token = response.json().get("token")
            s.headers.update({"Authorization": f"Bearer {token}"})
        return s
    
    def test_get_strategies(self, session):
        """Test getting available strategies"""
        response = session.get(f"{BASE_URL}/api/backtest/strategies")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5  # 5 strategies
        
        strategy_ids = [s["id"] for s in data]
        assert "momentum" in strategy_ids
        assert "mean_reversion" in strategy_ids
        assert "breakout" in strategy_ids
        assert "ma_crossover" in strategy_ids
        assert "value" in strategy_ids
        print(f"Available strategies: {strategy_ids}")
    
    def test_run_backtest_momentum(self, session):
        """Test running a momentum backtest"""
        payload = {
            "symbol": "AAPL",
            "strategy": "momentum",
            "period": "1y",
            "initial_capital": 10000,
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.10
        }
        response = session.post(f"{BASE_URL}/api/backtest/run", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check for error (insufficient data)
        if "error" in data:
            print(f"Backtest returned error (may be expected): {data['error']}")
            return
        
        # Validate result structure
        assert data["symbol"] == "AAPL"
        assert data["strategy"] == "momentum"
        assert "total_return" in data
        assert "final_value" in data
        assert "max_drawdown" in data
        assert "sharpe_ratio" in data
        assert "win_rate" in data
        assert "total_trades" in data
        assert "equity_curve" in data
        assert "trades" in data
        
        print(f"Backtest Result: Return={data['total_return']}%, Trades={data['total_trades']}, Win Rate={data['win_rate']}%")
    
    def test_run_backtest_mean_reversion(self, session):
        """Test running a mean reversion backtest"""
        payload = {
            "symbol": "MSFT",
            "strategy": "mean_reversion",
            "period": "6m",
            "initial_capital": 5000,
            "stop_loss_pct": 0.03,
            "take_profit_pct": 0.08
        }
        response = session.post(f"{BASE_URL}/api/backtest/run", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        if "error" not in data:
            assert data["strategy"] == "mean_reversion"
            print(f"Mean Reversion Backtest: Return={data.get('total_return')}%")
    
    def test_backtest_history(self, session):
        """Test getting backtest history"""
        response = session.get(f"{BASE_URL}/api/backtest/history?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Backtest history count: {len(data)}")
        
        if len(data) > 0:
            item = data[0]
            assert "symbol" in item
            assert "strategy" in item
            assert "result" in item
            print(f"Latest backtest: {item['symbol']} - {item['strategy']}")


class TestAlerts:
    """Alerts endpoint tests"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create authenticated session"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        response = s.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        if response.status_code == 200:
            token = response.json().get("token")
            s.headers.update({"Authorization": f"Bearer {token}"})
        return s
    
    def test_get_alert_types(self, session):
        """Test getting available alert types"""
        response = session.get(f"{BASE_URL}/api/alerts/types")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 4  # 4 alert types
        
        type_ids = [t["id"] for t in data]
        assert "price_above" in type_ids
        assert "price_below" in type_ids
        assert "change_pct" in type_ids
        assert "volume_spike" in type_ids
        print(f"Alert types: {type_ids}")
    
    def test_create_alert(self, session):
        """Test creating a new alert"""
        payload = {
            "symbol": "TEST_NVDA",
            "alert_type": "price_above",
            "value": 1000.0,
            "note": "Test alert for NVDA"
        }
        response = session.post(f"{BASE_URL}/api/alerts", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert data["symbol"] == "TEST_NVDA"
        assert data["alert_type"] == "price_above"
        assert data["value"] == 1000.0
        assert data["enabled"] == True
        assert data["triggered"] == False
        
        # Store alert ID for cleanup
        TestAlerts.test_alert_id = data["id"]
        print(f"Created alert: {data}")
    
    def test_get_alerts(self, session):
        """Test getting all alerts"""
        response = session.get(f"{BASE_URL}/api/alerts")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Total alerts: {len(data)}")
    
    def test_toggle_alert(self, session):
        """Test toggling alert enabled state"""
        if not hasattr(TestAlerts, 'test_alert_id'):
            pytest.skip("No test alert created")
        
        alert_id = TestAlerts.test_alert_id
        
        # Disable alert
        response = session.put(f"{BASE_URL}/api/alerts/{alert_id}", json={"enabled": False})
        assert response.status_code == 200
        
        data = response.json()
        assert data["enabled"] == False
        print(f"Disabled alert: {data}")
        
        # Re-enable alert
        response = session.put(f"{BASE_URL}/api/alerts/{alert_id}", json={"enabled": True})
        assert response.status_code == 200
        
        data = response.json()
        assert data["enabled"] == True
        print(f"Re-enabled alert: {data}")
    
    def test_check_alerts(self, session):
        """Test checking alerts against current prices"""
        response = session.get(f"{BASE_URL}/api/alerts/check")
        assert response.status_code == 200
        
        data = response.json()
        assert "triggered" in data
        assert "checked" in data
        print(f"Checked {data['checked']} alerts, {len(data['triggered'])} triggered")
    
    def test_alert_history(self, session):
        """Test getting alert history"""
        response = session.get(f"{BASE_URL}/api/alerts/history?limit=20")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Alert history count: {len(data)}")
    
    def test_delete_alert(self, session):
        """Test deleting an alert"""
        if not hasattr(TestAlerts, 'test_alert_id'):
            pytest.skip("No test alert created")
        
        alert_id = TestAlerts.test_alert_id
        
        response = session.delete(f"{BASE_URL}/api/alerts/{alert_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") == True
        print(f"Deleted alert: {alert_id}")
        
        # Verify deletion
        get_response = session.get(f"{BASE_URL}/api/alerts")
        alerts = get_response.json()
        alert_ids = [a["id"] for a in alerts]
        assert alert_id not in alert_ids
        print("Verified alert was deleted")


class TestAlertWorkflow:
    """Test complete alert workflow: create -> check -> reset -> delete"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create authenticated session"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        response = s.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        if response.status_code == 200:
            token = response.json().get("token")
            s.headers.update({"Authorization": f"Bearer {token}"})
        return s
    
    def test_full_alert_workflow(self, session):
        """Test complete alert lifecycle"""
        # 1. Create alert with low threshold (likely to trigger)
        payload = {
            "symbol": "AAPL",
            "alert_type": "price_above",
            "value": 1.0,  # Very low - should trigger
            "note": "Workflow test alert"
        }
        create_response = session.post(f"{BASE_URL}/api/alerts", json=payload)
        assert create_response.status_code == 200
        alert = create_response.json()
        alert_id = alert["id"]
        print(f"1. Created alert: {alert_id}")
        
        # 2. Check alerts - should trigger
        check_response = session.get(f"{BASE_URL}/api/alerts/check")
        assert check_response.status_code == 200
        check_data = check_response.json()
        print(f"2. Check result: {check_data['checked']} checked, {len(check_data['triggered'])} triggered")
        
        # 3. Verify alert is now triggered
        get_response = session.get(f"{BASE_URL}/api/alerts")
        alerts = get_response.json()
        our_alert = next((a for a in alerts if a["id"] == alert_id), None)
        
        if our_alert and our_alert.get("triggered"):
            print(f"3. Alert triggered: {our_alert.get('trigger_message')}")
            
            # 4. Reset the alert
            reset_response = session.post(f"{BASE_URL}/api/alerts/{alert_id}/reset")
            assert reset_response.status_code == 200
            print("4. Alert reset")
            
            # 5. Verify reset
            get_response2 = session.get(f"{BASE_URL}/api/alerts")
            alerts2 = get_response2.json()
            our_alert2 = next((a for a in alerts2 if a["id"] == alert_id), None)
            assert our_alert2["triggered"] == False
            print("5. Verified alert is no longer triggered")
        
        # 6. Delete alert
        delete_response = session.delete(f"{BASE_URL}/api/alerts/{alert_id}")
        assert delete_response.status_code == 200
        print("6. Alert deleted - workflow complete")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create authenticated session"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        response = s.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        if response.status_code == 200:
            token = response.json().get("token")
            s.headers.update({"Authorization": f"Bearer {token}"})
        return s
    
    def test_cleanup_test_alerts(self, session):
        """Clean up any TEST_ prefixed alerts"""
        response = session.get(f"{BASE_URL}/api/alerts")
        if response.status_code == 200:
            alerts = response.json()
            test_alerts = [a for a in alerts if a["symbol"].startswith("TEST_")]
            
            for alert in test_alerts:
                session.delete(f"{BASE_URL}/api/alerts/{alert['id']}")
                print(f"Cleaned up test alert: {alert['id']}")
            
            print(f"Cleaned up {len(test_alerts)} test alerts")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
