"""
Test Top Movers Scanner Feature
Tests:
- GET /api/top-movers/scan - Returns accepted symbols with source tags and pipeline stats
- GET /api/top-movers/status - Returns has_data, accepted_count, config
- GET /api/top-movers/performance - Returns daily performance summary
- GET /api/auto-trade/scan - Returns top_movers block with injected/in_prefilter/as_candidates counts
- Verify rejection reasons are grouped (e.g., 'Price > $50.0' not individual prices)
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


class TestTopMoversEndpoints:
    """Test Top Movers Scanner API endpoints"""

    def test_top_movers_scan_endpoint(self, headers):
        """GET /api/top-movers/scan returns accepted symbols with source tags and pipeline stats"""
        resp = requests.get(f"{BASE_URL}/api/top-movers/scan", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        
        # Verify structure
        assert "accepted" in data, "Response should have 'accepted' field"
        assert "accepted_symbols" in data, "Response should have 'accepted_symbols' field"
        assert "pipeline" in data, "Response should have 'pipeline' field"
        assert "config" in data, "Response should have 'config' field"
        assert "rejected" in data, "Response should have 'rejected' field"
        
        # Verify pipeline stats
        pipeline = data["pipeline"]
        assert "raw_gainers" in pipeline, "Pipeline should have raw_gainers"
        assert "raw_losers" in pipeline, "Pipeline should have raw_losers"
        assert "raw_actives" in pipeline, "Pipeline should have raw_actives"
        assert "filtered_gainers" in pipeline, "Pipeline should have filtered_gainers"
        assert "filtered_losers" in pipeline, "Pipeline should have filtered_losers"
        assert "filtered_actives" in pipeline, "Pipeline should have filtered_actives"
        assert "total_accepted" in pipeline, "Pipeline should have total_accepted"
        assert "total_rejected" in pipeline, "Pipeline should have total_rejected"
        assert "rejections_by_reason" in pipeline, "Pipeline should have rejections_by_reason"
        
        # Verify config
        config = data["config"]
        assert "max_gainers" in config, "Config should have max_gainers"
        assert "max_losers" in config, "Config should have max_losers"
        assert "max_actives" in config, "Config should have max_actives"
        assert "price_range" in config, "Config should have price_range"
        assert "min_volume" in config, "Config should have min_volume"
        assert "min_market_cap" in config, "Config should have min_market_cap"
        
        # Verify accepted items have source tags
        for item in data["accepted"]:
            assert "symbol" in item, "Accepted item should have symbol"
            assert "source" in item, "Accepted item should have source tag"
            assert item["source"] in ["top_gainer", "top_loser", "most_active"], \
                f"Source should be one of top_gainer/top_loser/most_active, got {item['source']}"
        
        print(f"Top Movers Scan: {pipeline['total_accepted']} accepted, {pipeline['total_rejected']} rejected")
        print(f"  Gainers: {pipeline['filtered_gainers']}, Losers: {pipeline['filtered_losers']}, Actives: {pipeline['filtered_actives']}")

    def test_top_movers_status_endpoint(self, headers):
        """GET /api/top-movers/status returns has_data, accepted_count, config"""
        resp = requests.get(f"{BASE_URL}/api/top-movers/status", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        
        # Verify required fields
        assert "has_data" in data, "Response should have 'has_data' field"
        assert "accepted_count" in data, "Response should have 'accepted_count' field"
        assert "config" in data, "Response should have 'config' field"
        assert "needs_refresh" in data, "Response should have 'needs_refresh' field"
        assert "accepted_symbols" in data, "Response should have 'accepted_symbols' field"
        
        # Verify config structure
        config = data["config"]
        assert "max_gainers" in config, "Config should have max_gainers"
        assert "max_losers" in config, "Config should have max_losers"
        assert "max_actives" in config, "Config should have max_actives"
        assert "refresh_interval_minutes" in config, "Config should have refresh_interval_minutes"
        assert "price_range" in config, "Config should have price_range"
        assert "min_volume" in config, "Config should have min_volume"
        assert "min_market_cap" in config, "Config should have min_market_cap"
        
        # Verify data types
        assert isinstance(data["has_data"], bool), "has_data should be boolean"
        assert isinstance(data["accepted_count"], int), "accepted_count should be integer"
        assert isinstance(data["accepted_symbols"], list), "accepted_symbols should be list"
        
        print(f"Top Movers Status: has_data={data['has_data']}, accepted_count={data['accepted_count']}")
        print(f"  Config: {config}")

    def test_top_movers_performance_endpoint(self, headers):
        """GET /api/top-movers/performance returns daily performance summary"""
        resp = requests.get(f"{BASE_URL}/api/top-movers/performance", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        
        # Verify required fields
        assert "date" in data, "Response should have 'date' field"
        assert "total_scans" in data, "Response should have 'total_scans' field"
        
        # If there are scans, verify additional fields
        if data["total_scans"] > 0:
            assert "unique_accepted_symbols" in data, "Response should have 'unique_accepted_symbols'"
            assert "accepted_symbols_list" in data, "Response should have 'accepted_symbols_list'"
            assert "unique_rejected_symbols" in data, "Response should have 'unique_rejected_symbols'"
            assert "top_rejection_reasons" in data, "Response should have 'top_rejection_reasons'"
            assert "last_scan" in data, "Response should have 'last_scan'"
        
        print(f"Top Movers Performance: date={data['date']}, total_scans={data['total_scans']}")

    def test_rejection_reasons_grouped(self, headers):
        """Verify rejection reasons are grouped (e.g., 'Price > $50.0' not individual prices)"""
        resp = requests.get(f"{BASE_URL}/api/top-movers/scan", headers=headers)
        assert resp.status_code == 200
        
        data = resp.json()
        rejections_by_reason = data["pipeline"].get("rejections_by_reason", {})
        
        # Check that rejection reasons are grouped, not individual values
        for reason in rejections_by_reason.keys():
            # Should NOT contain specific prices like "Price $123.45 > $50.0"
            # Should be grouped like "Price > $50.0" or "Volume too low"
            assert not any(char.isdigit() and '.' in reason and reason.count('.') > 1 for char in reason), \
                f"Rejection reason should be grouped, not individual: {reason}"
        
        # Verify expected grouped reasons exist if there are rejections
        if rejections_by_reason:
            expected_patterns = ["Price", "Volume", "Change", "Market cap", "Excluded", "Non-common"]
            found_patterns = [p for p in expected_patterns if any(p in r for r in rejections_by_reason.keys())]
            print(f"Grouped rejection reasons found: {list(rejections_by_reason.keys())}")
            print(f"Matched patterns: {found_patterns}")


class TestAutoTradeScanTopMovers:
    """Test Top Movers integration in auto-trade scan"""

    def test_auto_trade_scan_includes_top_movers_block(self, headers):
        """GET /api/auto-trade/scan returns top_movers block with injected/in_prefilter/as_candidates counts"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        
        # Verify top_movers block exists
        assert "top_movers" in data, "Response should have 'top_movers' block"
        
        top_movers = data["top_movers"]
        
        # Verify required fields in top_movers block
        assert "injected" in top_movers, "top_movers should have 'injected' count"
        assert "in_prefilter" in top_movers, "top_movers should have 'in_prefilter' count"
        assert "as_candidates" in top_movers, "top_movers should have 'as_candidates' count"
        assert "as_watchlist" in top_movers, "top_movers should have 'as_watchlist' count"
        
        # Verify data types
        assert isinstance(top_movers["injected"], int), "injected should be integer"
        assert isinstance(top_movers["in_prefilter"], int), "in_prefilter should be integer"
        assert isinstance(top_movers["as_candidates"], int), "as_candidates should be integer"
        assert isinstance(top_movers["as_watchlist"], int), "as_watchlist should be integer"
        
        print(f"Top Movers in Auto-Trade Scan:")
        print(f"  Injected: {top_movers['injected']}")
        print(f"  In Prefilter: {top_movers['in_prefilter']}")
        print(f"  As Candidates: {top_movers['as_candidates']}")
        print(f"  As Watchlist: {top_movers['as_watchlist']}")

    def test_auto_trade_scan_stats_include_top_movers_fields(self, headers):
        """Verify scan stats include top_movers_injected and top_movers_in_prefilter fields"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers)
        assert resp.status_code == 200
        
        data = resp.json()
        
        # Verify stats block exists
        assert "stats" in data, "Response should have 'stats' block"
        
        stats = data["stats"]
        
        # Verify top movers fields in stats
        assert "top_movers_injected" in stats, "stats should have 'top_movers_injected'"
        assert "top_movers_in_prefilter" in stats, "stats should have 'top_movers_in_prefilter'"
        
        print(f"Stats: top_movers_injected={stats['top_movers_injected']}, top_movers_in_prefilter={stats['top_movers_in_prefilter']}")

    def test_candidates_have_source_tags(self, headers):
        """Verify day trade candidates have source tags for top movers"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers)
        assert resp.status_code == 200
        
        data = resp.json()
        
        # Check day_trades for source tags
        day_trades = data.get("day_trades", [])
        
        # If there are day trades, check for is_top_mover and source fields
        for trade in day_trades:
            # These fields should exist (may be False/None if not a top mover)
            if trade.get("is_top_mover"):
                assert "source" in trade, f"Top mover candidate {trade.get('symbol')} should have source tag"
                assert trade["source"] in ["top_gainer", "top_loser", "most_active"], \
                    f"Source should be valid, got {trade.get('source')}"
                print(f"  Top Mover Candidate: {trade.get('symbol')} - source: {trade.get('source')}")
        
        print(f"Day trades checked: {len(day_trades)}")


class TestTopMoversQualityFilters:
    """Test quality filters are applied correctly"""

    def test_quality_filters_in_config(self, headers):
        """Verify quality filter values in config"""
        resp = requests.get(f"{BASE_URL}/api/top-movers/status", headers=headers)
        assert resp.status_code == 200
        
        data = resp.json()
        config = data["config"]
        
        # Verify expected filter values
        assert config["price_range"] == "$5.0-$50.0", f"Price range should be $5.0-$50.0, got {config['price_range']}"
        assert config["min_volume"] == "500,000", f"Min volume should be 500,000, got {config['min_volume']}"
        assert config["min_market_cap"] == "$100M", f"Min market cap should be $100M, got {config['min_market_cap']}"
        assert config["max_gainers"] == 30, f"Max gainers should be 30, got {config['max_gainers']}"
        assert config["max_losers"] == 30, f"Max losers should be 30, got {config['max_losers']}"
        assert config["max_actives"] == 20, f"Max actives should be 20, got {config['max_actives']}"
        assert config["refresh_interval_minutes"] == 20, f"Refresh interval should be 20, got {config['refresh_interval_minutes']}"
        
        print("Quality filters verified:")
        print(f"  Price Range: {config['price_range']}")
        print(f"  Min Volume: {config['min_volume']}")
        print(f"  Min Market Cap: {config['min_market_cap']}")
        print(f"  Max Gainers/Losers/Actives: {config['max_gainers']}/{config['max_losers']}/{config['max_actives']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
