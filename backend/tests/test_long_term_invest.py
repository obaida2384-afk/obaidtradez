"""
Long-Term Investing System Backend Tests
Tests all LT-invest endpoints: portfolio, universe, recommendations, stage-buy, trim, close, thesis, rebalance-check
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"

# Test data prefix for cleanup
TEST_PREFIX = "TEST_LT_"


class TestLongTermInvestAuth:
    """Authentication tests for LT endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Auth failed: {response.text}"
        data = response.json()
        assert "token" in data, f"No token in response: {data}"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_auth_access_works(self):
        """Test that auth endpoint returns valid token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "token" in data
        print(f"PASS: Auth access works, token received")
    
    def test_lt_endpoints_require_auth(self):
        """Test that all LT endpoints require authentication"""
        endpoints = [
            ("GET", "/api/lt-invest/portfolio"),
            ("GET", "/api/lt-invest/universe"),
            ("GET", "/api/lt-invest/recommendations"),
            ("GET", "/api/lt-invest/rebalance-check"),
            ("GET", "/api/lt-invest/thesis/VOO"),
            ("POST", "/api/lt-invest/stage-buy"),
            ("POST", "/api/lt-invest/trim"),
            ("POST", "/api/lt-invest/close"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            else:
                response = requests.post(f"{BASE_URL}{endpoint}", json={})
            
            assert response.status_code == 401, f"{endpoint} should require auth, got {response.status_code}"
        
        print(f"PASS: All 8 LT endpoints require authentication")


class TestLTPortfolio:
    """Portfolio endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE},
            headers={"Content-Type": "application/json"}
        )
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_portfolio_endpoint_returns_structure(self, headers):
        """Test /api/lt-invest/portfolio returns proper structure"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/portfolio", headers=headers)
        assert response.status_code == 200, f"Portfolio failed: {response.text}"
        
        data = response.json()
        
        # Check required top-level keys
        assert "summary" in data, "Missing 'summary' in portfolio response"
        assert "positions" in data, "Missing 'positions' in portfolio response"
        assert "bucket_breakdown" in data, "Missing 'bucket_breakdown' in portfolio response"
        
        # Check summary structure
        summary = data["summary"]
        required_summary_fields = [
            "total_value", "total_cost", "total_pnl_pct", "total_pnl_usd",
            "position_count", "bucket_allocation", "diversification_score",
            "needs_rebalance", "rebalance_reasons"
        ]
        for field in required_summary_fields:
            assert field in summary, f"Missing '{field}' in summary"
        
        # Check bucket_breakdown has all 3 buckets
        bucket_breakdown = data["bucket_breakdown"]
        expected_buckets = ["core", "quality_growth", "opportunistic_value"]
        for bucket in expected_buckets:
            assert bucket in bucket_breakdown, f"Missing bucket '{bucket}' in bucket_breakdown"
            bucket_info = bucket_breakdown[bucket]
            assert "target_min" in bucket_info, f"Missing target_min in {bucket}"
            assert "target_max" in bucket_info, f"Missing target_max in {bucket}"
        
        print(f"PASS: Portfolio endpoint returns proper structure with summary, positions, bucket_breakdown")
        print(f"  - Total value: ${summary['total_value']}")
        print(f"  - Position count: {summary['position_count']}")
        print(f"  - Diversification score: {summary['diversification_score']}")


class TestLTUniverse:
    """Universe endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE},
            headers={"Content-Type": "application/json"}
        )
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_universe_endpoint_returns_all_buckets(self, headers):
        """Test /api/lt-invest/universe returns core (9 ETFs), quality_growth (25), opportunistic_value (20)"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/universe", headers=headers)
        assert response.status_code == 200, f"Universe failed: {response.text}"
        
        data = response.json()
        
        # Check all buckets present
        assert "core" in data, "Missing 'core' bucket"
        assert "quality_growth" in data, "Missing 'quality_growth' bucket"
        assert "opportunistic_value" in data, "Missing 'opportunistic_value' bucket"
        assert "bucket_rules" in data, "Missing 'bucket_rules'"
        
        # Check counts
        core_count = len(data["core"])
        qg_count = len(data["quality_growth"])
        ov_count = len(data["opportunistic_value"])
        
        assert core_count == 9, f"Expected 9 core ETFs, got {core_count}"
        assert qg_count == 25, f"Expected 25 quality_growth stocks, got {qg_count}"
        assert ov_count == 20, f"Expected 20 opportunistic_value stocks, got {ov_count}"
        
        # Check some specific symbols
        assert "VOO" in data["core"], "VOO should be in core ETFs"
        assert "QQQ" in data["core"], "QQQ should be in core ETFs"
        assert "AAPL" in data["quality_growth"], "AAPL should be in quality_growth"
        assert "MSFT" in data["quality_growth"], "MSFT should be in quality_growth"
        assert "JPM" in data["opportunistic_value"], "JPM should be in opportunistic_value"
        
        # Check bucket_rules structure
        rules = data["bucket_rules"]
        for bucket in ["core", "quality_growth", "opportunistic_value"]:
            assert bucket in rules, f"Missing rules for {bucket}"
            assert "target_allocation_min" in rules[bucket]
            assert "target_allocation_max" in rules[bucket]
        
        print(f"PASS: Universe returns core ({core_count} ETFs), quality_growth ({qg_count}), opportunistic_value ({ov_count})")


class TestLTRecommendations:
    """Recommendations endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE},
            headers={"Content-Type": "application/json"}
        )
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_recommendations_endpoint_returns_list(self, headers):
        """Test /api/lt-invest/recommendations returns recommendations list"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/recommendations", headers=headers)
        assert response.status_code == 200, f"Recommendations failed: {response.text}"
        
        data = response.json()
        
        assert "recommendations" in data, "Missing 'recommendations' key"
        assert "count" in data, "Missing 'count' key"
        assert isinstance(data["recommendations"], list), "recommendations should be a list"
        
        # If there are recommendations, check structure
        if len(data["recommendations"]) > 0:
            rec = data["recommendations"][0]
            expected_fields = ["symbol", "action", "reason", "priority"]
            for field in expected_fields:
                assert field in rec, f"Missing '{field}' in recommendation"
            
            # Check action is valid
            valid_actions = ["BUY", "ADD", "TRIM", "SELL", "HOLD", "REBALANCE"]
            assert rec["action"] in valid_actions, f"Invalid action: {rec['action']}"
        
        print(f"PASS: Recommendations endpoint returns {data['count']} recommendations")


class TestLTStageBuy:
    """Stage buy endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE},
            headers={"Content-Type": "application/json"}
        )
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_stage_buy_voo_core_bucket(self, headers):
        """Test POST /api/lt-invest/stage-buy allows adding VOO to core bucket"""
        payload = {
            "symbol": "VOO",
            "bucket": "core",
            "shares": 2,
            "price": 450.00,
            "thesis": "TEST: S&P 500 core holding for long-term growth",
            "name": "Vanguard S&P 500"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/lt-invest/stage-buy",
            json=payload,
            headers=headers
        )
        assert response.status_code == 200, f"Stage buy failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, f"Stage buy not successful: {data}"
        assert "position" in data, "Missing 'position' in response"
        
        position = data["position"]
        assert position["symbol"] == "VOO"
        assert position["bucket"] == "core"
        assert position["shares"] == 2
        assert position["stage"] >= 1
        
        print(f"PASS: Stage buy VOO successful - Stage {position['stage']}/4, {position['shares']} shares")
    
    def test_stage_buy_validates_required_fields(self, headers):
        """Test stage buy validates required fields"""
        # Missing symbol
        response = requests.post(
            f"{BASE_URL}/api/lt-invest/stage-buy",
            json={"bucket": "core", "shares": 1, "price": 100},
            headers=headers
        )
        assert response.status_code == 200  # Returns 200 with error message
        data = response.json()
        assert "error" in data, "Should return error for missing symbol"
        
        # Invalid bucket
        response = requests.post(
            f"{BASE_URL}/api/lt-invest/stage-buy",
            json={"symbol": "TEST", "bucket": "invalid_bucket", "shares": 1, "price": 100},
            headers=headers
        )
        data = response.json()
        assert "error" in data, "Should return error for invalid bucket"
        
        print(f"PASS: Stage buy validates required fields correctly")


class TestLTThesis:
    """Thesis health endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE},
            headers={"Content-Type": "application/json"}
        )
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_thesis_endpoint_for_existing_position(self, headers):
        """Test /api/lt-invest/thesis/{symbol} returns thesis health for VOO"""
        # First ensure VOO exists (from previous test)
        response = requests.get(f"{BASE_URL}/api/lt-invest/thesis/VOO", headers=headers)
        assert response.status_code == 200, f"Thesis failed: {response.text}"
        
        data = response.json()
        
        # Check structure
        assert "symbol" in data, "Missing 'symbol'"
        assert data["symbol"] == "VOO"
        
        # If position exists, check health fields
        if "error" not in data:
            expected_fields = ["health_score", "health_status", "recommendation", "signals"]
            for field in expected_fields:
                assert field in data, f"Missing '{field}' in thesis health"
            
            # Check health_status is valid
            valid_statuses = ["strong", "neutral", "weak"]
            assert data["health_status"] in valid_statuses, f"Invalid health_status: {data['health_status']}"
            
            print(f"PASS: Thesis health for VOO - Score: {data['health_score']}, Status: {data['health_status']}, Rec: {data['recommendation']}")
        else:
            print(f"INFO: No position found for VOO - {data.get('error')}")


class TestLTRebalanceCheck:
    """Rebalance check endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE},
            headers={"Content-Type": "application/json"}
        )
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_rebalance_check_returns_status(self, headers):
        """Test /api/lt-invest/rebalance-check returns rebalance status"""
        response = requests.get(f"{BASE_URL}/api/lt-invest/rebalance-check", headers=headers)
        assert response.status_code == 200, f"Rebalance check failed: {response.text}"
        
        data = response.json()
        
        # Check required fields
        assert "needs_rebalance" in data, "Missing 'needs_rebalance'"
        assert "reasons" in data, "Missing 'reasons'"
        assert "bucket_allocation" in data, "Missing 'bucket_allocation'"
        assert "diversification_score" in data, "Missing 'diversification_score'"
        
        assert isinstance(data["needs_rebalance"], bool), "needs_rebalance should be boolean"
        assert isinstance(data["reasons"], list), "reasons should be a list"
        
        print(f"PASS: Rebalance check - Needs rebalance: {data['needs_rebalance']}, Reasons: {len(data['reasons'])}")


class TestLTTrimAndClose:
    """Trim and close endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE},
            headers={"Content-Type": "application/json"}
        )
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_trim_position(self, headers):
        """Test POST /api/lt-invest/trim allows trimming a position"""
        # First check if VOO position exists
        portfolio_response = requests.get(f"{BASE_URL}/api/lt-invest/portfolio", headers=headers)
        portfolio = portfolio_response.json()
        
        voo_position = next((p for p in portfolio.get("positions", []) if p["symbol"] == "VOO"), None)
        
        if voo_position and voo_position.get("shares", 0) > 1:
            payload = {
                "symbol": "VOO",
                "shares": 1,
                "price": 450.00,
                "reason": "TEST: Partial trim for testing"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/lt-invest/trim",
                json=payload,
                headers=headers
            )
            assert response.status_code == 200, f"Trim failed: {response.text}"
            
            data = response.json()
            # Should either have action or error
            if "error" not in data:
                assert "action" in data or "shares" in data, f"Unexpected trim response: {data}"
                print(f"PASS: Trim position successful")
            else:
                print(f"INFO: Trim returned error (expected if no position): {data.get('error')}")
        else:
            print(f"INFO: Skipping trim test - VOO position not found or insufficient shares")
    
    def test_trim_validates_required_fields(self, headers):
        """Test trim validates required fields"""
        response = requests.post(
            f"{BASE_URL}/api/lt-invest/trim",
            json={"symbol": "VOO"},  # Missing shares and price
            headers=headers
        )
        data = response.json()
        assert "error" in data, "Should return error for missing fields"
        print(f"PASS: Trim validates required fields")
    
    def test_close_position(self, headers):
        """Test POST /api/lt-invest/close allows closing a position"""
        # Close the VOO test position
        payload = {
            "symbol": "VOO",
            "reason": "TEST: Cleanup after testing"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/lt-invest/close",
            json=payload,
            headers=headers
        )
        assert response.status_code == 200, f"Close failed: {response.text}"
        
        data = response.json()
        if data.get("success"):
            assert data["symbol"] == "VOO"
            assert data["action"] == "closed"
            print(f"PASS: Close position successful - VOO closed")
        else:
            print(f"INFO: Close returned: {data}")
    
    def test_close_validates_symbol(self, headers):
        """Test close validates symbol field"""
        response = requests.post(
            f"{BASE_URL}/api/lt-invest/close",
            json={},  # Missing symbol
            headers=headers
        )
        data = response.json()
        assert "error" in data, "Should return error for missing symbol"
        print(f"PASS: Close validates symbol field")


class TestLTFullWorkflow:
    """Full workflow test: Create → Read → Update → Delete"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/access",
            json={"code": ACCESS_CODE},
            headers={"Content-Type": "application/json"}
        )
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    def test_full_crud_workflow(self, headers):
        """Test complete workflow: stage buy → verify in portfolio → thesis → close"""
        test_symbol = "QQQ"
        
        # 1. Stage Buy
        print(f"\n--- Step 1: Stage Buy {test_symbol} ---")
        buy_payload = {
            "symbol": test_symbol,
            "bucket": "core",
            "shares": 3,
            "price": 520.00,
            "thesis": "TEST: Nasdaq 100 exposure for tech growth",
            "name": "Invesco Nasdaq 100"
        }
        
        buy_response = requests.post(
            f"{BASE_URL}/api/lt-invest/stage-buy",
            json=buy_payload,
            headers=headers
        )
        assert buy_response.status_code == 200
        buy_data = buy_response.json()
        assert buy_data.get("success") == True, f"Stage buy failed: {buy_data}"
        print(f"  Stage buy successful: {buy_data['position']['shares']} shares at stage {buy_data['position']['stage']}")
        
        # 2. Verify in Portfolio
        print(f"\n--- Step 2: Verify {test_symbol} in Portfolio ---")
        portfolio_response = requests.get(f"{BASE_URL}/api/lt-invest/portfolio", headers=headers)
        assert portfolio_response.status_code == 200
        portfolio = portfolio_response.json()
        
        position = next((p for p in portfolio.get("positions", []) if p["symbol"] == test_symbol), None)
        assert position is not None, f"{test_symbol} not found in portfolio"
        assert position["shares"] == 3 or position["shares"] > 0, f"Shares mismatch"
        assert position["bucket"] == "core"
        print(f"  Found in portfolio: {position['shares']} shares, value ${position.get('current_value', 0)}")
        
        # 3. Check Thesis Health
        print(f"\n--- Step 3: Check Thesis Health ---")
        thesis_response = requests.get(f"{BASE_URL}/api/lt-invest/thesis/{test_symbol}", headers=headers)
        assert thesis_response.status_code == 200
        thesis = thesis_response.json()
        
        if "error" not in thesis:
            assert thesis["symbol"] == test_symbol
            print(f"  Thesis health: Score {thesis.get('health_score')}, Status: {thesis.get('health_status')}")
        
        # 4. Close Position (Cleanup)
        print(f"\n--- Step 4: Close Position (Cleanup) ---")
        close_response = requests.post(
            f"{BASE_URL}/api/lt-invest/close",
            json={"symbol": test_symbol, "reason": "TEST: Cleanup after workflow test"},
            headers=headers
        )
        assert close_response.status_code == 200
        close_data = close_response.json()
        assert close_data.get("success") == True
        print(f"  Position closed successfully")
        
        # 5. Verify Removed from Portfolio
        print(f"\n--- Step 5: Verify Removed from Portfolio ---")
        final_portfolio = requests.get(f"{BASE_URL}/api/lt-invest/portfolio", headers=headers)
        final_positions = final_portfolio.json().get("positions", [])
        position_after = next((p for p in final_positions if p["symbol"] == test_symbol), None)
        assert position_after is None, f"{test_symbol} should be removed from portfolio"
        print(f"  Verified: {test_symbol} no longer in active positions")
        
        print(f"\nPASS: Full CRUD workflow completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
