from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import asyncio
from functools import lru_cache
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# API Keys
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
FMP_API_KEY = os.environ.get('FMP_API_KEY')
FMP_BASE_URL = "https://financialmodelingprep.com/stable"

# Create the main app
app = FastAPI(title="AlphaLens API", description="AI-Powered Investment Research Platform")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===================== CACHE =====================
_cache: Dict[str, tuple] = {}
CACHE_TTL = 300  # 5 minutes

def get_cached(key: str) -> Optional[Any]:
    if key in _cache:
        data, timestamp = _cache[key]
        if datetime.now().timestamp() - timestamp < CACHE_TTL:
            return data
    return None

def set_cached(key: str, data: Any):
    _cache[key] = (data, datetime.now().timestamp())

# ===================== MODELS =====================

class StockScore(BaseModel):
    symbol: str
    company_name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    price: Optional[float] = None
    market_cap: Optional[float] = None
    
    # Component scores (0-100)
    overall_score: float = 0
    valuation_score: float = 0
    fundamentals_score: float = 0
    growth_score: float = 0
    momentum_score: float = 0
    technical_score: float = 0
    sentiment_score: float = 50  # Default neutral
    risk_score: float = 50  # Higher is lower risk
    
    # Classifications
    investment_signal: str = "Watchlist"  # Strong Candidate, Candidate, Watchlist, Avoid
    trading_signal: str = "Neutral"  # Breakout Candidate, Swing Candidate, Weak Setup, Avoid
    confidence: str = "Medium"  # High, Medium, Low
    
    # Key metrics
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    dividend_yield: Optional[float] = None
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    free_cash_flow: Optional[float] = None
    
    # Technical indicators
    rsi: Optional[float] = None
    price_to_sma50: Optional[float] = None
    price_to_sma200: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    distance_from_high: Optional[float] = None
    avg_volume: Optional[int] = None
    beta: Optional[float] = None
    
    # Analysis
    bull_case: List[str] = []
    bear_case: List[str] = []
    key_risks: List[str] = []
    recommendation_reason: str = ""
    strategy_fit: List[str] = []

class ScreenerRequest(BaseModel):
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    sector: Optional[str] = None
    min_pe: Optional[float] = None
    max_pe: Optional[float] = None
    min_dividend_yield: Optional[float] = None
    min_roe: Optional[float] = None
    min_revenue_growth: Optional[float] = None
    strategy: Optional[str] = None  # value, growth, momentum, swing
    limit: int = 20

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    recommendations: Optional[List[Dict]] = None

# ===================== FMP API CLIENT =====================

class FMPClient:
    def __init__(self):
        self.base_url = FMP_BASE_URL
        self.api_key = FMP_API_KEY
        self.headers = {"apikey": self.api_key}
    
    async def _get(self, endpoint: str, params: Dict = None) -> Optional[Any]:
        cache_key = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        cached = get_cached(cache_key)
        if cached:
            return cached
        
        try:
            params = params or {}
            async with httpx.AsyncClient(timeout=15.0, headers=self.headers) as client:
                response = await client.get(f"{self.base_url}/{endpoint}", params=params)
                if response.status_code == 200:
                    data = response.json()
                    set_cached(cache_key, data)
                    return data
                elif response.status_code == 429:
                    logger.warning("FMP rate limit hit")
                    return None
                else:
                    logger.error(f"FMP API error: {response.status_code} - {response.text[:200]}")
                    return None
        except Exception as e:
            logger.error(f"FMP request error: {e}")
            return None
    
    async def get_quote(self, symbol: str) -> Optional[Dict]:
        # New stable endpoint: /stable/quote?symbol=AAPL
        data = await self._get("quote", {"symbol": symbol})
        return data[0] if data and isinstance(data, list) and len(data) > 0 else data
    
    async def get_profile(self, symbol: str) -> Optional[Dict]:
        # New stable endpoint: /stable/profile?symbol=AAPL
        data = await self._get("profile", {"symbol": symbol})
        return data[0] if data and isinstance(data, list) and len(data) > 0 else data
    
    async def get_ratios_ttm(self, symbol: str) -> Optional[Dict]:
        # New stable endpoint: /stable/ratios-ttm?symbol=AAPL
        data = await self._get("ratios-ttm", {"symbol": symbol})
        return data[0] if data and isinstance(data, list) and len(data) > 0 else data
    
    async def get_key_metrics_ttm(self, symbol: str) -> Optional[Dict]:
        # New stable endpoint: /stable/key-metrics-ttm?symbol=AAPL
        data = await self._get("key-metrics-ttm", {"symbol": symbol})
        return data[0] if data and isinstance(data, list) and len(data) > 0 else data
    
    async def get_financial_growth(self, symbol: str) -> Optional[Dict]:
        # New stable endpoint: /stable/financial-growth?symbol=AAPL
        data = await self._get("financial-growth", {"symbol": symbol, "limit": 1})
        return data[0] if data and isinstance(data, list) and len(data) > 0 else data
    
    async def get_income_statement(self, symbol: str, limit: int = 4) -> Optional[List]:
        return await self._get("income-statement", {"symbol": symbol, "limit": limit})
    
    async def get_historical_price(self, symbol: str, days: int = 365) -> Optional[Dict]:
        # New endpoint: /stable/historical-price-eod/full?symbol=AAPL
        data = await self._get("historical-price-eod/full", {"symbol": symbol})
        if data and isinstance(data, list):
            return {"historical": data[:days]}
        return data
    
    async def get_stock_screener(self, params: Dict) -> Optional[List]:
        return await self._get("company-screener", params)
    
    async def get_stock_list(self) -> Optional[List]:
        return await self._get("stock-list")
    
    async def get_sector_performance(self) -> Optional[List]:
        return await self._get("sector-performance")
    
    async def get_stock_news(self, symbol: str, limit: int = 5) -> Optional[List]:
        # Try FMP news endpoint
        data = await self._get("stock-news", {"tickers": symbol, "limit": limit})
        return data if data else []

fmp = FMPClient()

# ===================== SCORING ENGINE =====================

class ScoringEngine:
    """Multi-factor scoring engine for stock analysis"""
    
    # Sector averages for peer comparison (simplified)
    SECTOR_BENCHMARKS = {
        "Technology": {"pe": 25, "pb": 5, "roe": 20, "growth": 15, "margin": 20},
        "Healthcare": {"pe": 20, "pb": 4, "roe": 15, "growth": 10, "margin": 15},
        "Financial Services": {"pe": 12, "pb": 1.2, "roe": 12, "growth": 5, "margin": 25},
        "Consumer Cyclical": {"pe": 18, "pb": 3, "roe": 15, "growth": 8, "margin": 10},
        "Consumer Defensive": {"pe": 22, "pb": 4, "roe": 18, "growth": 5, "margin": 12},
        "Industrials": {"pe": 18, "pb": 3, "roe": 15, "growth": 6, "margin": 10},
        "Energy": {"pe": 10, "pb": 1.5, "roe": 12, "growth": 5, "margin": 15},
        "Utilities": {"pe": 18, "pb": 1.8, "roe": 10, "growth": 3, "margin": 15},
        "Real Estate": {"pe": 35, "pb": 2, "roe": 8, "growth": 5, "margin": 30},
        "Communication Services": {"pe": 20, "pb": 3, "roe": 15, "growth": 10, "margin": 20},
        "Basic Materials": {"pe": 15, "pb": 2, "roe": 12, "growth": 5, "margin": 12},
        "default": {"pe": 18, "pb": 3, "roe": 15, "growth": 8, "margin": 15}
    }
    
    def get_benchmark(self, sector: str) -> Dict:
        return self.SECTOR_BENCHMARKS.get(sector, self.SECTOR_BENCHMARKS["default"])
    
    def score_valuation(self, data: Dict, sector: str) -> tuple:
        """Score valuation metrics (0-100). Higher = more attractive (cheaper)"""
        benchmark = self.get_benchmark(sector)
        score = 50  # Start neutral
        reasons = []
        
        pe = data.get('peRatioTTM') or data.get('pe')
        if pe and pe > 0:
            pe_ratio = benchmark['pe'] / pe if pe > 0 else 1
            if pe_ratio > 1.5:
                score += 20
                reasons.append(f"P/E of {pe:.1f} is significantly below sector average")
            elif pe_ratio > 1.1:
                score += 10
                reasons.append(f"P/E of {pe:.1f} is below sector average")
            elif pe_ratio < 0.7:
                score -= 15
                reasons.append(f"P/E of {pe:.1f} suggests premium valuation")
        
        pb = data.get('priceToBookRatioTTM') or data.get('pb')
        if pb and pb > 0:
            pb_ratio = benchmark['pb'] / pb if pb > 0 else 1
            if pb_ratio > 1.5:
                score += 15
                reasons.append(f"P/B ratio of {pb:.2f} indicates undervaluation")
            elif pb_ratio < 0.5:
                score -= 10
        
        ev_ebitda = data.get('enterpriseValueOverEBITDATTM')
        if ev_ebitda and 0 < ev_ebitda < 50:
            if ev_ebitda < 8:
                score += 15
                reasons.append(f"EV/EBITDA of {ev_ebitda:.1f} is attractive")
            elif ev_ebitda < 12:
                score += 5
            elif ev_ebitda > 20:
                score -= 10
                reasons.append(f"EV/EBITDA of {ev_ebitda:.1f} is elevated")
        
        peg = data.get('pegRatioTTM')
        if peg and 0 < peg < 5:
            if peg < 1:
                score += 15
                reasons.append(f"PEG ratio of {peg:.2f} suggests growth at reasonable price")
            elif peg < 1.5:
                score += 5
            elif peg > 2.5:
                score -= 10
        
        return max(0, min(100, score)), reasons
    
    def score_fundamentals(self, data: Dict, sector: str) -> tuple:
        """Score financial strength (0-100). Higher = stronger"""
        benchmark = self.get_benchmark(sector)
        score = 50
        reasons = []
        
        roe = data.get('returnOnEquityTTM') or data.get('roe')
        if roe:
            roe_pct = roe * 100 if roe < 1 else roe
            if roe_pct > benchmark['roe'] * 1.5:
                score += 20
                reasons.append(f"ROE of {roe_pct:.1f}% is excellent")
            elif roe_pct > benchmark['roe']:
                score += 10
                reasons.append(f"ROE of {roe_pct:.1f}% is above average")
            elif roe_pct < benchmark['roe'] * 0.5:
                score -= 15
                reasons.append(f"ROE of {roe_pct:.1f}% is weak")
        
        current = data.get('currentRatioTTM')
        if current:
            if current > 2:
                score += 10
                reasons.append(f"Strong liquidity (current ratio: {current:.2f})")
            elif current > 1.5:
                score += 5
            elif current < 1:
                score -= 15
                reasons.append(f"Liquidity concern (current ratio: {current:.2f})")
        
        de = data.get('debtEquityRatioTTM') or data.get('debtToEquity')
        if de is not None:
            if de < 0.3:
                score += 15
                reasons.append(f"Low debt (D/E: {de:.2f})")
            elif de < 0.8:
                score += 5
            elif de > 2:
                score -= 15
                reasons.append(f"High leverage (D/E: {de:.2f})")
        
        net_margin = data.get('netProfitMarginTTM')
        if net_margin:
            margin_pct = net_margin * 100 if net_margin < 1 else net_margin
            if margin_pct > benchmark['margin'] * 1.5:
                score += 10
                reasons.append(f"Excellent margins ({margin_pct:.1f}%)")
            elif margin_pct > benchmark['margin']:
                score += 5
        
        return max(0, min(100, score)), reasons
    
    def score_growth(self, data: Dict, sector: str) -> tuple:
        """Score growth metrics (0-100). Higher = stronger growth"""
        benchmark = self.get_benchmark(sector)
        score = 50
        reasons = []
        
        rev_growth = data.get('revenueGrowth')
        if rev_growth is not None:
            growth_pct = rev_growth * 100 if abs(rev_growth) < 1 else rev_growth
            if growth_pct > 20:
                score += 25
                reasons.append(f"Strong revenue growth ({growth_pct:.1f}%)")
            elif growth_pct > 10:
                score += 15
                reasons.append(f"Solid revenue growth ({growth_pct:.1f}%)")
            elif growth_pct > 0:
                score += 5
            elif growth_pct < -10:
                score -= 20
                reasons.append(f"Revenue declining ({growth_pct:.1f}%)")
        
        eps_growth = data.get('epsgrowth') or data.get('epsGrowth')
        if eps_growth is not None:
            eps_pct = eps_growth * 100 if abs(eps_growth) < 1 else eps_growth
            if eps_pct > 25:
                score += 20
                reasons.append(f"Strong earnings growth ({eps_pct:.1f}%)")
            elif eps_pct > 10:
                score += 10
            elif eps_pct < -15:
                score -= 15
                reasons.append(f"Earnings declining ({eps_pct:.1f}%)")
        
        return max(0, min(100, score)), reasons
    
    def score_momentum(self, quote: Dict, historical: List) -> tuple:
        """Score price momentum (0-100)"""
        score = 50
        reasons = []
        
        if not quote:
            return score, reasons
        
        price = quote.get('price', 0)
        sma50 = quote.get('priceAvg50', 0)
        sma200 = quote.get('priceAvg200', 0)
        
        if price and sma50 and sma50 > 0:
            ratio = price / sma50
            if ratio > 1.05:
                score += 15
                reasons.append("Price above 50-day moving average")
            elif ratio < 0.95:
                score -= 10
                reasons.append("Price below 50-day moving average")
        
        if price and sma200 and sma200 > 0:
            ratio = price / sma200
            if ratio > 1.1:
                score += 15
                reasons.append("Strong uptrend (above 200-day MA)")
            elif ratio < 0.9:
                score -= 10
                reasons.append("Downtrend (below 200-day MA)")
        
        # Golden cross
        if sma50 and sma200 and sma50 > sma200:
            score += 10
            reasons.append("Bullish moving average alignment")
        
        # 52-week position
        high_52 = quote.get('yearHigh', 0)
        low_52 = quote.get('yearLow', 0)
        if price and high_52 and low_52 and high_52 > low_52:
            position = (price - low_52) / (high_52 - low_52)
            if position > 0.8:
                score += 10
                reasons.append("Near 52-week high (momentum strength)")
            elif position < 0.2:
                score -= 5
                reasons.append("Near 52-week low")
        
        return max(0, min(100, score)), reasons
    
    def score_technical(self, quote: Dict, historical: List) -> tuple:
        """Score technical setup for trading (0-100)"""
        score = 50
        reasons = []
        
        if not quote:
            return score, reasons
        
        change_pct = quote.get('changesPercentage', 0)
        volume = quote.get('volume', 0)
        avg_volume = quote.get('avgVolume', 1)
        
        # Volume analysis
        if volume and avg_volume:
            vol_ratio = volume / avg_volume if avg_volume > 0 else 1
            if vol_ratio > 2:
                score += 15
                reasons.append(f"High volume ({vol_ratio:.1f}x average)")
            elif vol_ratio > 1.5:
                score += 5
        
        # Recent performance
        if change_pct:
            if 1 < change_pct < 5:
                score += 10
                reasons.append("Positive momentum today")
            elif change_pct > 5:
                score += 5
                reasons.append("Strong move (potential overextension)")
            elif change_pct < -3:
                score -= 10
        
        return max(0, min(100, score)), reasons
    
    def calculate_risk_score(self, data: Dict, quote: Dict) -> tuple:
        """Calculate risk score (0-100). Higher = LOWER risk"""
        score = 50
        reasons = []
        
        beta = quote.get('beta', 1) if quote else 1
        if beta:
            if beta < 0.8:
                score += 15
                reasons.append(f"Low volatility (beta: {beta:.2f})")
            elif beta > 1.5:
                score -= 15
                reasons.append(f"High volatility (beta: {beta:.2f})")
        
        de = data.get('debtEquityRatioTTM', 0)
        if de and de > 2:
            score -= 20
            reasons.append("High debt levels increase risk")
        
        market_cap = quote.get('marketCap', 0) if quote else 0
        if market_cap:
            if market_cap > 100e9:
                score += 10
                reasons.append("Large cap stability")
            elif market_cap < 2e9:
                score -= 10
                reasons.append("Small cap volatility risk")
        
        return max(0, min(100, score)), reasons
    
    def classify_investment_signal(self, overall_score: float, confidence: str) -> str:
        """Classify as investment signal"""
        if overall_score >= 75 and confidence in ["High", "Medium"]:
            return "Strong Candidate"
        elif overall_score >= 60:
            return "Candidate"
        elif overall_score >= 40:
            return "Watchlist"
        else:
            return "Avoid"
    
    def classify_trading_signal(self, momentum: float, technical: float) -> str:
        """Classify for short-term trading"""
        combined = (momentum + technical) / 2
        if combined >= 70:
            return "Breakout Candidate"
        elif combined >= 55:
            return "Swing Candidate"
        elif combined >= 40:
            return "Weak Setup"
        else:
            return "Avoid"
    
    def determine_confidence(self, data_completeness: float, score_variance: float) -> str:
        """Determine confidence level"""
        if data_completeness > 0.8 and score_variance < 15:
            return "High"
        elif data_completeness > 0.6:
            return "Medium"
        else:
            return "Low"
    
    def get_strategy_fit(self, scores: Dict) -> List[str]:
        """Determine which strategies the stock fits"""
        fits = []
        if scores['valuation'] >= 65 and scores['fundamentals'] >= 55:
            fits.append("Value")
        if scores['growth'] >= 65:
            fits.append("Growth")
        if scores['momentum'] >= 65 and scores['technical'] >= 55:
            fits.append("Momentum")
        if scores['technical'] >= 60 and scores['momentum'] >= 55:
            fits.append("Swing Trading")
        if scores['valuation'] >= 55 and scores['growth'] >= 55:
            fits.append("GARP")
        if scores['fundamentals'] >= 70 and scores['risk'] >= 60:
            fits.append("Quality")
        return fits
    
    def generate_recommendation_reason(self, symbol: str, scores: Dict, bull: List, bear: List) -> str:
        """Generate a clear recommendation reason"""
        overall = scores['overall']
        top_strength = max(scores.items(), key=lambda x: x[1] if x[0] != 'overall' else 0)
        
        if overall >= 70:
            return f"{symbol} ranks highly ({overall:.0f}/100) with particular strength in {top_strength[0]} ({top_strength[1]:.0f}). Key positives: {'; '.join(bull[:2]) if bull else 'Strong fundamentals'}."
        elif overall >= 55:
            return f"{symbol} shows moderate appeal ({overall:.0f}/100). Strengths in {top_strength[0]}, but mixed signals warrant caution. {bear[0] if bear else ''}"
        else:
            return f"{symbol} scores below average ({overall:.0f}/100). Primary concerns: {'; '.join(bear[:2]) if bear else 'Weak metrics'}. Consider avoiding or deeper research."

scoring_engine = ScoringEngine()

# ===================== STOCK ANALYZER =====================

async def analyze_stock(symbol: str) -> Optional[StockScore]:
    """Comprehensive stock analysis with scoring"""
    try:
        # Fetch all data in parallel
        quote, profile, ratios, metrics, growth = await asyncio.gather(
            fmp.get_quote(symbol),
            fmp.get_profile(symbol),
            fmp.get_ratios_ttm(symbol),
            fmp.get_key_metrics_ttm(symbol),
            fmp.get_financial_growth(symbol),
            return_exceptions=True
        )
        
        # Handle exceptions
        quote = quote if not isinstance(quote, Exception) else None
        profile = profile if not isinstance(profile, Exception) else None
        ratios = ratios if not isinstance(ratios, Exception) else None
        metrics = metrics if not isinstance(metrics, Exception) else None
        growth = growth if not isinstance(growth, Exception) else None
        
        if not quote and not profile:
            return None
        
        # Combine data
        combined = {}
        if ratios:
            combined.update(ratios)
        if metrics:
            combined.update(metrics)
        if growth:
            combined.update(growth)
        if quote:
            combined.update(quote)
        if profile:
            combined.update(profile)
        
        sector = profile.get('sector', 'default') if profile else 'default'
        
        # Calculate scores
        val_score, val_reasons = scoring_engine.score_valuation(combined, sector)
        fund_score, fund_reasons = scoring_engine.score_fundamentals(combined, sector)
        growth_score, growth_reasons = scoring_engine.score_growth(combined, sector)
        mom_score, mom_reasons = scoring_engine.score_momentum(quote, [])
        tech_score, tech_reasons = scoring_engine.score_technical(quote, [])
        risk_score, risk_reasons = scoring_engine.calculate_risk_score(combined, quote)
        
        # Calculate overall (weighted average)
        scores = {
            'valuation': val_score,
            'fundamentals': fund_score,
            'growth': growth_score,
            'momentum': mom_score,
            'technical': tech_score,
            'risk': risk_score,
            'sentiment': 50  # Default, would come from news analysis
        }
        
        # Weighted overall score
        overall = (
            val_score * 0.20 +
            fund_score * 0.20 +
            growth_score * 0.15 +
            mom_score * 0.15 +
            tech_score * 0.10 +
            risk_score * 0.10 +
            50 * 0.10  # sentiment placeholder
        )
        scores['overall'] = overall
        
        # Build bull/bear cases
        bull_case = val_reasons + fund_reasons + growth_reasons + mom_reasons
        bull_case = [r for r in bull_case if not any(w in r.lower() for w in ['weak', 'concern', 'declining', 'below', 'high debt', 'elevated'])]
        
        bear_case = [r for r in val_reasons + fund_reasons + growth_reasons + risk_reasons 
                     if any(w in r.lower() for w in ['weak', 'concern', 'declining', 'below', 'high', 'elevated', 'risk'])]
        
        # Key risks
        risks = []
        if risk_score < 40:
            risks.append("Higher than average volatility and risk profile")
        if combined.get('debtEquityRatioTTM', 0) > 1.5:
            risks.append("Elevated debt levels")
        if val_score < 40:
            risks.append("Valuation appears stretched")
        if growth_score < 40:
            risks.append("Growth metrics are weak")
        
        # Confidence
        data_fields = [quote, profile, ratios, metrics, growth]
        data_completeness = sum(1 for d in data_fields if d) / len(data_fields)
        score_values = [val_score, fund_score, growth_score, mom_score, tech_score]
        score_variance = max(score_values) - min(score_values)
        confidence = scoring_engine.determine_confidence(data_completeness, score_variance)
        
        # Classifications
        investment_signal = scoring_engine.classify_investment_signal(overall, confidence)
        trading_signal = scoring_engine.classify_trading_signal(mom_score, tech_score)
        strategy_fit = scoring_engine.get_strategy_fit(scores)
        
        # Recommendation reason
        recommendation = scoring_engine.generate_recommendation_reason(symbol, scores, bull_case[:5], bear_case[:5])
        
        return StockScore(
            symbol=symbol,
            company_name=profile.get('companyName', symbol) if profile else symbol,
            sector=sector,
            industry=profile.get('industry') if profile else None,
            price=quote.get('price') if quote else None,
            market_cap=quote.get('marketCap') if quote else None,
            
            overall_score=round(overall, 1),
            valuation_score=round(val_score, 1),
            fundamentals_score=round(fund_score, 1),
            growth_score=round(growth_score, 1),
            momentum_score=round(mom_score, 1),
            technical_score=round(tech_score, 1),
            sentiment_score=50,
            risk_score=round(risk_score, 1),
            
            investment_signal=investment_signal,
            trading_signal=trading_signal,
            confidence=confidence,
            
            pe_ratio=combined.get('peRatioTTM'),
            forward_pe=combined.get('forwardPE'),
            peg_ratio=combined.get('pegRatioTTM'),
            pb_ratio=combined.get('priceToBookRatioTTM'),
            ev_ebitda=combined.get('enterpriseValueOverEBITDATTM'),
            dividend_yield=combined.get('dividendYield'),
            revenue_growth=combined.get('revenueGrowth'),
            earnings_growth=combined.get('epsgrowth'),
            roe=combined.get('returnOnEquityTTM'),
            roa=combined.get('returnOnAssetsTTM'),
            debt_to_equity=combined.get('debtEquityRatioTTM'),
            current_ratio=combined.get('currentRatioTTM'),
            gross_margin=combined.get('grossProfitMarginTTM'),
            operating_margin=combined.get('operatingProfitMarginTTM'),
            net_margin=combined.get('netProfitMarginTTM'),
            free_cash_flow=combined.get('freeCashFlowPerShareTTM'),
            
            rsi=None,  # Would need technical API
            price_to_sma50=(quote.get('price', 0) / quote.get('priceAvg50', 1) - 1) * 100 if quote and quote.get('priceAvg50') else None,
            price_to_sma200=(quote.get('price', 0) / quote.get('priceAvg200', 1) - 1) * 100 if quote and quote.get('priceAvg200') else None,
            week_52_high=quote.get('yearHigh') if quote else None,
            week_52_low=quote.get('yearLow') if quote else None,
            distance_from_high=((quote.get('price', 0) / quote.get('yearHigh', 1)) - 1) * 100 if quote and quote.get('yearHigh') else None,
            avg_volume=quote.get('avgVolume') if quote else None,
            beta=profile.get('beta') if profile else None,
            
            bull_case=bull_case[:5],
            bear_case=bear_case[:5],
            key_risks=risks[:5],
            recommendation_reason=recommendation,
            strategy_fit=strategy_fit
        )
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        return None

# ===================== AI CHATBOT =====================

async def get_alphalens_response(message: str, session_id: str, context: Dict = None) -> tuple:
    """Get AI response with grounded financial reasoning"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    system_message = """You are AlphaLens AI, an expert investment research assistant. You provide actionable stock recommendations with clear, evidence-based reasoning.

YOUR ROLE:
- Generate ranked stock recommendations based on fundamentals, valuation, technicals, and momentum
- Explain WHY each stock ranks well or poorly using specific metrics
- Provide bull case, bear case, and key risks for every suggestion
- Be direct and recommendation-oriented, not just informational

COMMUNICATION STYLE:
- "This stock ranks highly because its P/E of 12 is below the sector average of 18, ROE is strong at 22%, and price momentum is positive."
- "Despite the low P/E, I'd avoid this stock because revenue is declining 8% YoY and debt is elevated."
- "This is a Watchlist candidate - the setup isn't confirmed yet, but fundamentals are improving."

SCORING SYSTEM (0-100):
- Valuation Score: P/E, P/B, EV/EBITDA, PEG vs sector peers
- Fundamentals Score: ROE, margins, debt levels, cash flow
- Growth Score: Revenue growth, earnings growth
- Momentum Score: Price vs 50/200-day MA, 52-week position
- Technical Score: Volume, recent price action
- Risk Score: Beta, leverage, market cap stability

CLASSIFICATION:
Investment: Strong Candidate | Candidate | Watchlist | Avoid
Trading: Breakout Candidate | Swing Candidate | Weak Setup | Avoid

RULES:
1. Never recommend based on one metric alone
2. Always include bull AND bear case
3. State confidence level (High/Medium/Low)
4. Mention when data is incomplete
5. Include disclaimer: "This is for research purposes only, not financial advice"
6. Be specific with numbers: "P/E of 15 vs sector 20" not "cheap"

When asked for recommendations, structure your response:
1. Top picks with scores
2. Why each ranks well (specific metrics)
3. Key risks
4. Trading vs investing suitability"""

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=system_message
        ).with_model("openai", "gpt-5.2")
        
        # Add context if available
        enhanced_message = message
        if context and context.get('stock_data'):
            enhanced_message += f"\n\nContext - Current stock data:\n{json.dumps(context['stock_data'], indent=2)}"
        
        user_message = UserMessage(text=enhanced_message)
        response = await chat.send_message(user_message)
        return response, None
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return f"I apologize, but I encountered an error. Please try again. Error: {str(e)}", None

# ===================== ROUTES =====================

@api_router.get("/")
async def root():
    return {"message": "AlphaLens API - AI-Powered Investment Research", "version": "1.0.0"}

@api_router.get("/stock/{symbol}", response_model=StockScore)
async def get_stock_analysis(symbol: str):
    """Get comprehensive stock analysis with scoring"""
    result = await analyze_stock(symbol.upper())
    if not result:
        raise HTTPException(status_code=404, detail=f"Unable to analyze {symbol}. Data may be unavailable.")
    return result

@api_router.get("/stock/{symbol}/quote")
async def get_stock_quote(symbol: str):
    """Get real-time stock quote"""
    quote = await fmp.get_quote(symbol.upper())
    if not quote:
        raise HTTPException(status_code=404, detail=f"Quote not found for {symbol}")
    return quote

@api_router.get("/stock/{symbol}/profile")
async def get_stock_profile(symbol: str):
    """Get company profile"""
    profile = await fmp.get_profile(symbol.upper())
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile not found for {symbol}")
    return profile

@api_router.get("/stock/{symbol}/historical")
async def get_stock_historical(symbol: str, days: int = Query(365, ge=30, le=1825)):
    """Get historical price data"""
    data = await fmp.get_historical_price(symbol.upper(), days)
    if not data:
        raise HTTPException(status_code=404, detail=f"Historical data not found for {symbol}")
    return data

@api_router.get("/stock/{symbol}/news")
async def get_stock_news(symbol: str, limit: int = Query(10, ge=1, le=50)):
    """Get recent news for a stock"""
    news = await fmp.get_stock_news(symbol.upper(), limit)
    return news or []

@api_router.post("/screener")
async def screen_stocks(request: ScreenerRequest):
    """Screen stocks based on criteria"""
    params = {}
    if request.min_market_cap:
        params['marketCapMoreThan'] = request.min_market_cap
    if request.max_market_cap:
        params['marketCapLowerThan'] = request.max_market_cap
    if request.sector:
        params['sector'] = request.sector
    params['limit'] = min(request.limit, 50)
    params['exchange'] = 'NYSE,NASDAQ'
    
    stocks = await fmp.get_stock_screener(params)
    if not stocks:
        return []
    
    # Analyze top stocks
    analyzed = []
    for stock in stocks[:request.limit]:
        analysis = await analyze_stock(stock['symbol'])
        if analysis:
            analyzed.append(analysis)
    
    # Sort by overall score
    analyzed.sort(key=lambda x: x.overall_score, reverse=True)
    return analyzed

@api_router.get("/rankings/{strategy}")
async def get_strategy_rankings(
    strategy: str,
    limit: int = Query(10, ge=5, le=25)
):
    """Get top ranked stocks for a specific strategy"""
    # Define strategy-specific screener params
    strategy_params = {
        "value": {"priceEarningsRatioLowerThan": 20, "debtEquityRatioLowerThan": 1},
        "growth": {"revenueGrowthMoreThan": 0.1},
        "momentum": {},
        "swing": {},
        "quality": {"returnOnEquityMoreThan": 0.15}
    }
    
    params = strategy_params.get(strategy, {})
    params['marketCapMoreThan'] = 10e9  # Large cap for reliability
    params['limit'] = 30
    params['exchange'] = 'NYSE,NASDAQ'
    
    stocks = await fmp.get_stock_screener(params)
    if not stocks:
        # Fallback to popular stocks
        stocks = [{"symbol": s} for s in ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "JPM", "V", "JNJ", "PG"]]
    
    # Analyze and filter by strategy
    analyzed = []
    for stock in stocks[:20]:
        analysis = await analyze_stock(stock['symbol'])
        if analysis and strategy in [s.lower() for s in analysis.strategy_fit]:
            analyzed.append(analysis)
        elif analysis and len(analyzed) < limit:
            analyzed.append(analysis)
    
    # Sort by relevant score
    sort_key = {
        "value": lambda x: x.valuation_score,
        "growth": lambda x: x.growth_score,
        "momentum": lambda x: x.momentum_score,
        "swing": lambda x: x.technical_score,
        "quality": lambda x: x.fundamentals_score
    }.get(strategy, lambda x: x.overall_score)
    
    analyzed.sort(key=sort_key, reverse=True)
    return analyzed[:limit]

@api_router.get("/recommendations")
async def get_top_recommendations(limit: int = Query(10, ge=5, le=20)):
    """Get top overall stock recommendations"""
    # Get a diverse set of stocks
    stocks = [{"symbol": s} for s in [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM", "V", "JNJ",
        "PG", "UNH", "HD", "MA", "DIS", "ADBE", "CRM", "NFLX", "COST", "PEP"
    ]]
    
    analyzed = []
    for stock in stocks:
        analysis = await analyze_stock(stock['symbol'])
        if analysis:
            analyzed.append(analysis)
    
    analyzed.sort(key=lambda x: x.overall_score, reverse=True)
    return analyzed[:limit]

@api_router.post("/compare")
async def compare_stocks(symbols: List[str]):
    """Compare multiple stocks side by side"""
    if len(symbols) < 2 or len(symbols) > 5:
        raise HTTPException(status_code=400, detail="Compare 2-5 stocks")
    
    analyses = []
    for symbol in symbols:
        analysis = await analyze_stock(symbol.upper())
        if analysis:
            analyses.append(analysis)
    
    if len(analyses) < 2:
        raise HTTPException(status_code=404, detail="Could not analyze enough stocks")
    
    # Sort by overall score
    analyses.sort(key=lambda x: x.overall_score, reverse=True)
    
    return {
        "stocks": analyses,
        "best_overall": analyses[0].symbol,
        "best_value": max(analyses, key=lambda x: x.valuation_score).symbol,
        "best_growth": max(analyses, key=lambda x: x.growth_score).symbol,
        "best_momentum": max(analyses, key=lambda x: x.momentum_score).symbol,
        "lowest_risk": max(analyses, key=lambda x: x.risk_score).symbol
    }

@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_alphalens(request: ChatRequest):
    """Chat with AlphaLens AI assistant"""
    session_id = request.session_id or str(uuid.uuid4())
    
    # Store user message
    await db.chat_history.insert_one({
        "session_id": session_id,
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Get AI response
    response, recommendations = await get_alphalens_response(
        request.message, 
        session_id,
        request.context
    )
    
    # Store AI response
    await db.chat_history.insert_one({
        "session_id": session_id,
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return ChatResponse(
        response=response, 
        session_id=session_id,
        recommendations=recommendations
    )

@api_router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    messages = await db.chat_history.find(
        {"session_id": session_id}, 
        {"_id": 0, "session_id": 0}
    ).sort("timestamp", 1).to_list(100)
    return messages

@api_router.get("/sectors")
async def get_sector_performance():
    """Get sector performance data"""
    data = await fmp.get_sector_performance()
    return data or []

@api_router.get("/search")
async def search_stocks(q: str = Query(..., min_length=1)):
    """Search for stocks by name or symbol"""
    try:
        async with httpx.AsyncClient(timeout=10.0, headers={"apikey": FMP_API_KEY}) as client:
            # Try symbol search first
            response = await client.get(
                f"{FMP_BASE_URL}/search-symbol",
                params={"query": q, "limit": 10}
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Search error: {e}")
    return []

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
