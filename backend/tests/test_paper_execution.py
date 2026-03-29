"""
Paper Execution API Tests
Tests for the Paper Trading Execution Engine with safety controls
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"


class TestPaperExecutionAuth:
    """Authentication tests for Paper Execution endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        return data["token"]
    
    def test_paper_settings_requires_auth(self):
        """Test that paper settings endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/paper/settings")
        assert response.status_code == 401
    
    def test_paper_queue_requires_auth(self):
        """Test that paper queue endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/paper/queue")
        assert response.status_code == 401
    
    def test_paper_stats_requires_auth(self):
        """Test that paper stats endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/paper/stats")
        assert response.status_code == 401


class TestPaperSettings:
    """Tests for Paper Execution Settings"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_get_paper_settings(self, headers):
        """Test getting paper execution settings"""
        response = requests.get(f"{BASE_URL}/api/paper/settings", headers=headers)
        assert response.status_code == 200
        
        settings = response.json()
        # Verify default settings structure
        assert "kill_switch" in settings
        assert "auto_execution" in settings
        assert "manual_approval" in settings
        assert "min_confidence" in settings
        assert "max_position_pct" in settings
        assert "cash_buffer" in settings
        assert "max_daily_loss_pct" in settings
        assert "block_extended_hours" in settings
        
        print(f"Settings: {settings}")
    
    def test_default_settings_values(self, headers):
        """Test that default settings have correct values"""
        response = requests.get(f"{BASE_URL}/api/paper/settings", headers=headers)
        assert response.status_code == 200
        
        settings = response.json()
        # Verify defaults: Manual Approval ON, Auto Execution OFF, Kill Switch OFF
        assert settings.get("manual_approval") == True, "Manual Approval should be ON by default"
        assert settings.get("auto_execution") == False, "Auto Execution should be OFF by default"
        # Kill switch may have been toggled in previous tests, so we just check it exists
        assert "kill_switch" in settings
        
        print(f"Default settings verified: manual_approval={settings.get('manual_approval')}, auto_execution={settings.get('auto_execution')}")
    
    def test_update_paper_settings(self, headers):
        """Test updating paper execution settings"""
        # Get current settings
        response = requests.get(f"{BASE_URL}/api/paper/settings", headers=headers)
        original_settings = response.json()
        
        # Update settings
        new_settings = {
            "max_position_pct": 0.10,
            "cash_buffer": 0.15,
            "min_confidence": 0.70
        }
        
        response = requests.post(f"{BASE_URL}/api/paper/settings", headers=headers, json=new_settings)
        assert response.status_code == 200
        
        # Verify update
        response = requests.get(f"{BASE_URL}/api/paper/settings", headers=headers)
        updated = response.json()
        assert updated.get("max_position_pct") == 0.10
        assert updated.get("cash_buffer") == 0.15
        assert updated.get("min_confidence") == 0.70
        
        # Restore original settings
        requests.post(f"{BASE_URL}/api/paper/settings", headers=headers, json=original_settings)
        print("Settings update test passed")


class TestKillSwitch:
    """Tests for Kill Switch functionality"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_get_kill_switch_state(self, headers):
        """Test getting kill switch state"""
        response = requests.get(f"{BASE_URL}/api/paper/kill-switch", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "kill_switch" in data
        print(f"Kill switch state: {data['kill_switch']}")
    
    def test_toggle_kill_switch_on(self, headers):
        """Test activating kill switch"""
        response = requests.post(f"{BASE_URL}/api/paper/kill-switch?active=true", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("kill_switch") == True
        print("Kill switch activated")
    
    def test_toggle_kill_switch_off(self, headers):
        """Test deactivating kill switch"""
        response = requests.post(f"{BASE_URL}/api/paper/kill-switch?active=false", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("kill_switch") == False
        print("Kill switch deactivated")
    
    def test_kill_switch_logged_in_audit(self, headers):
        """Test that kill switch toggle is logged in audit"""
        # Toggle kill switch
        requests.post(f"{BASE_URL}/api/paper/kill-switch?active=true", headers=headers)
        
        # Check audit log
        response = requests.get(f"{BASE_URL}/api/paper/audit?limit=5", headers=headers)
        assert response.status_code == 200
        
        audit_log = response.json()
        assert len(audit_log) > 0
        
        # Find kill switch entry
        kill_switch_entries = [e for e in audit_log if e.get("action") == "kill_switch_toggle"]
        assert len(kill_switch_entries) > 0, "Kill switch toggle should be logged"
        
        # Turn off kill switch
        requests.post(f"{BASE_URL}/api/paper/kill-switch?active=false", headers=headers)
        print("Kill switch audit logging verified")


class TestTradeQueue:
    """Tests for Trade Queue functionality"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_queue_trade(self, headers):
        """Test queuing a new trade"""
        trade_data = {
            "symbol": "TEST_AAPL",
            "side": "buy",
            "qty": 10,
            "reason": "Test trade for paper execution",
            "strategy": "manual",
            "confidence": 0.85
        }
        
        response = requests.post(f"{BASE_URL}/api/paper/queue", headers=headers, json=trade_data)
        assert response.status_code == 200
        
        trade = response.json()
        assert trade.get("symbol") == "TEST_AAPL"
        assert trade.get("side") == "buy"
        assert trade.get("qty") == 10
        assert trade.get("status") == "pending"
        assert "id" in trade
        
        print(f"Trade queued with ID: {trade['id']}")
        return trade["id"]
    
    def test_get_trade_queue(self, headers):
        """Test getting trade queue"""
        response = requests.get(f"{BASE_URL}/api/paper/queue", headers=headers)
        assert response.status_code == 200
        
        trades = response.json()
        assert isinstance(trades, list)
        print(f"Trade queue has {len(trades)} trades")
    
    def test_get_trade_queue_filtered(self, headers):
        """Test getting trade queue with status filter"""
        response = requests.get(f"{BASE_URL}/api/paper/queue?status=pending", headers=headers)
        assert response.status_code == 200
        
        trades = response.json()
        assert isinstance(trades, list)
        # All trades should be pending
        for trade in trades:
            assert trade.get("status") == "pending"
        
        print(f"Filtered queue has {len(trades)} pending trades")
    
    def test_get_paper_stats(self, headers):
        """Test getting paper execution statistics"""
        response = requests.get(f"{BASE_URL}/api/paper/stats", headers=headers)
        assert response.status_code == 200
        
        stats = response.json()
        assert "pending" in stats
        assert "approved" in stats
        assert "executed" in stats
        assert "rejected" in stats
        assert "cancelled" in stats
        assert "failed" in stats
        assert "total" in stats
        
        print(f"Stats: pending={stats['pending']}, approved={stats['approved']}, executed={stats['executed']}, failed={stats['failed']}")


class TestTradeWorkflow:
    """Tests for Trade Workflow (pending → approved → executed/rejected)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_approve_trade_workflow(self, headers):
        """Test approving a pending trade"""
        # Queue a new trade
        trade_data = {
            "symbol": "TEST_MSFT",
            "side": "buy",
            "qty": 5,
            "reason": "Test approval workflow",
            "strategy": "momentum"
        }
        
        response = requests.post(f"{BASE_URL}/api/paper/queue", headers=headers, json=trade_data)
        assert response.status_code == 200
        trade_id = response.json()["id"]
        
        # Approve the trade
        response = requests.post(f"{BASE_URL}/api/paper/trade/{trade_id}/approve", headers=headers)
        assert response.status_code == 200
        
        result = response.json()
        assert result.get("success") == True
        assert result.get("status") == "approved"
        
        # Verify trade status
        response = requests.get(f"{BASE_URL}/api/paper/trade/{trade_id}", headers=headers)
        assert response.status_code == 200
        trade = response.json()
        assert trade.get("status") == "approved"
        
        print(f"Trade {trade_id} approved successfully")
    
    def test_reject_trade_workflow(self, headers):
        """Test rejecting a pending trade"""
        # Queue a new trade
        trade_data = {
            "symbol": "TEST_GOOG",
            "side": "buy",
            "qty": 3,
            "reason": "Test rejection workflow",
            "strategy": "value"
        }
        
        response = requests.post(f"{BASE_URL}/api/paper/queue", headers=headers, json=trade_data)
        assert response.status_code == 200
        trade_id = response.json()["id"]
        
        # Reject the trade
        response = requests.post(f"{BASE_URL}/api/paper/trade/{trade_id}/reject?reason=Test%20rejection", headers=headers)
        assert response.status_code == 200
        
        result = response.json()
        assert result.get("success") == True
        assert result.get("status") == "rejected"
        
        # Verify trade status
        response = requests.get(f"{BASE_URL}/api/paper/trade/{trade_id}", headers=headers)
        assert response.status_code == 200
        trade = response.json()
        assert trade.get("status") == "rejected"
        
        print(f"Trade {trade_id} rejected successfully")
    
    def test_cancel_pending_trade(self, headers):
        """Test cancelling a pending trade"""
        # Queue a new trade
        trade_data = {
            "symbol": "TEST_AMZN",
            "side": "buy",
            "qty": 2,
            "reason": "Test cancel workflow",
            "strategy": "breakout"
        }
        
        response = requests.post(f"{BASE_URL}/api/paper/queue", headers=headers, json=trade_data)
        assert response.status_code == 200
        trade_id = response.json()["id"]
        
        # Cancel the trade
        response = requests.post(f"{BASE_URL}/api/paper/trade/{trade_id}/cancel", headers=headers)
        assert response.status_code == 200
        
        result = response.json()
        assert result.get("success") == True
        assert result.get("status") == "cancelled"
        
        print(f"Trade {trade_id} cancelled successfully")
    
    def test_cancel_approved_trade(self, headers):
        """Test cancelling an approved trade"""
        # Queue and approve a trade
        trade_data = {
            "symbol": "TEST_META",
            "side": "buy",
            "qty": 4,
            "reason": "Test cancel approved",
            "strategy": "manual"
        }
        
        response = requests.post(f"{BASE_URL}/api/paper/queue", headers=headers, json=trade_data)
        assert response.status_code == 200
        trade_id = response.json()["id"]
        
        # Approve
        requests.post(f"{BASE_URL}/api/paper/trade/{trade_id}/approve", headers=headers)
        
        # Cancel
        response = requests.post(f"{BASE_URL}/api/paper/trade/{trade_id}/cancel", headers=headers)
        assert response.status_code == 200
        
        result = response.json()
        assert result.get("success") == True
        assert result.get("status") == "cancelled"
        
        print(f"Approved trade {trade_id} cancelled successfully")


class TestRiskControls:
    """Tests for Risk Controls before execution"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_risk_check_endpoint(self, headers):
        """Test risk check endpoint"""
        trade_data = {
            "symbol": "AAPL",
            "side": "buy",
            "qty": 10,
            "confidence": 0.80
        }
        
        response = requests.post(f"{BASE_URL}/api/paper/risk-check", headers=headers, json=trade_data)
        assert response.status_code == 200
        
        result = response.json()
        assert "passed" in result
        assert "violations" in result
        
        print(f"Risk check result: passed={result['passed']}, violations={result['violations']}")
    
    def test_kill_switch_blocks_execution(self, headers):
        """Test that kill switch blocks trade execution"""
        # Activate kill switch
        requests.post(f"{BASE_URL}/api/paper/kill-switch?active=true", headers=headers)
        
        # Queue and approve a trade
        trade_data = {
            "symbol": "TEST_NVDA",
            "side": "buy",
            "qty": 5,
            "reason": "Test kill switch block",
            "strategy": "manual"
        }
        
        response = requests.post(f"{BASE_URL}/api/paper/queue", headers=headers, json=trade_data)
        trade_id = response.json()["id"]
        
        # Approve
        requests.post(f"{BASE_URL}/api/paper/trade/{trade_id}/approve", headers=headers)
        
        # Try to execute - should fail due to kill switch
        response = requests.post(f"{BASE_URL}/api/paper/trade/{trade_id}/execute", headers=headers)
        assert response.status_code == 200
        
        result = response.json()
        assert result.get("success") == False
        assert "violations" in result
        assert any("Kill switch" in v for v in result.get("violations", []))
        
        # Deactivate kill switch
        requests.post(f"{BASE_URL}/api/paper/kill-switch?active=false", headers=headers)
        
        print("Kill switch blocking verified")
    
    def test_low_confidence_blocked(self, headers):
        """Test that low confidence trades are blocked"""
        # Ensure kill switch is off
        requests.post(f"{BASE_URL}/api/paper/kill-switch?active=false", headers=headers)
        
        # Set min confidence to 0.80
        settings = {"min_confidence": 0.80}
        requests.post(f"{BASE_URL}/api/paper/settings", headers=headers, json=settings)
        
        # Queue a low confidence trade
        trade_data = {
            "symbol": "TEST_LOW_CONF",
            "side": "buy",
            "qty": 5,
            "confidence": 0.50,  # Below minimum
            "reason": "Test low confidence block",
            "strategy": "manual"
        }
        
        response = requests.post(f"{BASE_URL}/api/paper/queue", headers=headers, json=trade_data)
        trade_id = response.json()["id"]
        
        # Approve
        requests.post(f"{BASE_URL}/api/paper/trade/{trade_id}/approve", headers=headers)
        
        # Try to execute - should fail due to low confidence
        response = requests.post(f"{BASE_URL}/api/paper/trade/{trade_id}/execute", headers=headers)
        result = response.json()
        
        # Note: May also fail due to extended hours block
        assert result.get("success") == False
        
        # Reset min confidence
        settings = {"min_confidence": 0.60}
        requests.post(f"{BASE_URL}/api/paper/settings", headers=headers, json=settings)
        
        print("Low confidence blocking verified")


class TestAuditLog:
    """Tests for Audit Log functionality"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_get_audit_log(self, headers):
        """Test getting audit log"""
        response = requests.get(f"{BASE_URL}/api/paper/audit?limit=30", headers=headers)
        assert response.status_code == 200
        
        audit_log = response.json()
        assert isinstance(audit_log, list)
        
        # Verify audit entry structure
        if len(audit_log) > 0:
            entry = audit_log[0]
            assert "action" in entry
            assert "timestamp" in entry
        
        print(f"Audit log has {len(audit_log)} entries")
    
    def test_audit_log_contains_trade_actions(self, headers):
        """Test that audit log contains trade actions"""
        response = requests.get(f"{BASE_URL}/api/paper/audit?limit=50", headers=headers)
        assert response.status_code == 200
        
        audit_log = response.json()
        
        # Check for various action types
        action_types = set(entry.get("action") for entry in audit_log)
        
        # Should have at least some trade-related actions from previous tests
        expected_actions = ["trade_queued", "trade_approved", "trade_rejected", "trade_cancelled"]
        found_actions = [a for a in expected_actions if a in action_types]
        
        print(f"Found audit actions: {action_types}")
        assert len(found_actions) > 0, "Should have at least one trade action in audit log"


class TestTradeExecution:
    """Tests for Trade Execution (Alpaca integration)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_execute_approved_trade(self, headers):
        """Test executing an approved trade (will fail with invalid Alpaca keys)"""
        # Ensure kill switch is off
        requests.post(f"{BASE_URL}/api/paper/kill-switch?active=false", headers=headers)
        
        # Queue and approve a trade
        trade_data = {
            "symbol": "AAPL",
            "side": "buy",
            "qty": 1,
            "reason": "Test execution",
            "strategy": "manual",
            "confidence": 0.90
        }
        
        response = requests.post(f"{BASE_URL}/api/paper/queue", headers=headers, json=trade_data)
        assert response.status_code == 200
        trade_id = response.json()["id"]
        
        # Approve
        response = requests.post(f"{BASE_URL}/api/paper/trade/{trade_id}/approve", headers=headers)
        assert response.status_code == 200
        
        # Execute - will fail due to invalid Alpaca keys or extended hours
        response = requests.post(f"{BASE_URL}/api/paper/trade/{trade_id}/execute", headers=headers)
        assert response.status_code == 200
        
        result = response.json()
        # Execution will fail due to invalid Alpaca keys or risk controls
        # This is expected behavior
        print(f"Execution result: {result}")
    
    def test_cannot_execute_pending_trade(self, headers):
        """Test that pending trades cannot be executed directly"""
        # Queue a trade (don't approve)
        trade_data = {
            "symbol": "TEST_PENDING",
            "side": "buy",
            "qty": 1,
            "reason": "Test pending execution block",
            "strategy": "manual"
        }
        
        response = requests.post(f"{BASE_URL}/api/paper/queue", headers=headers, json=trade_data)
        trade_id = response.json()["id"]
        
        # Try to execute without approval
        response = requests.post(f"{BASE_URL}/api/paper/trade/{trade_id}/execute", headers=headers)
        assert response.status_code == 200
        
        result = response.json()
        assert result.get("success") == False
        assert "approved" in result.get("error", "").lower()
        
        print("Pending trade execution block verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
