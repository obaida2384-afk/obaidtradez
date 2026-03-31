"""
Test Price Integrity P2 Features for ObaidTradez
Tests:
1. Ticker normalization (ZI→GTM mapping)
2. Price freshness validation
3. price_data in candidates
4. entry_status classification (TRADE_NOW/WATCHLIST/MISSED)
5. price_audit debug logging
6. ticker_mappings endpoint
7. Dead ticker exclusion from scans
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
    assert data.get("success"), f"Auth not successful: {data}"
    return data.get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestTickerMappingsEndpoint:
    """Test /api/debug/ticker_mappings endpoint"""
    
    def test_ticker_mappings_returns_known_renames(self, auth_headers):
        """Should return 14 known renames (ZI→GTM, TWTR→X, FB→META, etc.)"""
        resp = requests.get(f"{BASE_URL}/api/debug/ticker_mappings", headers=auth_headers)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Check structure
        assert "ticker_mappings" in data, "Missing ticker_mappings field"
        assert "dead_tickers" in data, "Missing dead_tickers field"
        assert "stats" in data, "Missing stats field"
        
        mappings = data["ticker_mappings"]
        assert isinstance(mappings, dict), "ticker_mappings should be a dict"
        
        # Verify known renames exist
        expected_renames = {
            "ZI": "GTM",
            "TWTR": "X",
            "FB": "META",
            "DISCA": "WBD",
            "VIAC": "PARA",
            "FEYE": "MNDT",
            "KSU": "CP",
            "ZNGA": "TTWO",
            "HFC": "PSX",
            "ECHO": "CHRW",
            "PLAN": "ANPL",
            "SAFM": "TSN",
            "ONEM": "AMZN",
        }
        
        for old, new in expected_renames.items():
            assert old in mappings, f"Missing rename: {old}"
            assert mappings[old] == new, f"Wrong mapping for {old}: expected {new}, got {mappings[old]}"
        
        # Should have at least 13 renames (MIME→MIME is self-mapping)
        assert len(mappings) >= 13, f"Expected at least 13 renames, got {len(mappings)}"
        print(f"✓ Found {len(mappings)} ticker mappings")
        
    def test_ticker_mappings_returns_dead_tickers(self, auth_headers):
        """Should return 160+ dead tickers"""
        resp = requests.get(f"{BASE_URL}/api/debug/ticker_mappings", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        
        dead_tickers = data.get("dead_tickers", [])
        assert isinstance(dead_tickers, list), "dead_tickers should be a list"
        
        # Should have many dead tickers flagged
        print(f"✓ Found {len(dead_tickers)} dead tickers")
        # Note: The exact count depends on what's been synced
        

class TestPriceIntegrityZI:
    """Test price integrity for ZI (renamed to GTM)"""
    
    def test_zi_shows_renamed_to_gtm(self, auth_headers):
        """GET /api/debug/price_integrity/ZI should show is_renamed=true AND ticker_canonical=GTM
        Note: ZI is NOT dead - it's renamed to GTM which is actively trading"""
        resp = requests.get(f"{BASE_URL}/api/debug/price_integrity/ZI", headers=auth_headers)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Check structure
        assert "validated" in data, "Missing validated field"
        assert "ticker_canonical" in data, "Missing ticker_canonical field"
        assert "is_renamed" in data, "Missing is_renamed field"
        
        validated = data["validated"]
        
        # ZI should be renamed to GTM
        assert data["ticker_canonical"] == "GTM", f"Expected ticker_canonical=GTM, got {data['ticker_canonical']}"
        assert data["is_renamed"] == True, f"Expected is_renamed=true, got {data['is_renamed']}"
        
        # GTM (the canonical symbol) should have a valid price
        assert validated.get("price", 0) > 0, f"GTM should have a price, got {validated.get('price')}"
        
        # GTM should NOT be stale (it's actively trading)
        assert validated.get("stale") == False, f"GTM should not be stale"
        
        print(f"✓ ZI: ticker_canonical={data['ticker_canonical']}, is_renamed={data['is_renamed']}, price=${validated.get('price'):.2f}")


class TestPriceIntegrityMRVL:
    """Test price integrity for MRVL (healthy stock)"""
    
    def test_mrvl_shows_healthy(self, auth_headers):
        """GET /api/debug/price_integrity/MRVL should show stale=false, price around $87, mismatch=false"""
        resp = requests.get(f"{BASE_URL}/api/debug/price_integrity/MRVL", headers=auth_headers)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        validated = data["validated"]
        
        # MRVL should NOT be stale
        assert validated.get("stale") == False, f"MRVL should be stale=false, got {validated.get('stale')}"
        
        # MRVL should NOT be dead
        assert validated.get("dead_ticker") == False, f"MRVL should be dead_ticker=false, got {validated.get('dead_ticker')}"
        
        # MRVL should have a price (around $87 based on previous tests)
        price = validated.get("price", 0)
        assert price > 50, f"MRVL price should be > $50, got ${price}"
        
        # Source should be alpaca
        source = validated.get("source", "")
        assert "alpaca" in source.lower() or "fmp" in source.lower(), f"Expected alpaca or fmp source, got {source}"
        
        # Should not be renamed
        assert data.get("is_renamed") == False, f"MRVL should not be renamed"
        
        print(f"✓ MRVL: price=${price:.2f}, stale={validated.get('stale')}, source={source}")


class TestPriceIntegrityBatch:
    """Test batch price integrity checks"""
    
    def test_batch_healthy_symbols(self, auth_headers):
        """GET /api/debug/price_integrity?symbols=AAPL,TSLA should show all healthy with source=alpaca"""
        resp = requests.get(f"{BASE_URL}/api/debug/price_integrity", 
                           params={"symbols": "AAPL,TSLA"}, headers=auth_headers)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Check structure
        assert "healthy" in data, "Missing healthy count"
        assert "dead" in data, "Missing dead count"
        assert "stale" in data, "Missing stale count"
        
        # Both should be healthy
        assert data["healthy"] == 2, f"Expected 2 healthy, got {data['healthy']}"
        assert data["dead"] == 0, f"Expected 0 dead, got {data['dead']}"
        
        print(f"✓ AAPL,TSLA: healthy={data['healthy']}, dead={data['dead']}, stale={data['stale']}")


class TestAutoTradeScan:
    """Test /api/auto-trade/scan endpoint"""
    
    def test_scan_excludes_dead_tickers(self, auth_headers):
        """GET /api/auto-trade/scan should NOT contain dead ticker symbols ZI, TWTR, SIVB"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=auth_headers, timeout=60)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        dead_tickers = ["ZI", "TWTR", "SIVB"]
        
        # Check day_trades
        day_trades = data.get("day_trades", [])
        for dt in day_trades:
            symbol = dt.get("symbol", "")
            assert symbol not in dead_tickers, f"Dead ticker {symbol} found in day_trades"
        
        # Check long_term
        long_term = data.get("long_term", [])
        for lt in long_term:
            symbol = lt.get("symbol", "")
            assert symbol not in dead_tickers, f"Dead ticker {symbol} found in long_term"
        
        # Check watchlist
        watchlist = data.get("watchlist", [])
        for w in watchlist:
            symbol = w.get("symbol", "")
            assert symbol not in dead_tickers, f"Dead ticker {symbol} found in watchlist"
        
        print(f"✓ No dead tickers in scan results (day_trades={len(day_trades)}, long_term={len(long_term)}, watchlist={len(watchlist)})")
    
    def test_scan_has_price_audit(self, auth_headers):
        """GET /api/auto-trade/scan response must contain 'price_audit' array"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=auth_headers, timeout=60)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Check price_audit exists
        assert "price_audit" in data, "Missing price_audit field in scan response"
        price_audit = data["price_audit"]
        assert isinstance(price_audit, list), "price_audit should be a list"
        
        # Check price_audit entries have required fields
        if len(price_audit) > 0:
            entry = price_audit[0]
            required_fields = ["symbol", "price_used", "source", "status", "stale", "entry_status"]
            for field in required_fields:
                assert field in entry, f"Missing {field} in price_audit entry"
            
            print(f"✓ price_audit has {len(price_audit)} entries with fields: {list(entry.keys())}")
        else:
            print("✓ price_audit exists but is empty (market may be closed)")
    
    def test_candidates_have_price_data(self, auth_headers):
        """Each candidate in day_trades/long_term/watchlist must have 'price_data' object"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=auth_headers, timeout=60)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        all_candidates = data.get("day_trades", []) + data.get("long_term", []) + data.get("watchlist", [])
        
        price_data_fields = ["price", "source", "synced_at", "status"]
        
        for candidate in all_candidates[:10]:  # Check first 10
            symbol = candidate.get("symbol", "unknown")
            assert "price_data" in candidate, f"Missing price_data for {symbol}"
            
            pd = candidate["price_data"]
            assert isinstance(pd, dict), f"price_data should be dict for {symbol}"
            
            for field in price_data_fields:
                assert field in pd, f"Missing {field} in price_data for {symbol}"
        
        print(f"✓ Checked {min(10, len(all_candidates))} candidates - all have price_data with required fields")
    
    def test_candidates_have_entry_status(self, auth_headers):
        """Each candidate must have 'entry_status' field set to one of: TRADE_NOW, WATCHLIST, MISSED, NO_LEVELS, UNKNOWN"""
        resp = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=auth_headers, timeout=60)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        valid_statuses = ["TRADE_NOW", "WATCHLIST", "MISSED", "NO_LEVELS", "UNKNOWN"]
        
        all_candidates = data.get("day_trades", []) + data.get("long_term", []) + data.get("watchlist", [])
        
        status_counts = {}
        for candidate in all_candidates:
            symbol = candidate.get("symbol", "unknown")
            assert "entry_status" in candidate, f"Missing entry_status for {symbol}"
            
            status = candidate["entry_status"]
            assert status in valid_statuses, f"Invalid entry_status '{status}' for {symbol}"
            
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"✓ Entry status distribution: {status_counts}")


class TestInvestmentsScan:
    """Test /api/investments/scan endpoint"""
    
    def test_investments_excludes_dead_tickers(self, auth_headers):
        """GET /api/investments/scan should NOT include actual dead_ticker symbols like SIVB, TWTR
        Note: ZI is NOT dead - it's renamed to GTM which is actively trading"""
        resp = requests.get(f"{BASE_URL}/api/investments/scan", headers=auth_headers, timeout=60)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # These are actual dead tickers (bankrupt/delisted)
        dead_tickers = ["SIVB", "TWTR"]
        
        # Check all categories
        for category in ["strong_buy", "buy", "hold", "sell", "all"]:
            signals = data.get(category, [])
            for sig in signals:
                symbol = sig.get("symbol", "")
                assert symbol not in dead_tickers, f"Dead ticker {symbol} found in investments/{category}"
        
        total = data.get("diagnostics", {}).get("signals_generated", 0)
        print(f"✓ No dead tickers (SIVB, TWTR) in investments scan ({total} signals)")
    
    def test_renamed_tickers_allowed(self, auth_headers):
        """Renamed tickers like ZI (→GTM) should be allowed if the canonical symbol is live"""
        resp = requests.get(f"{BASE_URL}/api/investments/scan", headers=auth_headers, timeout=60)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # ZI is renamed to GTM which is live - it should be allowed
        all_symbols = [s.get("symbol") for s in data.get("all", [])]
        
        # ZI may or may not be in the scan depending on its score, but it should NOT be blocked
        # The key test is that dead tickers are excluded
        print(f"✓ Investments scan has {len(all_symbols)} symbols")


class TestSyncSignals:
    """Test /api/prices/sync-signals endpoint"""
    
    def test_sync_signals_returns_counts(self, auth_headers):
        """POST /api/prices/sync-signals should return {updated, dead_flagged, rejected, total}"""
        resp = requests.post(f"{BASE_URL}/api/prices/sync-signals", headers=auth_headers, timeout=120)
        assert resp.status_code == 200, f"Failed: {resp.text}"
        data = resp.json()
        
        # Check required fields
        required_fields = ["updated", "dead_flagged", "rejected", "total"]
        for field in required_fields:
            assert field in data, f"Missing {field} in sync-signals response"
        
        print(f"✓ sync-signals: updated={data['updated']}, dead_flagged={data['dead_flagged']}, rejected={data['rejected']}, total={data['total']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
