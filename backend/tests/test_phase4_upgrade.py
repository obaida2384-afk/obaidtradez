"""
ObaidTradez Phase 4 Upgrade Tests
Tests for: Dynamic thresholds, pipeline funnel, no-trade diagnostics, 
news catalyst scoring, scheduler safety upgrades, and frontend dashboard features.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/access", json={
        "code": "Bullishalmarkhan7.7"
    })
    assert response.status_code == 200, f"Auth failed: {response.text}"
    data = response.json()
    assert data.get("success") == True, f"Auth not successful: {data}"
    return data.get("token")

@pytest.fixture(scope="module")
def headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestAutoTradeScanEndpoint:
    """Test GET /api/auto-trade/scan for new Phase 4 fields"""
    
    def test_scan_returns_dynamic_thresholds(self, headers):
        """Test that scan returns dynamic_thresholds with DT and LT values"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers)
        assert response.status_code == 200, f"Scan failed: {response.text}"
        data = response.json()
        
        # Check dynamic_thresholds exists
        assert "dynamic_thresholds" in data, f"Missing dynamic_thresholds in response: {data.keys()}"
        dt = data["dynamic_thresholds"]
        
        # Check required fields
        assert "dt_threshold" in dt, f"Missing dt_threshold: {dt}"
        assert "lt_threshold" in dt, f"Missing lt_threshold: {dt}"
        
        # Validate threshold values are reasonable (50-100 range)
        assert 50 <= dt["dt_threshold"] <= 100, f"DT threshold out of range: {dt['dt_threshold']}"
        assert 50 <= dt["lt_threshold"] <= 100, f"LT threshold out of range: {dt['lt_threshold']}"
        print(f"✓ Dynamic thresholds: DT={dt['dt_threshold']}, LT={dt['lt_threshold']}")
    
    def test_scan_returns_risk_mode(self, headers):
        """Test that scan returns risk_mode (CAUTIOUS/NORMAL/DEFENSIVE)"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check risk_mode exists (can be in dynamic_thresholds or top-level)
        risk_mode = data.get("risk_mode") or data.get("dynamic_thresholds", {}).get("risk_mode")
        assert risk_mode is not None, f"Missing risk_mode in response"
        assert risk_mode in ["NORMAL", "CAUTIOUS", "DEFENSIVE"], f"Invalid risk_mode: {risk_mode}"
        print(f"✓ Risk mode: {risk_mode}")
    
    def test_scan_returns_pipeline_funnel(self, headers):
        """Test that scan returns pipeline_funnel with 7 stages"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check pipeline_funnel exists
        assert "pipeline_funnel" in data, f"Missing pipeline_funnel in response: {data.keys()}"
        pf = data["pipeline_funnel"]
        
        # Check required fields
        assert "funnel" in pf, f"Missing funnel in pipeline_funnel: {pf}"
        assert "bottleneck" in pf, f"Missing bottleneck in pipeline_funnel: {pf}"
        assert "top_rejections" in pf, f"Missing top_rejections in pipeline_funnel: {pf}"
        
        # Check current pipeline stages exist in funnel
        expected_stages = [
            "universe_scanned", "prefilter_passed", "ta_analyzed",
            "setup_found", "filters_passed", "confidence_passed", "risk_approved", "executed"
        ]
        funnel = pf["funnel"]
        for stage in expected_stages:
            assert stage in funnel, f"Missing stage '{stage}' in funnel: {funnel.keys()}"
        
        print(f"✓ Pipeline funnel stages: {list(funnel.keys())}")
        print(f"✓ Bottleneck: {pf['bottleneck']}")
        print(f"✓ Top rejections: {list(pf['top_rejections'].keys())[:5]}")
    
    def test_scan_returns_no_trade_summary(self, headers):
        """Test that scan returns no_trade_summary with near_misses, opportunity_quality, top_reasons"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/scan", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check no_trade_summary exists
        assert "no_trade_summary" in data, f"Missing no_trade_summary in response: {data.keys()}"
        nts = data["no_trade_summary"]
        
        # Check required fields
        assert "near_misses" in nts, f"Missing near_misses: {nts}"
        assert "opportunity_quality" in nts, f"Missing opportunity_quality: {nts}"
        assert "top_reasons" in nts, f"Missing top_reasons: {nts}"
        
        # Validate opportunity_quality values
        valid_qualities = ["HIGH_OPPORTUNITY", "MEDIUM_OPPORTUNITY", "LOW_OPPORTUNITY"]
        assert nts["opportunity_quality"] in valid_qualities, f"Invalid opportunity_quality: {nts['opportunity_quality']}"
        
        # near_misses should be a list
        assert isinstance(nts["near_misses"], list), f"near_misses should be list: {type(nts['near_misses'])}"
        
        print(f"✓ No-trade summary: opportunity={nts['opportunity_quality']}, near_misses={len(nts['near_misses'])}")
        if nts["near_misses"]:
            nm = nts["near_misses"][0]
            print(f"  First near-miss: {nm.get('symbol')} conf={nm.get('confidence')}")


class TestNewsAnalyzeEndpoint:
    """Test GET /api/news/analyze/{symbol} for new Phase 4 fields"""
    
    def test_analyze_nvda_returns_catalyst_score(self, headers):
        """Test that NVDA analysis returns catalyst_score 0-100"""
        response = requests.get(f"{BASE_URL}/api/news/analyze/NVDA", headers=headers, timeout=30)
        assert response.status_code == 200, f"News analyze failed: {response.text}"
        data = response.json()
        
        # Check catalyst_score exists
        assert "catalyst_score" in data, f"Missing catalyst_score: {data.keys()}"
        score = data["catalyst_score"]
        assert isinstance(score, (int, float)), f"catalyst_score should be numeric: {type(score)}"
        assert 0 <= score <= 100, f"catalyst_score out of range: {score}"
        print(f"✓ NVDA catalyst_score: {score}")
    
    def test_analyze_nvda_returns_category(self, headers):
        """Test that NVDA analysis returns category (HOT/BULLISH/BEARISH/WATCHLIST/IGNORE)"""
        response = requests.get(f"{BASE_URL}/api/news/analyze/NVDA", headers=headers, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # Check category exists
        assert "category" in data, f"Missing category: {data.keys()}"
        valid_categories = ["HOT", "BULLISH", "BEARISH", "WATCHLIST", "IGNORE"]
        assert data["category"] in valid_categories, f"Invalid category: {data['category']}"
        print(f"✓ NVDA category: {data['category']}")
    
    def test_analyze_nvda_returns_trade_impact(self, headers):
        """Test that NVDA analysis returns trade_impact (HIGH/MEDIUM/LOW)"""
        response = requests.get(f"{BASE_URL}/api/news/analyze/NVDA", headers=headers, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # Check trade_impact exists
        assert "trade_impact" in data, f"Missing trade_impact: {data.keys()}"
        valid_impacts = ["HIGH", "MEDIUM", "LOW"]
        assert data["trade_impact"] in valid_impacts, f"Invalid trade_impact: {data['trade_impact']}"
        print(f"✓ NVDA trade_impact: {data['trade_impact']}")
    
    def test_analyze_nvda_returns_news_velocity(self, headers):
        """Test that NVDA analysis returns news_velocity and velocity_details"""
        response = requests.get(f"{BASE_URL}/api/news/analyze/NVDA", headers=headers, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # Check news_velocity exists
        assert "news_velocity" in data, f"Missing news_velocity: {data.keys()}"
        valid_velocities = ["high", "medium", "low", "none"]
        assert data["news_velocity"] in valid_velocities, f"Invalid news_velocity: {data['news_velocity']}"
        
        # Check velocity_details if present
        if "velocity_details" in data:
            vd = data["velocity_details"]
            assert "articles_24h" in vd, f"Missing articles_24h in velocity_details"
            assert "articles_4h" in vd, f"Missing articles_4h in velocity_details"
            assert "sources" in vd, f"Missing sources in velocity_details"
            assert "trend" in vd, f"Missing trend in velocity_details"
            assert "velocity_score" in vd, f"Missing velocity_score in velocity_details"
            print(f"✓ NVDA velocity: {data['news_velocity']}, 24h={vd['articles_24h']}, 4h={vd['articles_4h']}, sources={vd['sources']}")
        else:
            print(f"✓ NVDA news_velocity: {data['news_velocity']}")
    
    def test_analyze_nvda_returns_trade_description(self, headers):
        """Test that NVDA analysis returns trade_description"""
        response = requests.get(f"{BASE_URL}/api/news/analyze/NVDA", headers=headers, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # Check trade_description exists
        assert "trade_description" in data, f"Missing trade_description: {data.keys()}"
        assert isinstance(data["trade_description"], str), f"trade_description should be string"
        assert len(data["trade_description"]) > 0, f"trade_description should not be empty"
        print(f"✓ NVDA trade_description: {data['trade_description'][:80]}...")
    
    def test_analyze_nvda_returns_filter_stats(self, headers):
        """Test that NVDA analysis returns filter_stats with pipeline stages"""
        response = requests.get(f"{BASE_URL}/api/news/analyze/NVDA", headers=headers, timeout=30)
        assert response.status_code == 200
        data = response.json()
        
        # Check filter_stats exists
        assert "filter_stats" in data, f"Missing filter_stats: {data.keys()}"
        fs = data["filter_stats"]
        
        # Check required fields
        expected_fields = ["raw_ingested", "after_relevance", "after_dedup", "high_signal_count", "filler_removed"]
        for field in expected_fields:
            assert field in fs, f"Missing {field} in filter_stats: {fs.keys()}"
        
        print(f"✓ NVDA filter_stats: raw={fs['raw_ingested']} → relevant={fs['after_relevance']} → dedup={fs['after_dedup']} → signal={fs['high_signal_count']} (filler={fs['filler_removed']})")


class TestSchedulerStatusEndpoint:
    """Test GET /api/scheduler/status for new Phase 4 fields"""
    
    def test_scheduler_returns_post_cooldown_active(self, headers):
        """Test that scheduler status returns post_cooldown_active field"""
        response = requests.get(f"{BASE_URL}/api/scheduler/status", headers=headers)
        assert response.status_code == 200, f"Scheduler status failed: {response.text}"
        data = response.json()
        
        # Check post_cooldown_active exists
        assert "post_cooldown_active" in data, f"Missing post_cooldown_active: {data.keys()}"
        assert isinstance(data["post_cooldown_active"], bool), f"post_cooldown_active should be bool"
        print(f"✓ post_cooldown_active: {data['post_cooldown_active']}")
    
    def test_scheduler_returns_daily_loss_pct_of_max(self, headers):
        """Test that scheduler status returns daily_loss_pct_of_max field"""
        response = requests.get(f"{BASE_URL}/api/scheduler/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check daily_loss_pct_of_max exists
        assert "daily_loss_pct_of_max" in data, f"Missing daily_loss_pct_of_max: {data.keys()}"
        pct = data["daily_loss_pct_of_max"]
        assert isinstance(pct, (int, float)), f"daily_loss_pct_of_max should be numeric"
        assert 0 <= pct <= 100, f"daily_loss_pct_of_max out of range: {pct}"
        print(f"✓ daily_loss_pct_of_max: {pct}%")
    
    def test_scheduler_settings_max_consecutive_losses_is_2(self, headers):
        """Test that scheduler settings has max_consecutive_losses=2 (not 3)"""
        response = requests.get(f"{BASE_URL}/api/scheduler/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check settings exists
        assert "settings" in data, f"Missing settings: {data.keys()}"
        settings = data["settings"]
        
        # Check max_consecutive_losses
        assert "max_consecutive_losses" in settings, f"Missing max_consecutive_losses: {settings.keys()}"
        assert settings["max_consecutive_losses"] == 2, f"max_consecutive_losses should be 2, got: {settings['max_consecutive_losses']}"
        print(f"✓ max_consecutive_losses: {settings['max_consecutive_losses']}")
    
    def test_scheduler_settings_post_cooldown_threshold_boost(self, headers):
        """Test that scheduler settings has post_cooldown_threshold_boost=5"""
        response = requests.get(f"{BASE_URL}/api/scheduler/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        settings = data.get("settings", {})
        
        # Check post_cooldown_threshold_boost
        assert "post_cooldown_threshold_boost" in settings, f"Missing post_cooldown_threshold_boost: {settings.keys()}"
        assert settings["post_cooldown_threshold_boost"] == 5, f"post_cooldown_threshold_boost should be 5, got: {settings['post_cooldown_threshold_boost']}"
        print(f"✓ post_cooldown_threshold_boost: {settings['post_cooldown_threshold_boost']}")


class TestNewsOverviewEndpoint:
    """Test GET /api/news/overview for category_distribution"""
    
    def test_overview_returns_category_distribution(self, headers):
        """Test that overview returns category_distribution with HOT/BULLISH/BEARISH/WATCHLIST/IGNORE"""
        response = requests.get(f"{BASE_URL}/api/news/overview", headers=headers)
        assert response.status_code == 200, f"News overview failed: {response.text}"
        data = response.json()
        
        # Check category_distribution exists
        assert "category_distribution" in data, f"Missing category_distribution: {data.keys()}"
        cd = data["category_distribution"]
        
        # Should be a dict with category keys
        assert isinstance(cd, dict), f"category_distribution should be dict: {type(cd)}"
        
        # Valid categories
        valid_categories = ["HOT", "BULLISH", "BEARISH", "WATCHLIST", "IGNORE"]
        for cat in cd.keys():
            assert cat in valid_categories, f"Invalid category in distribution: {cat}"
        
        print(f"✓ Category distribution: {cd}")


class TestNewsBreakingEndpoint:
    """Test GET /api/news/breaking for catalyst fields"""
    
    def test_breaking_returns_catalysts_with_category_badges(self, headers):
        """Test that breaking news returns items with category and velocity"""
        response = requests.get(f"{BASE_URL}/api/news/breaking", headers=headers)
        assert response.status_code == 200, f"Breaking news failed: {response.text}"
        data = response.json()
        
        # Should be a list
        assert isinstance(data, list), f"Breaking news should be list: {type(data)}"
        
        if len(data) > 0:
            item = data[0]
            # Check required fields
            assert "symbol" in item, f"Missing symbol in breaking item"
            assert "category" in item, f"Missing category in breaking item"
            assert "catalyst_score" in item, f"Missing catalyst_score in breaking item"
            
            valid_categories = ["HOT", "BULLISH", "BEARISH", "WATCHLIST", "IGNORE"]
            assert item["category"] in valid_categories, f"Invalid category: {item['category']}"
            
            print(f"✓ Breaking news: {len(data)} items, first={item['symbol']} category={item['category']} score={item['catalyst_score']}")
        else:
            print(f"✓ Breaking news: 0 items (no catalysts detected)")


class TestAutoTradeStatusEndpoint:
    """Test GET /api/auto-trade/status for market regime"""
    
    def test_status_returns_market_regime(self, headers):
        """Test that auto-trade status returns market_regime"""
        response = requests.get(f"{BASE_URL}/api/auto-trade/status", headers=headers)
        assert response.status_code == 200, f"Auto-trade status failed: {response.text}"
        data = response.json()
        
        # Check market_regime exists
        assert "market_regime" in data, f"Missing market_regime: {data.keys()}"
        mr = data["market_regime"]
        
        # Check required fields
        assert "regime" in mr, f"Missing regime in market_regime"
        valid_regimes = ["bullish", "neutral_bullish", "neutral", "neutral_bearish", "bearish", "high_volatility"]
        assert mr["regime"] in valid_regimes, f"Invalid regime: {mr['regime']}"
        
        print(f"✓ Market regime: {mr['regime']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
