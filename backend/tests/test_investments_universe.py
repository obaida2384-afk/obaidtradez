"""
Test suite for ObaidTradez Investment Universe Enhancement
Tests: /api/investments/browse, /api/investments/filters, /api/investments/refresh
Features: Pagination, filtering, broad market coverage (350+ stocks)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ACCESS_CODE = "Bullishalmarkhan7.7"


class TestInvestmentUniverse:
    """Tests for the expanded investment universe with 350+ stocks"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200, f"Auth failed: {response.text}"
        data = response.json()
        assert data.get("success"), "Auth not successful"
        self.token = data.get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    # ============ /api/investments/filters Tests ============
    
    def test_filters_endpoint_returns_sectors(self):
        """Test that filters endpoint returns available sectors"""
        response = requests.get(f"{BASE_URL}/api/investments/filters", headers=self.headers)
        assert response.status_code == 200, f"Filters endpoint failed: {response.text}"
        
        data = response.json()
        assert "sectors" in data, "Missing sectors in response"
        assert isinstance(data["sectors"], list), "Sectors should be a list"
        print(f"Available sectors: {len(data['sectors'])} - {data['sectors'][:5]}...")
    
    def test_filters_endpoint_returns_signal_counts(self):
        """Test that filters endpoint returns signal counts"""
        response = requests.get(f"{BASE_URL}/api/investments/filters", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "signals" in data, "Missing signals in response"
        assert isinstance(data["signals"], dict), "Signals should be a dict"
        print(f"Signal counts: {data['signals']}")
    
    def test_filters_endpoint_returns_category_counts(self):
        """Test that filters endpoint returns category counts"""
        response = requests.get(f"{BASE_URL}/api/investments/filters", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "categories" in data, "Missing categories in response"
        assert isinstance(data["categories"], dict), "Categories should be a dict"
        print(f"Category counts: {data['categories']}")
    
    def test_filters_endpoint_returns_total_signals(self):
        """Test that filters endpoint returns total signal count"""
        response = requests.get(f"{BASE_URL}/api/investments/filters", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_signals" in data, "Missing total_signals in response"
        assert isinstance(data["total_signals"], int), "total_signals should be int"
        print(f"Total signals in database: {data['total_signals']}")
    
    def test_filters_endpoint_returns_market_cap_ranges(self):
        """Test that filters endpoint returns market cap ranges"""
        response = requests.get(f"{BASE_URL}/api/investments/filters", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "market_cap_ranges" in data, "Missing market_cap_ranges in response"
        assert isinstance(data["market_cap_ranges"], list), "market_cap_ranges should be a list"
        assert len(data["market_cap_ranges"]) >= 4, "Should have at least 4 market cap ranges"
        print(f"Market cap ranges: {[r['label'] for r in data['market_cap_ranges']]}")
    
    # ============ /api/investments/browse Tests ============
    
    def test_browse_endpoint_returns_paginated_results(self):
        """Test that browse endpoint returns paginated results"""
        response = requests.get(
            f"{BASE_URL}/api/investments/browse",
            params={"page": 1, "page_size": 30},
            headers=self.headers
        )
        assert response.status_code == 200, f"Browse endpoint failed: {response.text}"
        
        data = response.json()
        assert "signals" in data, "Missing signals in response"
        assert "total" in data, "Missing total in response"
        assert "page" in data, "Missing page in response"
        assert "page_size" in data, "Missing page_size in response"
        assert "total_pages" in data, "Missing total_pages in response"
        
        print(f"Browse results: {len(data['signals'])} signals, total: {data['total']}, pages: {data['total_pages']}")
    
    def test_browse_endpoint_pagination_works(self):
        """Test that pagination returns different results on different pages"""
        page1 = requests.get(
            f"{BASE_URL}/api/investments/browse",
            params={"page": 1, "page_size": 10},
            headers=self.headers
        ).json()
        
        page2 = requests.get(
            f"{BASE_URL}/api/investments/browse",
            params={"page": 2, "page_size": 10},
            headers=self.headers
        ).json()
        
        if page1["total_pages"] > 1:
            # Different pages should have different stocks
            page1_symbols = [s["symbol"] for s in page1["signals"]]
            page2_symbols = [s["symbol"] for s in page2["signals"]]
            assert page1_symbols != page2_symbols, "Page 1 and 2 should have different stocks"
            print(f"Page 1 symbols: {page1_symbols[:5]}")
            print(f"Page 2 symbols: {page2_symbols[:5]}")
        else:
            print("Only 1 page of results, skipping pagination comparison")
    
    def test_browse_endpoint_filter_by_sector(self):
        """Test filtering by sector"""
        # First get available sectors
        filters = requests.get(f"{BASE_URL}/api/investments/filters", headers=self.headers).json()
        
        if filters.get("sectors"):
            sector = filters["sectors"][0]
            response = requests.get(
                f"{BASE_URL}/api/investments/browse",
                params={"sectors": sector, "page_size": 50},
                headers=self.headers
            )
            assert response.status_code == 200
            
            data = response.json()
            # All returned stocks should be in the specified sector
            for signal in data["signals"]:
                assert signal.get("sector") == sector, f"Stock {signal['symbol']} has sector {signal.get('sector')}, expected {sector}"
            print(f"Filtered by sector '{sector}': {len(data['signals'])} stocks")
        else:
            pytest.skip("No sectors available for filtering")
    
    def test_browse_endpoint_filter_by_signal(self):
        """Test filtering by signal type"""
        response = requests.get(
            f"{BASE_URL}/api/investments/browse",
            params={"signals": "Buy", "page_size": 50},
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        for signal in data["signals"]:
            assert signal.get("signal") == "Buy", f"Stock {signal['symbol']} has signal {signal.get('signal')}, expected Buy"
        print(f"Filtered by signal 'Buy': {len(data['signals'])} stocks")
    
    def test_browse_endpoint_filter_by_min_score(self):
        """Test filtering by minimum overall score"""
        min_score = 60
        response = requests.get(
            f"{BASE_URL}/api/investments/browse",
            params={"min_score": min_score, "page_size": 50},
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        for signal in data["signals"]:
            assert signal.get("overall_score", 0) >= min_score, f"Stock {signal['symbol']} has score {signal.get('overall_score')}, expected >= {min_score}"
        print(f"Filtered by min_score {min_score}: {len(data['signals'])} stocks")
    
    def test_browse_endpoint_filter_by_market_cap(self):
        """Test filtering by market cap range"""
        # Large cap: $10B - $200B
        response = requests.get(
            f"{BASE_URL}/api/investments/browse",
            params={"min_market_cap": 10e9, "max_market_cap": 200e9, "page_size": 50},
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        for signal in data["signals"]:
            mc = signal.get("market_cap")
            if mc:  # Some stocks may have missing market cap
                assert 10e9 <= mc <= 200e9, f"Stock {signal['symbol']} has market cap {mc}, expected between 10B and 200B"
        print(f"Filtered by large cap: {len(data['signals'])} stocks")
    
    def test_browse_endpoint_sorting(self):
        """Test sorting by different fields"""
        # Sort by overall_score descending
        response = requests.get(
            f"{BASE_URL}/api/investments/browse",
            params={"sort_by": "overall_score", "sort_dir": "desc", "page_size": 10},
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        scores = [s.get("overall_score", 0) for s in data["signals"]]
        assert scores == sorted(scores, reverse=True), "Results should be sorted by score descending"
        print(f"Top scores: {scores[:5]}")
    
    def test_browse_endpoint_returns_stock_details(self):
        """Test that browse returns complete stock details"""
        response = requests.get(
            f"{BASE_URL}/api/investments/browse",
            params={"page_size": 10},  # Minimum page_size is 10
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        if data["signals"]:
            signal = data["signals"][0]
            # Check required fields
            required_fields = ["symbol", "name", "signal", "overall_score", "category"]
            for field in required_fields:
                assert field in signal, f"Missing required field: {field}"
            
            # Check extended fields for universe
            extended_fields = ["sector", "market_cap", "market_cap_label", "data_completeness"]
            for field in extended_fields:
                assert field in signal, f"Missing extended field: {field}"
            
            print(f"Sample stock: {signal['symbol']} - {signal['name']}")
            print(f"  Sector: {signal.get('sector')}, Market Cap: {signal.get('market_cap_label')}")
            print(f"  Score: {signal.get('overall_score')}, Signal: {signal.get('signal')}")
            print(f"  Data Completeness: {signal.get('data_completeness')}%")
    
    # ============ /api/investments/refresh Tests ============
    
    def test_refresh_endpoint_triggers_background_scan(self):
        """Test that refresh endpoint triggers background scanning"""
        response = requests.post(
            f"{BASE_URL}/api/investments/refresh",
            params={"limit": 50},  # Small limit for testing
            headers=self.headers
        )
        assert response.status_code == 200, f"Refresh endpoint failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Missing message in response"
        assert "status" in data, "Missing status in response"
        assert data["status"] == "processing", "Status should be 'processing'"
        print(f"Refresh response: {data}")
    
    # ============ /api/investments/scan Tests ============
    
    def test_scan_endpoint_returns_categorized_signals(self):
        """Test that scan endpoint returns signals in categories"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=self.headers)
        assert response.status_code == 200, f"Scan endpoint failed: {response.text}"
        
        data = response.json()
        expected_categories = ["hot", "bullish", "undervalued", "watch", "bearish"]
        for cat in expected_categories:
            assert cat in data, f"Missing category: {cat}"
            assert isinstance(data[cat], list), f"Category {cat} should be a list"
        
        print(f"Scan results:")
        for cat in expected_categories:
            print(f"  {cat}: {len(data[cat])} stocks")
    
    def test_scan_endpoint_returns_total_analyzed(self):
        """Test that scan endpoint returns total analyzed count"""
        response = requests.get(f"{BASE_URL}/api/investments/scan", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_analyzed" in data, "Missing total_analyzed in response"
        print(f"Total stocks analyzed: {data['total_analyzed']}")
    
    # ============ /api/investments/analyze/{symbol} Tests ============
    
    def test_analyze_single_stock(self):
        """Test analyzing a single stock"""
        response = requests.get(f"{BASE_URL}/api/investments/analyze/AAPL", headers=self.headers)
        assert response.status_code == 200, f"Analyze endpoint failed: {response.text}"
        
        data = response.json()
        assert data["symbol"] == "AAPL", "Symbol should be AAPL"
        assert "overall_score" in data, "Missing overall_score"
        assert "valuation_score" in data, "Missing valuation_score"
        assert "quality_score" in data, "Missing quality_score"
        assert "growth_score" in data, "Missing growth_score"
        assert "financial_strength" in data, "Missing financial_strength"
        assert "risk_score" in data, "Missing risk_score"
        assert "bull_case" in data, "Missing bull_case"
        assert "bear_case" in data, "Missing bear_case"
        assert "sector" in data, "Missing sector"
        assert "market_cap_label" in data, "Missing market_cap_label"
        
        print(f"AAPL Analysis:")
        print(f"  Overall Score: {data['overall_score']}")
        print(f"  Signal: {data['signal']}, Category: {data['category']}")
        print(f"  Sector: {data['sector']}, Market Cap: {data['market_cap_label']}")
    
    def test_analyze_invalid_symbol(self):
        """Test analyzing an invalid symbol returns 404"""
        response = requests.get(f"{BASE_URL}/api/investments/analyze/INVALIDXYZ123", headers=self.headers)
        assert response.status_code == 404, f"Expected 404 for invalid symbol, got {response.status_code}"
    
    # ============ Authentication Tests ============
    
    def test_browse_requires_auth(self):
        """Test that browse endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/investments/browse")
        assert response.status_code == 401, "Browse should require auth"
    
    def test_filters_requires_auth(self):
        """Test that filters endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/investments/filters")
        assert response.status_code == 401, "Filters should require auth"
    
    def test_refresh_requires_auth(self):
        """Test that refresh endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/investments/refresh")
        assert response.status_code == 401, "Refresh should require auth"


class TestUniverseStats:
    """Tests for universe statistics endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/access", json={"code": ACCESS_CODE})
        assert response.status_code == 200
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_universe_stats_endpoint(self):
        """Test universe stats endpoint returns statistics"""
        response = requests.get(f"{BASE_URL}/api/universe/stats", headers=self.headers)
        assert response.status_code == 200, f"Universe stats failed: {response.text}"
        
        data = response.json()
        assert "count" in data, "Missing count in response"
        print(f"Universe stats: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
