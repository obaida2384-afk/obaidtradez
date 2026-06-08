"""
Test suite for ObaidTradez News Sentiment Integration
Tests: News sentiment in trading signals, news API endpoints, watchlist functionality
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8000')
ACCESS_CODE = "Bullishalmarkhan7.7"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/access",
        json={"code": ACCESS_CODE}
    )
    assert response.status_code == 200, f"Auth failed: {response.text}"
    data = response.json()
    assert data.get("success") is True
    return data.get("token")


@pytest.fixture
def api_client(auth_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestNewsSentimentInTradingSignals:
    """Test news sentiment integration in trading signals"""
    
    def test_trading_scan_returns_news_sentiment_fields(self, api_client):
        """Verify /api/trading/scan returns news_sentiment, news_impact, news_headlines"""
        response = api_client.get(f"{BASE_URL}/api/trading/scan")
        assert response.status_code == 200
        
        data = response.json()
        assert "top_trades" in data
        assert len(data["top_trades"]) > 0
        
        # Check first top trade has news sentiment fields
        first_trade = data["top_trades"][0]
        assert "news_sentiment" in first_trade, "Missing news_sentiment field"
        assert "news_impact" in first_trade, "Missing news_impact field"
        assert "news_headlines" in first_trade, "Missing news_headlines field"
        
        print(f"First trade: {first_trade['symbol']}")
        print(f"  News sentiment: {first_trade['news_sentiment']}")
        print(f"  News impact: {first_trade['news_impact']}")
        print(f"  Headlines count: {len(first_trade['news_headlines']) if first_trade['news_headlines'] else 0}")
    
    def test_news_sentiment_values_are_valid(self, api_client):
        """Verify news sentiment values are in expected range"""
        response = api_client.get(f"{BASE_URL}/api/trading/scan")
        assert response.status_code == 200
        
        data = response.json()
        valid_sentiments = ["Bullish", "Bearish", "Slightly Positive", "Slightly Negative", "Neutral"]
        
        for trade in data["top_trades"]:
            sentiment = trade.get("news_sentiment")
            impact = trade.get("news_impact")
            
            # Sentiment should be valid or None
            if sentiment:
                assert sentiment in valid_sentiments, f"Invalid sentiment: {sentiment}"
            
            # Impact should be between -10 and +10
            if impact is not None:
                assert -10 <= impact <= 10, f"Impact out of range: {impact}"
    
    def test_news_headlines_structure(self, api_client):
        """Verify news headlines have correct structure"""
        response = api_client.get(f"{BASE_URL}/api/trading/scan")
        assert response.status_code == 200
        
        data = response.json()
        
        for trade in data["top_trades"]:
            headlines = trade.get("news_headlines", [])
            if headlines:
                for headline in headlines:
                    assert "title" in headline, "Headline missing title"
                    assert "sentiment" in headline, "Headline missing sentiment"
                    print(f"  {trade['symbol']}: {headline['title'][:50]}... ({headline['sentiment']})")


class TestNewsAPIEndpoints:
    """Test dedicated news API endpoints"""
    
    def test_news_for_symbol_returns_data(self, api_client):
        """Verify /api/news/{symbol} returns news analysis data"""
        response = api_client.get(f"{BASE_URL}/api/news/AAPL")
        assert response.status_code == 200
        
        data = response.json()
        # News API now returns a dict with analysis (not a raw list)
        assert isinstance(data, dict), "Expected news analysis dict"
        assert "article_count" in data or "symbol" in data or "catalyst_score" in data
        print(f"AAPL news: {data.get('article_count', 'N/A')} articles")
    
    def test_news_for_multiple_symbols(self, api_client):
        """Test news endpoint for various symbols"""
        symbols = ["MSFT", "GOOGL", "NVDA"]
        
        for symbol in symbols:
            response = api_client.get(f"{BASE_URL}/api/news/{symbol}")
            assert response.status_code == 200, f"Failed for {symbol}"
            data = response.json()
            count = data.get("article_count", 0) if isinstance(data, dict) else len(data)
            print(f"{symbol}: {count} news items")
    
    def test_news_sentiment_scores_valid(self, api_client):
        """Verify news analysis returns valid catalyst score"""
        response = api_client.get(f"{BASE_URL}/api/news/AAPL")
        assert response.status_code == 200
        
        data = response.json()
        # News API returns dict with catalyst_score (0-100)
        if "catalyst_score" in data:
            score = data["catalyst_score"]
            assert 0 <= score <= 100, f"Invalid catalyst score: {score}"
            print(f"AAPL catalyst score: {score}")


class TestWatchlistFunctionality:
    """Test watchlist add/remove/display functionality"""
    
    def test_watchlist_loads(self, api_client):
        """Verify watchlist endpoint returns data"""
        response = api_client.get(f"{BASE_URL}/api/watchlist")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"Watchlist has {len(data)} items")
    
    def test_watchlist_items_have_required_fields(self, api_client):
        """Verify watchlist items have all required fields"""
        response = api_client.get(f"{BASE_URL}/api/watchlist")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            item = data[0]
            required_fields = ["symbol", "name", "price", "signal", "category"]
            for field in required_fields:
                assert field in item, f"Missing field: {field}"
            print(f"Sample item: {item['symbol']} - ${item['price']} - {item['signal']}")
    
    def test_add_stock_to_watchlist(self, api_client):
        """Test adding a stock to watchlist"""
        # First remove if exists
        api_client.delete(f"{BASE_URL}/api/watchlist/GME")
        
        # Add stock
        response = api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "GME", "source": "test"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        print(f"Added GME: {data.get('message')}")
        
        # Verify it's in watchlist
        response = api_client.get(f"{BASE_URL}/api/watchlist")
        symbols = [item["symbol"] for item in response.json()]
        assert "GME" in symbols, "GME not found in watchlist after adding"
    
    def test_remove_stock_from_watchlist(self, api_client):
        """Test removing a stock from watchlist"""
        # First ensure it exists
        api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "GME", "source": "test"}
        )
        
        # Remove it
        response = api_client.delete(f"{BASE_URL}/api/watchlist/GME")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        print(f"Removed GME: {data.get('message')}")
    
    def test_watchlist_persists(self, api_client):
        """Test that watchlist items persist"""
        # Add a test stock
        api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={"symbol": "AMD", "source": "test"}
        )
        
        # Get watchlist
        response = api_client.get(f"{BASE_URL}/api/watchlist")
        assert response.status_code == 200
        
        symbols = [item["symbol"] for item in response.json()]
        assert "AMD" in symbols, "AMD should persist in watchlist"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/watchlist/AMD")


class TestInvestmentPage:
    """Test investment page loads successfully"""
    
    def test_investments_scan_returns_data(self, api_client):
        """Verify /api/investments/scan returns categories"""
        response = api_client.get(f"{BASE_URL}/api/investments/scan")
        assert response.status_code == 200
        
        data = response.json()
        categories = ["hot", "bullish", "undervalued", "watch", "bearish"]
        
        for cat in categories:
            assert cat in data, f"Missing category: {cat}"
            print(f"{cat}: {len(data[cat])} stocks")
    
    def test_investments_browse_returns_data(self, api_client):
        """Verify /api/investments/browse returns paginated data"""
        response = api_client.get(f"{BASE_URL}/api/investments/browse")
        assert response.status_code == 200
        
        data = response.json()
        assert "signals" in data
        assert "total" in data
        print(f"Total stocks: {data['total']}")


class TestDashboardData:
    """Test dashboard displays trading signals and investment ideas"""
    
    def test_trading_scan_for_dashboard(self, api_client):
        """Verify trading scan provides data for dashboard"""
        response = api_client.get(f"{BASE_URL}/api/trading/scan")
        assert response.status_code == 200
        
        data = response.json()
        assert "top_trades" in data
        assert len(data["top_trades"]) > 0
        
        # Dashboard should show top trading signals
        print(f"Top trades for dashboard: {len(data['top_trades'])}")
        for trade in data["top_trades"][:3]:
            print(f"  {trade['symbol']}: {trade['signal']} ({trade['confidence']*100:.0f}%)")
    
    def test_investments_scan_for_dashboard(self, api_client):
        """Verify investments scan provides data for dashboard"""
        response = api_client.get(f"{BASE_URL}/api/investments/scan")
        assert response.status_code == 200
        
        data = response.json()
        assert "hot" in data
        
        # Dashboard should show investment ideas
        print(f"Hot investment ideas: {len(data['hot'])}")


class TestHighVolatilityStocks:
    """Test high-volatility day trading stocks are in universe"""
    
    def test_day_trading_stocks_in_universe(self, api_client):
        """Verify high-volatility stocks are available"""
        # These should be in the expanded universe
        day_trading_stocks = ["GME", "AMC", "TQQQ", "SQQQ", "MARA", "RIOT"]
        
        for symbol in day_trading_stocks:
            response = api_client.get(f"{BASE_URL}/api/trading/analyze/{symbol}")
            # Should return 200 even if no signal generated
            assert response.status_code == 200, f"Failed to analyze {symbol}"
            print(f"{symbol}: Analysis available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
