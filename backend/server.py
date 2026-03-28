"""
ObaidTradez - AI Trading & Investing Platform
Backend Server with Multi-API Integration
"""

from fastapi import FastAPI, APIRouter, HTTPException, Query, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Tuple
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import asyncio
import json
import hashlib
import secrets

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# ===================== CONFIGURATION =====================
class Config:
    MONGO_URL = os.environ['MONGO_URL']
    DB_NAME = os.environ.get('DB_NAME', 'obaidtradez')
    ACCESS_CODE = os.environ.get('ACCESS_CODE_HASH', '')
    EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
    
    # Financial APIs
    FMP_API_KEY = os.environ.get('FMP_API_KEY')
    ALPHA_VANTAGE_KEY = os.environ.get('ALPHA_VANTAGE_KEY')
    NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
    POLYGON_API_KEY = os.environ.get('POLYGON_API_KEY')
    FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY')
    
    # Alpaca
    ALPACA_API_KEY = os.environ.get('ALPACA_API_KEY')
    ALPACA_SECRET_KEY = os.environ.get('ALPACA_SECRET_KEY')
    ALPACA_BASE_URL = os.environ.get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

config = Config()

# MongoDB
client = AsyncIOMotorClient(config.MONGO_URL)
db = client[config.DB_NAME]

# FastAPI App
app = FastAPI(title="ObaidTradez API", description="AI Trading & Investing Platform")
api_router = APIRouter(prefix="/api")

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===================== CACHE =====================
_cache: Dict[str, tuple] = {}
CACHE_TTL = 120  # 2 minutes

def get_cached(key: str) -> Optional[Any]:
    if key in _cache:
        data, ts = _cache[key]
        if datetime.now().timestamp() - ts < CACHE_TTL:
            return data
    return None

def set_cached(key: str, data: Any, ttl: int = None):
    _cache[key] = (data, datetime.now().timestamp())

# ===================== MODELS =====================

class AccessRequest(BaseModel):
    code: str

class AccessResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str

class TradingSignal(BaseModel):
    symbol: str
    name: str
    price: Optional[float] = None
    signal: str  # Buy, Watch, Avoid
    confidence: float
    entry_zone: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[str] = None
    risk_reward: Optional[str] = None
    reasoning: str
    indicators: Dict[str, Any] = {}
    category: str  # Hot, Medium, Avoid, Breakout, Momentum, HighVolatility

class InvestmentSignal(BaseModel):
    symbol: str
    name: str
    price: Optional[float] = None
    signal: str  # Buy, Hold, Sell, Watchlist
    confidence: float
    overall_score: float
    valuation_score: float
    quality_score: float
    growth_score: float
    financial_strength: float
    risk_score: float
    intrinsic_value: Optional[float] = None
    upside_potential: Optional[str] = None
    bull_case: List[str] = []
    bear_case: List[str] = []
    risks: List[str] = []
    reasoning: str
    category: str  # Hot, Bullish, Bearish, Undervalued, Overpriced, Watch

class NewsItem(BaseModel):
    title: str
    source: str
    url: str
    published: str
    sentiment: str  # Positive, Neutral, Negative
    sentiment_score: float
    summary: Optional[str] = None
    symbols: List[str] = []

class RiskSettings(BaseModel):
    max_position_size: float = 0.05  # 5% of portfolio
    max_daily_loss: float = 0.02  # 2%
    max_weekly_loss: float = 0.05  # 5%
    max_drawdown: float = 0.10  # 10%
    min_confidence: float = 0.6
    cash_buffer: float = 0.10  # Keep 10% cash
    sector_limit: float = 0.25  # Max 25% in one sector

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    mode: str = "general"  # trading, investing, general

# ===================== ACCESS CONTROL =====================

# Store valid session tokens
_valid_tokens: Dict[str, datetime] = {}

def generate_token() -> str:
    return secrets.token_urlsafe(32)

def validate_access_code(code: str) -> bool:
    return code == config.ACCESS_CODE

def validate_token(token: str) -> bool:
    if token in _valid_tokens:
        if datetime.now() < _valid_tokens[token]:
            return True
        else:
            del _valid_tokens[token]
    return False

async def verify_access(authorization: str = Header(None)) -> bool:
    if not authorization:
        raise HTTPException(status_code=401, detail="Access token required")
    
    token = authorization.replace("Bearer ", "")
    if not validate_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return True

# ===================== API CLIENTS =====================

class MultiAPIClient:
    """Unified multi-provider API client with fallback"""
    
    def __init__(self):
        self.fmp_url = "https://financialmodelingprep.com/stable"
        self.polygon_url = "https://api.polygon.io"
        self.finnhub_url = "https://finnhub.io/api/v1"
        self.news_url = "https://newsapi.org/v2"
        self.alpaca_url = config.ALPACA_BASE_URL
        self.alpaca_data_url = "https://data.alpaca.markets"
    
    async def _request(self, url: str, headers: Dict = None, params: Dict = None) -> Optional[Any]:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    return resp.json()
                logger.warning(f"API error {resp.status_code}: {url}")
        except Exception as e:
            logger.error(f"Request error: {e}")
        return None
    
    # FMP Methods
    async def fmp_quote(self, symbol: str) -> Optional[Dict]:
        cache_key = f"fmp_quote_{symbol}"
        cached = get_cached(cache_key)
        if cached:
            return cached
        
        data = await self._request(
            f"{self.fmp_url}/quote",
            headers={"apikey": config.FMP_API_KEY},
            params={"symbol": symbol}
        )
        if data and isinstance(data, list) and len(data) > 0:
            set_cached(cache_key, data[0])
            return data[0]
        return None
    
    async def fmp_profile(self, symbol: str) -> Optional[Dict]:
        cache_key = f"fmp_profile_{symbol}"
        cached = get_cached(cache_key)
        if cached:
            return cached
        
        data = await self._request(
            f"{self.fmp_url}/profile",
            headers={"apikey": config.FMP_API_KEY},
            params={"symbol": symbol}
        )
        if data and isinstance(data, list) and len(data) > 0:
            set_cached(cache_key, data[0])
            return data[0]
        return None
    
    async def fmp_ratios(self, symbol: str) -> Optional[Dict]:
        data = await self._request(
            f"{self.fmp_url}/ratios-ttm",
            headers={"apikey": config.FMP_API_KEY},
            params={"symbol": symbol}
        )
        return data[0] if data and isinstance(data, list) and len(data) > 0 else None
    
    async def fmp_metrics(self, symbol: str) -> Optional[Dict]:
        data = await self._request(
            f"{self.fmp_url}/key-metrics-ttm",
            headers={"apikey": config.FMP_API_KEY},
            params={"symbol": symbol}
        )
        return data[0] if data and isinstance(data, list) and len(data) > 0 else None
    
    async def fmp_growth(self, symbol: str) -> Optional[Dict]:
        data = await self._request(
            f"{self.fmp_url}/financial-growth",
            headers={"apikey": config.FMP_API_KEY},
            params={"symbol": symbol, "limit": 1}
        )
        return data[0] if data and isinstance(data, list) and len(data) > 0 else None
    
    async def fmp_historical(self, symbol: str) -> Optional[List]:
        data = await self._request(
            f"{self.fmp_url}/historical-price-eod/full",
            headers={"apikey": config.FMP_API_KEY},
            params={"symbol": symbol}
        )
        return data if isinstance(data, list) else None
    
    async def fmp_screener(self, params: Dict) -> Optional[List]:
        return await self._request(
            f"{self.fmp_url}/company-screener",
            headers={"apikey": config.FMP_API_KEY},
            params=params
        )
    
    # Polygon Methods
    async def polygon_quote(self, symbol: str) -> Optional[Dict]:
        data = await self._request(
            f"{self.polygon_url}/v2/aggs/ticker/{symbol}/prev",
            params={"apiKey": config.POLYGON_API_KEY}
        )
        if data and data.get("results"):
            return data["results"][0]
        return None
    
    async def polygon_news(self, symbol: str = None, limit: int = 10) -> Optional[List]:
        params = {"apiKey": config.POLYGON_API_KEY, "limit": limit}
        if symbol:
            params["ticker"] = symbol
        data = await self._request(f"{self.polygon_url}/v2/reference/news", params=params)
        return data.get("results", []) if data else None
    
    # Finnhub Methods
    async def finnhub_quote(self, symbol: str) -> Optional[Dict]:
        return await self._request(
            f"{self.finnhub_url}/quote",
            params={"symbol": symbol, "token": config.FINNHUB_API_KEY}
        )
    
    async def finnhub_news(self, symbol: str) -> Optional[List]:
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        return await self._request(
            f"{self.finnhub_url}/company-news",
            params={"symbol": symbol, "from": week_ago, "to": today, "token": config.FINNHUB_API_KEY}
        )
    
    async def finnhub_sentiment(self, symbol: str) -> Optional[Dict]:
        return await self._request(
            f"{self.finnhub_url}/news-sentiment",
            params={"symbol": symbol, "token": config.FINNHUB_API_KEY}
        )
    
    # NewsAPI Methods
    async def newsapi_search(self, query: str, limit: int = 10) -> Optional[List]:
        data = await self._request(
            f"{self.news_url}/everything",
            params={
                "q": query,
                "apiKey": config.NEWS_API_KEY,
                "pageSize": limit,
                "sortBy": "publishedAt",
                "language": "en"
            }
        )
        return data.get("articles", []) if data else None
    
    # Alpaca Methods
    async def alpaca_account(self) -> Optional[Dict]:
        return await self._request(
            f"{self.alpaca_url}/v2/account",
            headers={
                "APCA-API-KEY-ID": config.ALPACA_API_KEY,
                "APCA-API-SECRET-KEY": config.ALPACA_SECRET_KEY
            }
        )
    
    async def alpaca_positions(self) -> Optional[List]:
        return await self._request(
            f"{self.alpaca_url}/v2/positions",
            headers={
                "APCA-API-KEY-ID": config.ALPACA_API_KEY,
                "APCA-API-SECRET-KEY": config.ALPACA_SECRET_KEY
            }
        )
    
    async def alpaca_orders(self, status: str = "open") -> Optional[List]:
        return await self._request(
            f"{self.alpaca_url}/v2/orders",
            headers={
                "APCA-API-KEY-ID": config.ALPACA_API_KEY,
                "APCA-API-SECRET-KEY": config.ALPACA_SECRET_KEY
            },
            params={"status": status}
        )

api_client = MultiAPIClient()

# ===================== TRADING SIGNAL ENGINE =====================

class TradingEngine:
    """Short-term trading signal generation"""
    
    async def analyze_for_trading(self, symbol: str) -> Optional[TradingSignal]:
        """Analyze stock for short-term trading opportunities"""
        try:
            quote, profile = await asyncio.gather(
                api_client.fmp_quote(symbol),
                api_client.fmp_profile(symbol),
                return_exceptions=True
            )
            
            if isinstance(quote, Exception) or not quote:
                return None
            if isinstance(profile, Exception):
                profile = None
            
            price = quote.get('price', 0)
            change_pct = quote.get('changesPercentage', 0)
            volume = quote.get('volume', 0)
            avg_volume = quote.get('avgVolume', 1)
            sma50 = quote.get('priceAvg50', 0)
            sma200 = quote.get('priceAvg200', 0)
            high_52 = quote.get('yearHigh', 0)
            low_52 = quote.get('yearLow', 0)
            
            # Calculate indicators
            vol_ratio = volume / avg_volume if avg_volume > 0 else 1
            price_vs_50 = ((price / sma50) - 1) * 100 if sma50 > 0 else 0
            price_vs_200 = ((price / sma200) - 1) * 100 if sma200 > 0 else 0
            
            # Position in 52-week range
            range_52 = high_52 - low_52 if high_52 > low_52 else 1
            position_52 = ((price - low_52) / range_52) * 100 if range_52 > 0 else 50
            
            # Score components
            momentum_score = 50
            volume_score = 50
            technical_score = 50
            trend_score = 50
            
            reasons = []
            
            # Momentum analysis
            if change_pct > 3:
                momentum_score += 25
                reasons.append(f"Strong momentum (+{change_pct:.1f}% today)")
            elif change_pct > 1:
                momentum_score += 15
            elif change_pct < -3:
                momentum_score -= 20
                reasons.append(f"Weak price action ({change_pct:.1f}%)")
            
            # Volume analysis
            if vol_ratio > 2:
                volume_score += 30
                reasons.append(f"High volume ({vol_ratio:.1f}x average)")
            elif vol_ratio > 1.5:
                volume_score += 15
            elif vol_ratio < 0.5:
                volume_score -= 15
            
            # Technical setup
            if price > sma50 > sma200:
                technical_score += 25
                trend_score += 20
                reasons.append("Bullish MA alignment")
            elif price > sma50:
                technical_score += 10
            elif price < sma50 < sma200:
                technical_score -= 20
                reasons.append("Bearish trend")
            
            # Breakout detection
            if position_52 > 90 and vol_ratio > 1.5:
                technical_score += 20
                reasons.append("Near 52-week high with volume (breakout)")
            elif position_52 < 20:
                technical_score -= 10
            
            # Calculate overall
            overall = (momentum_score * 0.30 + volume_score * 0.25 + 
                      technical_score * 0.25 + trend_score * 0.20)
            
            # Determine signal
            if overall >= 70 and len(reasons) >= 2:
                signal = "Buy"
                category = "Hot" if overall >= 80 else "Breakout"
            elif overall >= 55:
                signal = "Watch"
                category = "Medium"
            else:
                signal = "Avoid"
                category = "Avoid"
            
            # Entry/Exit calculation
            entry_zone = f"${price * 0.98:.2f} - ${price:.2f}"
            stop_loss = round(price * 0.95, 2)  # 5% stop
            take_profit = round(price * 1.10, 2)  # 10% target
            risk = price - stop_loss
            reward = take_profit - price
            rr_ratio = f"1:{reward/risk:.1f}" if risk > 0 else "N/A"
            
            return TradingSignal(
                symbol=symbol,
                name=profile.get('companyName', symbol) if profile else symbol,
                price=price,
                signal=signal,
                confidence=min(overall / 100, 0.95),
                entry_zone=entry_zone,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size="2-3% of portfolio",
                risk_reward=rr_ratio,
                reasoning="; ".join(reasons) if reasons else "Standard setup",
                indicators={
                    "change_pct": change_pct,
                    "volume_ratio": round(vol_ratio, 2),
                    "price_vs_50ma": round(price_vs_50, 2),
                    "price_vs_200ma": round(price_vs_200, 2),
                    "52_week_position": round(position_52, 1)
                },
                category=category
            )
        except Exception as e:
            logger.error(f"Trading analysis error for {symbol}: {e}")
            return None
    
    async def scan_trading_opportunities(self) -> Dict[str, List[TradingSignal]]:
        """Scan market for trading opportunities"""
        # Trading-focused universe
        universe = [
            "NVDA", "AMD", "TSLA", "META", "AAPL", "MSFT", "GOOGL", "AMZN",
            "NFLX", "CRM", "SHOP", "SQ", "COIN", "PLTR", "ROKU", "SNAP",
            "UBER", "ABNB", "RIVN", "LCID", "NIO", "MARA", "RIOT", "HOOD"
        ]
        
        signals = await asyncio.gather(*[self.analyze_for_trading(s) for s in universe])
        signals = [s for s in signals if s]
        
        hot = [s for s in signals if s.category == "Hot"]
        breakout = [s for s in signals if s.category == "Breakout"]
        momentum = [s for s in signals if s.indicators.get('change_pct', 0) > 2]
        high_volume = [s for s in signals if s.indicators.get('volume_ratio', 0) > 1.5]
        avoid = [s for s in signals if s.signal == "Avoid"]
        
        return {
            "hot": sorted(hot, key=lambda x: x.confidence, reverse=True)[:5],
            "breakout": sorted(breakout, key=lambda x: x.confidence, reverse=True)[:5],
            "momentum": sorted(momentum, key=lambda x: x.indicators.get('change_pct', 0), reverse=True)[:5],
            "high_volume": sorted(high_volume, key=lambda x: x.indicators.get('volume_ratio', 0), reverse=True)[:5],
            "avoid": avoid[:5],
            "all": sorted(signals, key=lambda x: x.confidence, reverse=True)
        }

trading_engine = TradingEngine()

# ===================== INVESTMENT SIGNAL ENGINE =====================

class InvestmentEngine:
    """Long-term investment analysis"""
    
    SECTOR_BENCHMARKS = {
        "Technology": {"pe": 28, "roe": 20, "growth": 15, "margin": 22},
        "Healthcare": {"pe": 22, "roe": 15, "growth": 10, "margin": 18},
        "Financial Services": {"pe": 12, "roe": 12, "growth": 6, "margin": 28},
        "Consumer Cyclical": {"pe": 20, "roe": 16, "growth": 8, "margin": 12},
        "Consumer Defensive": {"pe": 24, "roe": 18, "growth": 5, "margin": 14},
        "Industrials": {"pe": 20, "roe": 15, "growth": 7, "margin": 12},
        "Energy": {"pe": 12, "roe": 12, "growth": 5, "margin": 15},
        "default": {"pe": 20, "roe": 15, "growth": 8, "margin": 15}
    }
    
    async def analyze_for_investment(self, symbol: str) -> Optional[InvestmentSignal]:
        """Analyze stock for long-term investment"""
        try:
            quote, profile, ratios, metrics, growth = await asyncio.gather(
                api_client.fmp_quote(symbol),
                api_client.fmp_profile(symbol),
                api_client.fmp_ratios(symbol),
                api_client.fmp_metrics(symbol),
                api_client.fmp_growth(symbol),
                return_exceptions=True
            )
            
            # Handle exceptions
            quote = None if isinstance(quote, Exception) else quote
            profile = None if isinstance(profile, Exception) else profile
            ratios = None if isinstance(ratios, Exception) else ratios
            metrics = None if isinstance(metrics, Exception) else metrics
            growth = None if isinstance(growth, Exception) else growth
            
            if not quote and not profile:
                return None
            
            # Combine data
            data = {}
            for d in [ratios, metrics, growth, quote, profile]:
                if d:
                    data.update(d)
            
            sector = data.get('sector', 'default')
            benchmark = self.SECTOR_BENCHMARKS.get(sector, self.SECTOR_BENCHMARKS['default'])
            price = data.get('price', 0)
            
            bull_case = []
            bear_case = []
            risks = []
            
            # Valuation Score
            valuation_score = 50
            pe = data.get('peRatioTTM')
            if pe and pe > 0:
                if pe < benchmark['pe'] * 0.7:
                    valuation_score += 25
                    bull_case.append(f"Attractive P/E of {pe:.1f} vs sector {benchmark['pe']}")
                elif pe < benchmark['pe']:
                    valuation_score += 12
                elif pe > benchmark['pe'] * 1.5:
                    valuation_score -= 20
                    bear_case.append(f"Premium valuation (P/E: {pe:.1f})")
            
            ev_ebitda = data.get('enterpriseValueOverEBITDATTM')
            if ev_ebitda and 0 < ev_ebitda < 50:
                if ev_ebitda < 10:
                    valuation_score += 15
                    bull_case.append(f"Low EV/EBITDA of {ev_ebitda:.1f}")
                elif ev_ebitda > 20:
                    valuation_score -= 10
            
            # Quality Score
            quality_score = 50
            roe = data.get('returnOnEquityTTM')
            if roe:
                roe_pct = roe * 100 if abs(roe) < 1 else roe
                if roe_pct > benchmark['roe'] * 1.5:
                    quality_score += 25
                    bull_case.append(f"Excellent ROE of {roe_pct:.1f}%")
                elif roe_pct > benchmark['roe']:
                    quality_score += 12
                elif roe_pct < 8:
                    quality_score -= 15
                    bear_case.append(f"Low ROE ({roe_pct:.1f}%)")
            
            net_margin = data.get('netProfitMarginTTM')
            if net_margin:
                margin_pct = net_margin * 100 if abs(net_margin) < 1 else net_margin
                if margin_pct > benchmark['margin']:
                    quality_score += 10
                elif margin_pct < 5:
                    quality_score -= 10
                    risks.append("Thin profit margins")
            
            # Growth Score
            growth_score = 50
            rev_growth = data.get('revenueGrowth')
            if rev_growth is not None:
                growth_pct = rev_growth * 100 if abs(rev_growth) < 1 else rev_growth
                if growth_pct > 20:
                    growth_score += 25
                    bull_case.append(f"Strong revenue growth ({growth_pct:.1f}%)")
                elif growth_pct > 10:
                    growth_score += 12
                elif growth_pct < 0:
                    growth_score -= 20
                    bear_case.append(f"Revenue declining ({growth_pct:.1f}%)")
            
            # Financial Strength Score
            strength_score = 50
            de = data.get('debtEquityRatioTTM')
            if de is not None:
                if de < 0.3:
                    strength_score += 20
                    bull_case.append(f"Strong balance sheet (D/E: {de:.2f})")
                elif de > 1.5:
                    strength_score -= 20
                    risks.append(f"High debt (D/E: {de:.2f})")
            
            current = data.get('currentRatioTTM')
            if current:
                if current > 2:
                    strength_score += 10
                elif current < 1:
                    strength_score -= 15
                    risks.append("Liquidity concerns")
            
            # Risk Score (higher = safer)
            risk_score = 70
            beta = data.get('beta', 1)
            if beta and beta > 1.5:
                risk_score -= 20
                risks.append(f"High volatility (beta: {beta:.2f})")
            elif beta and beta < 0.8:
                risk_score += 10
            
            market_cap = data.get('marketCap', 0)
            if market_cap < 2e9:
                risk_score -= 15
                risks.append("Small cap risk")
            elif market_cap > 100e9:
                risk_score += 10
            
            # Overall Score
            overall = (
                valuation_score * 0.25 +
                quality_score * 0.25 +
                growth_score * 0.20 +
                strength_score * 0.20 +
                risk_score * 0.10
            )
            
            # Determine signal
            if overall >= 72 and len(bull_case) >= 2:
                signal = "Buy"
                category = "Hot" if overall >= 80 else "Bullish"
            elif overall >= 58:
                signal = "Hold" if len(bear_case) > 0 else "Watchlist"
                category = "Watch"
            elif overall >= 45:
                signal = "Watchlist"
                category = "Watch"
            else:
                signal = "Sell" if len(bear_case) >= 2 else "Watchlist"
                category = "Bearish" if overall < 40 else "Watch"
            
            # Intrinsic value estimate (simplified DCF proxy)
            fcf = data.get('freeCashFlowPerShareTTM', 0)
            intrinsic = None
            upside = None
            if fcf and fcf > 0:
                growth_rate = (rev_growth or 0.05)
                discount_rate = 0.10
                terminal_multiple = 15
                intrinsic = fcf * terminal_multiple * (1 + growth_rate)
                if price > 0:
                    upside_pct = ((intrinsic / price) - 1) * 100
                    upside = f"{upside_pct:+.1f}%"
                    if upside_pct > 30:
                        bull_case.append(f"Potential upside of {upside_pct:.0f}%")
                        category = "Undervalued"
                    elif upside_pct < -20:
                        bear_case.append(f"Appears overvalued by {abs(upside_pct):.0f}%")
                        category = "Overpriced"
            
            reasoning = f"Overall score {overall:.0f}/100. "
            if bull_case:
                reasoning += f"Strengths: {'; '.join(bull_case[:2])}. "
            if bear_case:
                reasoning += f"Concerns: {'; '.join(bear_case[:2])}."
            
            return InvestmentSignal(
                symbol=symbol,
                name=data.get('companyName', symbol),
                price=price,
                signal=signal,
                confidence=min(overall / 100, 0.95),
                overall_score=round(overall, 1),
                valuation_score=round(valuation_score, 1),
                quality_score=round(quality_score, 1),
                growth_score=round(growth_score, 1),
                financial_strength=round(strength_score, 1),
                risk_score=round(risk_score, 1),
                intrinsic_value=round(intrinsic, 2) if intrinsic else None,
                upside_potential=upside,
                bull_case=bull_case[:5],
                bear_case=bear_case[:5],
                risks=risks[:5],
                reasoning=reasoning,
                category=category
            )
        except Exception as e:
            logger.error(f"Investment analysis error for {symbol}: {e}")
            return None
    
    async def scan_investment_opportunities(self) -> Dict[str, List[InvestmentSignal]]:
        """Scan for long-term investment opportunities"""
        # Investment-focused universe (quality companies)
        universe = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "V", "MA", "JPM",
            "JNJ", "UNH", "PG", "HD", "KO", "PEP", "WMT", "COST", "MCD", "DIS",
            "ADBE", "CRM", "NFLX", "INTC", "AMD", "QCOM", "TXN", "AVGO", "CSCO"
        ]
        
        signals = await asyncio.gather(*[self.analyze_for_investment(s) for s in universe])
        signals = [s for s in signals if s]
        
        hot = [s for s in signals if s.category == "Hot"]
        bullish = [s for s in signals if s.category == "Bullish"]
        undervalued = [s for s in signals if s.category == "Undervalued"]
        bearish = [s for s in signals if s.category == "Bearish"]
        overpriced = [s for s in signals if s.category == "Overpriced"]
        watch = [s for s in signals if s.category == "Watch"]
        
        return {
            "hot": sorted(hot, key=lambda x: x.overall_score, reverse=True)[:5],
            "bullish": sorted(bullish, key=lambda x: x.overall_score, reverse=True)[:5],
            "undervalued": sorted(undervalued, key=lambda x: x.overall_score, reverse=True)[:5],
            "watch": sorted(watch, key=lambda x: x.overall_score, reverse=True)[:5],
            "bearish": bearish[:5],
            "overpriced": overpriced[:5],
            "avoid": [s for s in signals if s.signal == "Sell"][:5],
            "all": sorted(signals, key=lambda x: x.overall_score, reverse=True)
        }

investment_engine = InvestmentEngine()

# ===================== NEWS & SENTIMENT =====================

class NewsSentimentEngine:
    """News aggregation and sentiment analysis"""
    
    POSITIVE_WORDS = ['surge', 'jump', 'beat', 'exceed', 'upgrade', 'buy', 'bullish', 'growth', 'profit', 'gain', 'rally', 'breakthrough']
    NEGATIVE_WORDS = ['drop', 'fall', 'miss', 'downgrade', 'sell', 'bearish', 'loss', 'decline', 'crash', 'warning', 'lawsuit', 'investigation']
    
    def analyze_sentiment(self, text: str) -> Tuple[str, float]:
        """Simple rule-based sentiment analysis"""
        text_lower = text.lower()
        pos_count = sum(1 for w in self.POSITIVE_WORDS if w in text_lower)
        neg_count = sum(1 for w in self.NEGATIVE_WORDS if w in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return "Neutral", 0.5
        
        score = pos_count / total
        if score > 0.6:
            return "Positive", score
        elif score < 0.4:
            return "Negative", 1 - score
        return "Neutral", 0.5
    
    async def get_news_for_symbol(self, symbol: str) -> List[NewsItem]:
        """Get news for a specific symbol"""
        news_items = []
        
        # Try Finnhub first
        finnhub_news = await api_client.finnhub_news(symbol)
        if finnhub_news:
            for item in finnhub_news[:5]:
                sentiment, score = self.analyze_sentiment(item.get('headline', ''))
                news_items.append(NewsItem(
                    title=item.get('headline', ''),
                    source=item.get('source', 'Unknown'),
                    url=item.get('url', ''),
                    published=item.get('datetime', ''),
                    sentiment=sentiment,
                    sentiment_score=score,
                    summary=item.get('summary', ''),
                    symbols=[symbol]
                ))
        
        # Try Polygon as backup
        if len(news_items) < 5:
            polygon_news = await api_client.polygon_news(symbol, limit=5)
            if polygon_news:
                for item in polygon_news:
                    sentiment, score = self.analyze_sentiment(item.get('title', ''))
                    news_items.append(NewsItem(
                        title=item.get('title', ''),
                        source=item.get('publisher', {}).get('name', 'Unknown'),
                        url=item.get('article_url', ''),
                        published=item.get('published_utc', ''),
                        sentiment=sentiment,
                        sentiment_score=score,
                        summary=item.get('description', ''),
                        symbols=item.get('tickers', [])
                    ))
        
        return news_items[:10]
    
    async def get_market_news(self) -> List[NewsItem]:
        """Get general market news"""
        news_items = []
        
        # Search for market news via NewsAPI
        newsapi_results = await api_client.newsapi_search("stock market finance trading", limit=10)
        if newsapi_results:
            for item in newsapi_results:
                sentiment, score = self.analyze_sentiment(item.get('title', ''))
                news_items.append(NewsItem(
                    title=item.get('title', ''),
                    source=item.get('source', {}).get('name', 'Unknown'),
                    url=item.get('url', ''),
                    published=item.get('publishedAt', ''),
                    sentiment=sentiment,
                    sentiment_score=score,
                    summary=item.get('description', ''),
                    symbols=[]
                ))
        
        return news_items

news_engine = NewsSentimentEngine()

# ===================== AI CHATBOT =====================

async def get_chatbot_response(message: str, session_id: str, mode: str = "general") -> str:
    """AI-powered financial assistant"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    system_prompts = {
        "trading": """You are ObaidTradez Trading Assistant - an expert short-term trading advisor.

Focus on: momentum, breakouts, volume, technical setups, risk/reward, entry/exit zones.
For every trade idea provide: signal (Buy/Watch/Avoid), confidence, entry zone, stop-loss, take-profit, position size, reasoning.
Be direct and actionable. Never give generic advice.""",

        "investing": """You are ObaidTradez Investment Assistant - an expert long-term investment advisor.

Focus on: business quality, valuation, cash flows, growth, intrinsic value, competitive moats, management.
For every investment idea provide: signal (Buy/Hold/Sell/Watchlist), confidence, valuation assessment, bull case, bear case, risks.
Explain like Warren Buffett - clear, logical, focused on business fundamentals.""",

        "general": """You are ObaidTradez AI - a comprehensive financial assistant.

You can help with:
- Trading questions (momentum, technicals, entries, exits)
- Investment questions (valuation, DCF, fundamentals)
- Financial modeling (DCF, comparables, LBO basics)
- Chart analysis and pattern interpretation
- Portfolio construction and risk management
- Financial metrics and ratios explanation

Be direct, practical, and educational. Reference specific numbers when possible."""
    }
    
    system_message = system_prompts.get(mode, system_prompts["general"])
    
    try:
        chat = LlmChat(
            api_key=config.EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=system_message
        ).with_model("openai", "gpt-5.2")
        
        user_message = UserMessage(text=message)
        response = await chat.send_message(user_message)
        return response
    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        return f"I apologize, but I encountered an error. Please try again. Error: {str(e)}"

# ===================== ROUTES =====================

# Access Control
@api_router.post("/auth/access", response_model=AccessResponse)
async def verify_access_code(request: AccessRequest):
    """Verify access code and return session token"""
    if validate_access_code(request.code):
        token = generate_token()
        _valid_tokens[token] = datetime.now() + timedelta(hours=24)
        
        # Log successful access
        await db.access_logs.insert_one({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": True
        })
        
        return AccessResponse(success=True, token=token, message="Access granted")
    
    # Log failed attempt
    await db.access_logs.insert_one({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": False
    })
    
    return AccessResponse(success=False, message="Invalid access code")

@api_router.get("/auth/verify")
async def verify_token(authorization: str = Header(None)):
    """Verify if token is valid"""
    if not authorization:
        return {"valid": False}
    token = authorization.replace("Bearer ", "")
    return {"valid": validate_token(token)}

# Trading
@api_router.get("/trading/scan")
async def scan_trading(auth: bool = Depends(verify_access)):
    """Scan market for trading opportunities"""
    return await trading_engine.scan_trading_opportunities()

@api_router.get("/trading/analyze/{symbol}")
async def analyze_trading(symbol: str, auth: bool = Depends(verify_access)):
    """Analyze specific symbol for trading"""
    signal = await trading_engine.analyze_for_trading(symbol.upper())
    if not signal:
        raise HTTPException(status_code=404, detail=f"Unable to analyze {symbol}")
    return signal

# Investments
@api_router.get("/investments/scan")
async def scan_investments(auth: bool = Depends(verify_access)):
    """Scan market for investment opportunities"""
    return await investment_engine.scan_investment_opportunities()

@api_router.get("/investments/analyze/{symbol}")
async def analyze_investment(symbol: str, auth: bool = Depends(verify_access)):
    """Analyze specific symbol for investment"""
    signal = await investment_engine.analyze_for_investment(symbol.upper())
    if not signal:
        raise HTTPException(status_code=404, detail=f"Unable to analyze {symbol}")
    return signal

# News & Sentiment
@api_router.get("/news/market")
async def get_market_news(auth: bool = Depends(verify_access)):
    """Get general market news"""
    return await news_engine.get_market_news()

@api_router.get("/news/{symbol}")
async def get_symbol_news(symbol: str, auth: bool = Depends(verify_access)):
    """Get news for specific symbol"""
    return await news_engine.get_news_for_symbol(symbol.upper())

# Alpaca Account
@api_router.get("/account")
async def get_account(auth: bool = Depends(verify_access)):
    """Get Alpaca account info"""
    account = await api_client.alpaca_account()
    if not account:
        raise HTTPException(status_code=500, detail="Unable to fetch account")
    return account

@api_router.get("/positions")
async def get_positions(auth: bool = Depends(verify_access)):
    """Get current positions"""
    positions = await api_client.alpaca_positions()
    return positions or []

@api_router.get("/orders")
async def get_orders(status: str = "open", auth: bool = Depends(verify_access)):
    """Get orders"""
    orders = await api_client.alpaca_orders(status)
    return orders or []

# Chatbot
@api_router.post("/chat")
async def chat(request: ChatRequest, auth: bool = Depends(verify_access)):
    """Chat with AI assistant"""
    session_id = request.session_id or str(uuid.uuid4())
    
    await db.chat_history.insert_one({
        "session_id": session_id,
        "role": "user",
        "content": request.message,
        "mode": request.mode,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    response = await get_chatbot_response(request.message, session_id, request.mode)
    
    await db.chat_history.insert_one({
        "session_id": session_id,
        "role": "assistant",
        "content": response,
        "mode": request.mode,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"response": response, "session_id": session_id}

# Search
@api_router.get("/search")
async def search_symbols(q: str = Query(..., min_length=1), auth: bool = Depends(verify_access)):
    """Search for symbols"""
    try:
        async with httpx.AsyncClient(timeout=10.0, headers={"apikey": config.FMP_API_KEY}) as client:
            resp = await client.get(
                f"https://financialmodelingprep.com/stable/search-symbol",
                params={"query": q, "limit": 10}
            )
            if resp.status_code == 200:
                return resp.json()
    except:
        pass
    return []

# Health check (no auth required)
@api_router.get("/")
async def root():
    return {"name": "ObaidTradez API", "version": "1.0.0", "status": "running"}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
