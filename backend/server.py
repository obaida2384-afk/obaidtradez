"""
ObaidTradez - AI Trading & Investing Platform
Backend Server with Multi-API Integration and Broad Universe Coverage
"""

from fastapi import FastAPI, APIRouter, HTTPException, Query, Depends, Header, BackgroundTasks
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

# Import enhanced investment engine
from enhanced_investment_engine import EnhancedInvestmentEngine, convert_to_legacy_format

# Import AI trading system
from ai_trading_system import (
    AutoTradeOrchestrator, AutoTradeSettings, StockClassifier,
    ConfidenceScoringEngine, MarketRegimeDetector
)

# Import enhanced news engine
from news_sentiment_engine import EnhancedNewsSentimentEngine

# Import auto-trade scheduler
from auto_trade_scheduler import AutoTradeScheduler
from live_price_engine import LivePriceEngine
from live_reeval_engine import LiveReEvaluationEngine
from price_integrity import PriceIntegrityService
from reeval_verifier import ReEvalVerifier
from starlette.responses import StreamingResponse
from top_movers_scanner import TopMoversScanner
from performance_tracker import PerformanceTracker
from long_term_engine import LongTermInvestingEngine
from execution_transparency import ExecutionTransparencyTracker

# ===================== CONFIGURATION =====================
class Config:
    MONGO_URL = os.environ['MONGO_URL']
    DB_NAME = os.environ.get('DB_NAME', 'obaidtradez')
    ACCESS_CODE = os.environ.get('ACCESS_CODE_HASH', '')
    ACCESS_USERNAME = os.environ.get('ACCESS_USERNAME', '')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    
    # Financial APIs
    FMP_API_KEY = os.environ.get('FMP_API_KEY')
    ALPHA_VANTAGE_KEY = os.environ.get('ALPHA_VANTAGE_KEY')
    NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
    POLYGON_API_KEY = os.environ.get('POLYGON_API_KEY')
    FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY')
    
    # Alpaca
    ALPACA_API_KEY = os.environ.get('ALPACA_API_KEY')
    ALPACA_SECRET_KEY = os.environ.get('ALPACA_SECRET_KEY')
    # Store base URL without /v2, add it in API calls
    _raw_base_url = os.environ.get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets/v2')
    ALPACA_BASE_URL = _raw_base_url.rstrip('/').replace('/v2', '')

config = Config()

# MongoDB
client = AsyncIOMotorClient(config.MONGO_URL)
db = client[config.DB_NAME]

# Enhanced News Engine (initialized early for route handlers)
enhanced_news_engine = EnhancedNewsSentimentEngine(db)

# FastAPI App
app = FastAPI(title="ObaidTradez API", description="AI Trading & Investing Platform")
api_router = APIRouter(prefix="/api")

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===================== CACHE =====================
_cache: Dict[str, tuple] = {}
CACHE_TTL = 120  # 2 minutes
UNIVERSE_CACHE_TTL = 3600  # 1 hour for universe
SIGNAL_CACHE_TTL = 900  # 15 minutes for signals

def get_cached(key: str, ttl: int = CACHE_TTL) -> Optional[Any]:
    if key in _cache:
        data, ts = _cache[key]
        if datetime.now().timestamp() - ts < ttl:
            return data
    return None

def set_cached(key: str, data: Any, ttl: int = None):
    _cache[key] = (data, datetime.now().timestamp())

# ===================== MODELS =====================

class AccessRequest(BaseModel):
    username: Optional[str] = None
    code: str

class AccessResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str

class TradingSignal(BaseModel):
    symbol: str
    name: str
    price: Optional[float] = None
    signal: str
    confidence: float
    entry_zone: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[str] = None
    risk_reward: Optional[str] = None
    reasoning: str
    indicators: Dict[str, Any] = {}
    category: str
    # News sentiment fields
    news_sentiment: Optional[str] = None  # Bullish, Bearish, Neutral, etc.
    news_impact: Optional[int] = None  # -10 to +10
    news_headlines: Optional[List[Dict]] = None  # Recent headlines with sentiment

class InvestmentSignal(BaseModel):
    symbol: str
    name: str
    price: Optional[float] = None
    signal: str
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
    category: str
    # Extended fields for universe
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    market_cap: Optional[float] = None
    market_cap_label: Optional[str] = None
    data_completeness: float = 100.0
    last_updated: Optional[str] = None

class UniverseStock(BaseModel):
    symbol: str
    name: str
    exchange: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    market_cap: Optional[float] = None
    is_etf: bool = False
    is_actively_trading: bool = True

class InvestmentFilters(BaseModel):
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    sectors: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    min_valuation_score: Optional[float] = None
    min_quality_score: Optional[float] = None
    min_growth_score: Optional[float] = None
    min_overall_score: Optional[float] = None
    signals: Optional[List[str]] = None
    categories: Optional[List[str]] = None

class NewsItem(BaseModel):
    title: str
    source: str
    url: str
    published: str
    sentiment: str
    sentiment_score: float
    summary: Optional[str] = None
    symbols: List[str] = []

class RiskSettings(BaseModel):
    max_position_size: float = 0.05
    max_daily_loss: float = 0.02
    max_weekly_loss: float = 0.05
    max_drawdown: float = 0.10
    min_confidence: float = 0.6
    cash_buffer: float = 0.10
    sector_limit: float = 0.25

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    mode: str = "general"

# ===================== ACCESS CONTROL =====================

_valid_tokens: Dict[str, datetime] = {}

def generate_token() -> str:
    return secrets.token_urlsafe(32)

def validate_access_code(code: str, username: str = None) -> bool:
    password_ok = code == config.ACCESS_CODE
    if config.ACCESS_USERNAME:
        return password_ok and username == config.ACCESS_USERNAME
    return password_ok

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
        self.alpaca_headers = {
            "APCA-API-KEY-ID": config.ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": config.ALPACA_SECRET_KEY
        }
    
    async def _request(self, url: str, headers: Dict = None, params: Dict = None, timeout: float = 15.0) -> Optional[Any]:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    return resp.json()
                logger.warning(f"API error {resp.status_code}: {url}")
        except Exception as e:
            logger.error(f"Request error: {e}")
        return None
    
    # ============ UNIVERSE LOADING METHODS ============
    
    async def fmp_stock_list(self) -> Optional[List[Dict]]:
        """Get all tradable stocks from FMP"""
        cache_key = "fmp_stock_list"
        cached = get_cached(cache_key, UNIVERSE_CACHE_TTL)
        if cached:
            return cached
        
        data = await self._request(
            f"{self.fmp_url}/stock-list",
            headers={"apikey": config.FMP_API_KEY},
            timeout=30.0
        )
        if data:
            set_cached(cache_key, data)
        return data
    
    async def fmp_tradable_list(self) -> Optional[List[Dict]]:
        """Get actively tradable stocks"""
        cache_key = "fmp_tradable_list"
        cached = get_cached(cache_key, UNIVERSE_CACHE_TTL)
        if cached:
            return cached
        
        data = await self._request(
            f"{self.fmp_url}/available-traded/list",
            headers={"apikey": config.FMP_API_KEY},
            timeout=30.0
        )
        if data:
            set_cached(cache_key, data)
        return data
    
    async def fmp_etf_list(self) -> Optional[List[Dict]]:
        """Get ETF list"""
        cache_key = "fmp_etf_list"
        cached = get_cached(cache_key, UNIVERSE_CACHE_TTL)
        if cached:
            return cached
        
        data = await self._request(
            f"{self.fmp_url}/etf-list",
            headers={"apikey": config.FMP_API_KEY},
            timeout=30.0
        )
        if data:
            set_cached(cache_key, data)
        return data
    
    async def fmp_screener(self, params: Dict) -> Optional[List[Dict]]:
        """Use FMP stock screener for targeted filtering"""
        return await self._request(
            f"{self.fmp_url}/stock-screener",
            headers={"apikey": config.FMP_API_KEY},
            params=params,
            timeout=30.0
        )
    
    async def fmp_batch_quote(self, symbols: List[str]) -> Optional[List[Dict]]:
        """Get batch quotes for multiple symbols"""
        if not symbols:
            return []
        symbols_str = ",".join(symbols[:50])  # FMP limit
        return await self._request(
            f"{self.fmp_url}/quote",
            headers={"apikey": config.FMP_API_KEY},
            params={"symbol": symbols_str}
        )
    
    # ============ EXISTING METHODS ============
    
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
    
    async def fmp_historical(self, symbol: str, days: int = 200) -> Optional[List]:
        """Get historical price data"""
        data = await self._request(
            f"{self.fmp_url}/historical-price-eod/full",
            headers={"apikey": config.FMP_API_KEY},
            params={"symbol": symbol, "limit": days}
        )
        return data if isinstance(data, list) else None
    
    async def fmp_historical_30yr(self, symbol: str) -> Optional[List]:
        """Get up to 30 years of historical price data by fetching in chunks"""
        try:
            from datetime import datetime, timedelta
            today = datetime.now().strftime("%Y-%m-%d")
            mid_date = (datetime.now() - timedelta(days=7300)).strftime("%Y-%m-%d")  # ~20yr ago
            start_date = (datetime.now() - timedelta(days=11000)).strftime("%Y-%m-%d")  # ~30yr ago
            
            # Fetch recent chunk (last ~20 years) and older chunk in parallel
            recent, older = await asyncio.gather(
                self._request(
                    f"{self.fmp_url}/historical-price-eod/full",
                    headers={"apikey": config.FMP_API_KEY},
                    params={"symbol": symbol, "from": mid_date, "to": today}
                ),
                self._request(
                    f"{self.fmp_url}/historical-price-eod/full",
                    headers={"apikey": config.FMP_API_KEY},
                    params={"symbol": symbol, "from": start_date, "to": mid_date}
                ),
                return_exceptions=True
            )
            
            recent = recent if isinstance(recent, list) else []
            older = older if isinstance(older, list) else []
            
            # Merge: recent is newest-first, older is newest-first
            # Combine: recent (newest) + older (older data)
            combined = recent + older
            
            if not combined:
                # Fallback to single call
                data = await self._request(
                    f"{self.fmp_url}/historical-price-eod/full",
                    headers={"apikey": config.FMP_API_KEY},
                    params={"symbol": symbol, "from": start_date, "to": today}
                )
                return data if isinstance(data, list) else None
            
            return combined
        except Exception as e:
            logger.error(f"30yr historical fetch error for {symbol}: {e}")
            return None
    
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
    
    # FMP News Methods
    async def fmp_news(self, symbol: str, limit: int = 10) -> Optional[List]:
        """Get FMP stock news for a symbol"""
        return await self._request(
            f"{self.fmp_url}/stock-news",
            headers={"apikey": config.FMP_API_KEY},
            params={"symbol": symbol, "limit": limit}
        )
    
    async def fmp_general_news(self, limit: int = 20) -> Optional[List]:
        """Get FMP general news"""
        return await self._request(
            f"{self.fmp_url}/general-news",
            headers={"apikey": config.FMP_API_KEY},
            params={"limit": limit}
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

# ===================== UNIVERSE MANAGER =====================

class UniverseManager:
    """Manages the investment universe - fetching, storing, and updating stock lists"""
    
    # Comprehensive stock universe - 1000+ companies across all sectors and market caps
    CORE_UNIVERSE = [
        # ============ MEGA CAP TECH (50+) ============
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL",
        "ADBE", "CRM", "CSCO", "ACN", "TXN", "QCOM", "IBM", "AMD", "INTC", "AMAT",
        "ADI", "LRCX", "MU", "SNPS", "CDNS", "KLAC", "MRVL", "NXPI", "MCHP", "ON",
        
        # ============ SOFTWARE & CLOUD (80+) ============
        "NOW", "INTU", "PANW", "FTNT", "ZS", "CRWD", "NET", "DDOG", "SNOW", "MDB",
        "OKTA", "PLTR", "PATH", "WDAY", "VEEV", "SPLK", "TEAM", "HUBS", "ZM", "DOCU",
        "TWLO", "U", "SHOP", "TTD", "BILL", "PAYC", "PCTY", "SQ", "TOST", "FICO",
        "ANSS", "PTC", "SSNC", "GWRE", "BSY", "MANH", "APPF", "QTWO", "TENB", "QLYS",
        "SAIL", "RPD", "VRNS", "CYBR", "S", "SWI", "NTCT", "SCWX", "ZI", "CFLT",
        "ESTC", "NEWR", "SUMO", "DT", "FROG", "API", "DOCN", "DBX", "BOX", "FSLY",
        "NCNO", "ALRM", "BIGC", "WIX", "SPSC", "PRGS", "BASE", "EVBG", "PLAN", "CDAY",
        "DCT", "APPN", "FRSH", "BL", "PEGA", "MDSO", "LSPD", "CWAN", "RIOT", "MARA",
        
        # ============ SEMICONDUCTORS (60+) ============
        "ASML", "TSM", "ARM", "GFS", "WOLF", "SWKS", "QRVO", "CRUS", "SLAB", "SMTC",
        "MKSI", "ENTG", "KLIC", "POWI", "DIOD", "SYNA", "SITM", "ALGM", "MTSI", "AMBA",
        "LSCC", "INDI", "ACMR", "AOSL", "CEVA", "RMBS", "NVMI", "ONTO", "FORM", "IPGP",
        "VECO", "UCTT", "COHR", "LITE", "II-VI", "AAOI", "VIAV", "IIVI", "NPTN", "ACIA",
        "MPWR", "SMCI", "AEHR", "ATKR", "TER", "NVEC", "HIMX", "OLED", "UMC", "ASX",
        "STM", "NXPI", "MCHP", "SWKS", "TXN", "QCOM", "ADI", "MRVL", "ON", "GFS",
        
        # ============ FINANCIAL SERVICES (120+) ============
        "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "C",
        "AXP", "USB", "PNC", "TFC", "COF", "BK", "STT", "NTRS", "FITB", "HBAN",
        "KEY", "CFG", "MTB", "RF", "ZION", "CMA", "FCNCA", "WAL", "EWBC", "PACW",
        "FRC", "SBNY", "SIVB", "ALLY", "SYF", "DFS", "NAVI", "SLM", "TREE", "LC",
        "CME", "ICE", "NDAQ", "CBOE", "MKTX", "VIRT", "HOOD", "IBKR", "LPLA", "RJF",
        "SEIC", "TROW", "BEN", "IVZ", "FHI", "AMG", "JHG", "APAM", "VRTS", "EV",
        "SPGI", "MCO", "MSCI", "FDS", "MORN", "VRSK", "INFO", "DNB", "TRI", "CSGP",
        "FIS", "FISV", "GPN", "ADP", "PAYX", "WEX", "PYPL", "SQ", "FI", "COIN",
        "AIG", "PRU", "MET", "AFL", "LNC", "UNM", "VOYA", "PFG", "RGA", "GL",
        "CB", "TRV", "ALL", "PGR", "HIG", "CNA", "WRB", "RE", "RNR", "CINF",
        "L", "Y", "ERIE", "SIGI", "KMPR", "HCI", "PLMR", "KNSL", "ROOT", "LMND",
        "BRO", "MMC", "AON", "WTW", "AJG", "RYAN", "GSHD", "ESGR", "BRP", "BWIN",
        
        # ============ HEALTHCARE (150+) ============
        "UNH", "JNJ", "LLY", "PFE", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY",
        "AMGN", "GILD", "VRTX", "REGN", "MRNA", "BIIB", "ILMN", "ISRG", "SYK", "BSX",
        "MDT", "ZBH", "EW", "BDX", "DXCM", "ALGN", "IDXX", "IQV", "A", "MTD",
        "WAT", "PKI", "BIO", "TECH", "TFX", "HOLX", "COO", "XRAY", "HSIC", "OMI",
        "PODD", "TNDM", "IRTC", "LIVN", "NVST", "GMED", "NUVA", "ITGR", "LNTH", "CERS",
        "HCA", "THC", "UHS", "CYH", "SGRY", "SEM", "ACHC", "ENSG", "NHC", "PNTG",
        "CVS", "CI", "HUM", "CNC", "MOH", "OSCR", "CLVR", "ALHC", "CLOV", "BHVN",
        "ALNY", "SGEN", "BMRN", "SRPT", "EXEL", "INCY", "HALO", "PCVX", "BNTX", "NVAX",
        "CRSP", "BEAM", "EDIT", "NTLA", "VERV", "FATE", "RCKT", "BLUE", "SGMO", "RARE",
        "IONS", "SAREPTA", "UTHR", "NBIX", "JAZZ", "ACAD", "PTCT", "FOLD", "TGTX", "INSM",
        "IMGN", "RETA", "ARCT", "VXRT", "TBIO", "TVTX", "APLS", "DNLI", "ICPT", "CORT",
        "AXSM", "SAGE", "SAVA", "PRTA", "ARWR", "AKBA", "ALDX", "ARVN", "BCYC", "KALV",
        "ZTS", "IDXX", "ELAN", "PAHC", "PETQ", "CVET", "PETS", "WOOF", "BARK", "CHWY",
        "LFST", "TDOC", "AMWL", "DOCS", "ONEM", "TALK", "LVGO", "PHR", "ACCD", "HIMS",
        "OSCR", "GDRX", "SGFY", "PDCO", "MCK", "CAH", "ABC", "HSIC", "OMI", "PDCO",
        
        # ============ CONSUMER DISCRETIONARY (100+) ============
        "HD", "NKE", "MCD", "SBUX", "LOW", "TJX", "TGT", "ROST", "CMG", "DHI",
        "LEN", "PHM", "TOL", "MTH", "TMHC", "KBH", "MDC", "MHO", "CCS", "GRBK",
        "GM", "F", "TSLA", "RIVN", "LCID", "FSR", "NKLA", "GOEV", "RIDE", "ARVL",
        "ABNB", "BKNG", "EXPE", "MAR", "HLT", "H", "WH", "CHH", "STAY", "PLYA",
        "ORLY", "AZO", "AAP", "GPC", "LKQ", "MNRO", "PRTS", "DORM", "MOD", "SMP",
        "BBY", "WSM", "RH", "LOVE", "ARHS", "ETD", "PLBY", "BOOT", "BGFV", "HIBB",
        "DPZ", "YUM", "QSR", "DENN", "DIN", "TXRH", "CAKE", "BLMN", "EAT", "DRI",
        "WING", "SHAK", "BROS", "JACK", "PZZA", "FRGI", "BJRI", "RUTH", "RRGB", "LOCO",
        "LULU", "GPS", "ANF", "AEO", "URBN", "EXPR", "CATO", "PLCE", "TLYS", "ZUMZ",
        "RCL", "CCL", "NCLH", "WYNN", "LVS", "MGM", "CZR", "PENN", "DKNG", "RSI",
        
        # ============ CONSUMER STAPLES (60+) ============
        "PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL", "MDLZ", "KMB",
        "GIS", "K", "HSY", "SJM", "CAG", "KHC", "CPB", "HRL", "TSN", "SAFM",
        "STZ", "BF.B", "TAP", "SAM", "FIZZ", "CELH", "MNST", "KDP", "COKE", "NBEV",
        "EL", "CHD", "CLX", "SPB", "HELE", "HPC", "IPAR", "COTY", "REV", "ELF",
        "KR", "SYY", "USFD", "PFGC", "CORE", "CHEF", "UNFI", "SPTN", "WMK", "ACI",
        "DLTR", "DG", "FIVE", "OLLI", "BIG", "PRTY", "TUP", "HBI", "COLM", "VFC",
        
        # ============ INDUSTRIALS (120+) ============
        "UNP", "HON", "UPS", "BA", "CAT", "GE", "RTX", "DE", "LMT", "NOC",
        "MMM", "ITW", "EMR", "ROK", "ETN", "PH", "GD", "TXT", "LHX", "HII",
        "WM", "RSG", "WCN", "SRCL", "CLH", "CWST", "HCCI", "GFL", "ECOL", "ADSW",
        "CTAS", "CINF", "ROL", "ABM", "BRC", "ARMK", "GHC", "HRI", "NSP", "HURN",
        "FDX", "CSX", "NSC", "UNP", "CP", "CNI", "KSU", "WAB", "GWW", "FAST",
        "PCAR", "CMI", "PACCAR", "OSHK", "ALV", "LEA", "MGA", "VC", "AXL", "ADNT",
        "TT", "IR", "XYL", "FELE", "RXN", "FLOW", "MWA", "WTS", "BMI", "LNN",
        "ODFL", "SAIA", "XPO", "JBHT", "CHRW", "HUBG", "LSTR", "WERN", "KNX", "ARCB",
        "HTLD", "MRTN", "SNDR", "USAK", "RLGT", "YELL", "ECHO", "CVLG", "PTSI", "USX",
        "J", "FLR", "JCI", "CARR", "TDY", "GNRC", "AME", "KEYS", "TRMB", "GRMN",
        "AXON", "TDG", "HEI", "HWM", "HAYW", "CW", "ESAB", "MIR", "ZWS", "SPXC",
        "NVT", "HUBB", "AYI", "ALLE", "LII", "WCC", "CNM", "SITE", "SUM", "EXP",
        
        # ============ ENERGY (80+) ============
        "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "PXD",
        "HES", "DVN", "FANG", "HAL", "BKR", "KMI", "WMB", "OKE", "LNG", "TRGP",
        "MRO", "APA", "MGY", "MTDR", "CTRA", "OVV", "SM", "RRC", "AR", "SWN",
        "CNX", "EQT", "GPOR", "CHK", "NEXT", "CRK", "PDCE", "REPX", "PR", "ESTE",
        "FTI", "NOV", "CHX", "WHD", "OII", "RES", "HLX", "CLB", "PUMP", "LBRT",
        "PTEN", "HP", "NBR", "NE", "RIG", "DO", "VAL", "BORR", "SDRL", "PDS",
        "DINO", "DK", "PARR", "CVI", "PBF", "HFC", "CLMT", "CAPL", "NS", "GEL",
        "ET", "EPD", "MMP", "PAA", "MPLX", "WES", "ENLC", "DCP", "HESM", "SHLX",
        
        # ============ MATERIALS (60+) ============
        "LIN", "APD", "ECL", "SHW", "DD", "NEM", "FCX", "NUE", "VMC", "MLM",
        "DOW", "PPG", "ALB", "CTVA", "CF", "MOS", "NTR", "FMC", "SMG", "ANDE",
        "IFF", "CE", "EMN", "HUN", "ASH", "GCP", "OLN", "WLK", "CC", "TROX",
        "CLF", "X", "AA", "CENX", "CMC", "STLD", "RS", "ATI", "ARNC", "HAYN",
        "RGLD", "WPM", "FNV", "GOLD", "AEM", "KGC", "BTG", "IAG", "EGO", "PAAS",
        "BHP", "RIO", "VALE", "TECK", "SCCO", "MEOH", "OI", "BALL", "CCK", "SEE",
        
        # ============ UTILITIES (50+) ============
        "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "PEG", "ED",
        "WEC", "ES", "AWK", "DTE", "ETR", "FE", "AEE", "CMS", "EVRG", "AES",
        "NI", "LNT", "ATCO", "OGS", "NWE", "POR", "AVA", "BKH", "NWN", "UTL",
        "ALE", "PNM", "IDA", "MGEE", "AQN", "OTTR", "HE", "SJW", "WTRG", "YORW",
        "VST", "NRG", "RUN", "SEDG", "ENPH", "NOVA", "ARRY", "CSIQ", "JKS", "FSLR",
        
        # ============ REAL ESTATE (70+) ============
        "PLD", "AMT", "EQIX", "CCI", "PSA", "SPG", "O", "VICI", "WELL", "DLR",
        "AVB", "EQR", "ARE", "MAA", "ESS", "UDR", "VTR", "PEAK", "SUI", "HST",
        "EXR", "CUBE", "LSI", "NSA", "REXR", "TRNO", "STAG", "LXP", "IIPR", "GTY",
        "REG", "KIM", "FRT", "BRX", "SITE", "ROIC", "AKR", "UE", "ESRT", "PDM",
        "SLG", "VNO", "BXP", "KRC", "HIW", "OFC", "CUZ", "DEI", "JBGS", "WRE",
        "INVH", "AMH", "SFR", "NXRT", "ELME", "AIV", "NHI", "SBRA", "OHI", "LTC",
        "HR", "DOC", "GMRE", "MPW", "CHCT", "GEO", "CXW", "LADR", "STWD", "BXMT",
        
        # ============ COMMUNICATION SERVICES (60+) ============
        "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS", "CHTR", "WBD", "PARA", "FOX",
        "FOXA", "VIAC", "DISC", "DISCA", "NWSA", "NWS", "LBRDA", "SIRI", "LYV", "MSGS",
        "OMC", "IPG", "WPP", "PUBGY", "MGAM", "ZD", "QNST", "DLB", "TGNA", "GTN",
        "EA", "TTWO", "ATVI", "ZNGA", "PLTK", "SKLZ", "DDI", "SLGG", "HUYA", "DOYU",
        "RBLX", "MTCH", "BMBL", "IAC", "ANGI", "TREE", "YELP", "TRIP", "GRPN", "CARG",
        "SPOT", "PINS", "SNAP", "TWTR", "ROKU", "FUBO", "PLBY", "GENI", "DKNG", "PENN",
        
        # ============ HIGH GROWTH / MOMENTUM (80+) ============
        "SMCI", "MSTR", "APP", "CELH", "DUOL", "DKNG", "DASH", "RKLB", "IONQ", "SOUN",
        "AI", "UPST", "SOFI", "HOOD", "AFRM", "RIVN", "LCID", "NIO", "XPEV", "LI",
        "PLTR", "SNOW", "NET", "DDOG", "MDB", "ZS", "CRWD", "OKTA", "TWLO", "COIN",
        "PATH", "U", "CFLT", "ESTC", "GTLB", "MNDY", "HUBS", "ZI", "BRZE", "AMPL",
        "DOCS", "DOCN", "DT", "NEWR", "SUMO", "FROG", "API", "ASAN", "WEAV", "SMAR",
        "COUR", "UDMY", "CHGG", "LRNG", "SKIL", "VMEO", "PRCH", "OPEN", "RDFN", "COMP",
        "CVNA", "VROOM", "LOTZ", "SFT", "SPCE", "JOBY", "ACHR", "LILM", "EVTL", "GOEV",
        "WKHS", "RIDE", "HYLN", "XL", "BLNK", "CHPT", "EVGO", "DCFC", "VLTA", "NKLA",
        
        # ============ CLEAN ENERGY & EV (50+) ============
        "ENPH", "SEDG", "FSLR", "RUN", "NOVA", "PLUG", "BE", "BLDP", "FCEL", "BLOOM",
        "QS", "SLDP", "MVST", "DCRC", "LCID", "RIVN", "FSR", "ARVL", "CANOO", "WKHS",
        "MP", "LAC", "LTHM", "SQM", "PLL", "LIVENT", "ALB", "SGML", "OUST", "LAZR",
        "VLDR", "AEVA", "INVZ", "MVIS", "CPTN", "INDI", "PSNY", "ARVL", "RIDE", "GOEV",
        "ICLN", "TAN", "QCLN", "PBW", "SMOG", "ACES", "CTEC", "CNRG", "ERTH", "DRIV",
        
        # ============ CYBERSECURITY (30+) ============
        "PANW", "CRWD", "FTNT", "ZS", "OKTA", "CYBR", "TENB", "QLYS", "VRNS", "RPD",
        "S", "SAIL", "SWI", "NTCT", "SCWX", "FEYE", "MIME", "OSPN", "RDWR", "CHKP",
        "BB", "CACI", "LDOS", "BAH", "SAIC", "MANT", "ICE", "PSN", "CSGP", "PLTR",
        
        # ============ INTERNATIONAL ADRs (40+) ============
        "BABA", "JD", "PDD", "BIDU", "NIO", "XPEV", "LI", "BILI", "TME", "IQ",
        "VIPS", "YMM", "DIDI", "TAL", "EDU", "GOTU", "DAO", "KC", "TUYA", "FINV",
        "SE", "GRAB", "CPNG", "COUPN", "MELI", "STNE", "PAGS", "NU", "XP", "BSBR",
        "SAP", "ASML", "NVO", "SNY", "AZN", "GSK", "SONY", "TM", "HMC", "SHOP",
        
        # ============ SMALL/MID CAP VALUE (80+) ============
        "SNA", "LKQ", "JBL", "TOL", "STLD", "CLF", "X", "AA", "RHI", "JBHT",
        "CHRW", "XPO", "SAIA", "LSTR", "WERN", "KNX", "ARCB", "HUBG", "HTLD", "MATX",
        "RBC", "MSM", "GGG", "FLS", "ITT", "ROP", "IEX", "NDSN", "MIDD", "GTLS",
        "AIT", "GGG", "IDEX", "FLS", "RBC", "WTS", "FELE", "RXN", "FLOW", "MWA",
        "DCI", "ENS", "AAON", "AOS", "WTS", "FELE", "BMI", "LNN", "SXI", "MATW",
        "ROLL", "TRS", "SXT", "PRLB", "ROCK", "IIVI", "MKSI", "ENTG", "TTC", "EAF",
        "TREX", "AZEK", "DOOR", "SITE", "SUM", "BLDR", "BLD", "IBP", "APOG", "AWI",
        "TILE", "BECN", "PGTI", "GMS", "PATK", "JELD", "UFPI", "LGIH", "CVCO", "SKY",
        
        # ============ DAY TRADING / HIGH VOLATILITY (60+) ============
        # Meme stocks & retail favorites with high daily ranges
        "GME", "AMC", "BBBY", "BB", "CLOV", "WISH", "WKHS", "SPCE", "HYMC", "MULN",
        "TLRY", "SNDL", "CGC", "ACB", "CRON", "HEXO", "OGI", "VFF", "KERN", "GRWG",
        # High beta tech with massive intraday moves
        "NVDA", "AMD", "TSLA", "COIN", "MSTR", "RIOT", "MARA", "BITF", "CLSK", "BTBT",
        "HIVE", "HUT", "GREE", "CORZ", "CIFR", "DGII", "SDIG", "IREN", "WULF", "BTDR",
        # Biotech runners (FDA plays, volatile)
        "MRNA", "BNTX", "NVAX", "VXRT", "ATOS", "SESN", "CRVS", "OCGN", "INO", "SRNE",
        "NRXP", "CEMI", "PRPH", "ADGI", "ABOS", "CABA", "HOOK", "CALT", "GRPH", "ONCR",
        # SPACs & recent IPOs with high volatility
        "DWAC", "PHUN", "BKKT", "IRNT", "TMC", "VLTA", "DNA", "PAYO", "BIRD", "OPAD",
        # Leveraged ETFs for day trading (3x)
        "TQQQ", "SQQQ", "SPXL", "SPXS", "UPRO", "UVXY", "SOXL", "SOXS", "LABU", "LABD",
        "FAS", "FAZ", "TNA", "TZA", "NUGT", "DUST", "JNUG", "JDST", "ERX", "ERY",
        # High volume large caps for scalping
        "AAPL", "SPY", "QQQ", "META", "AMZN", "GOOG", "MSFT", "NFLX", "BABA", "PYPL"
    ]
    
    # ETFs for sector exposure + Leveraged for day trading
    CORE_ETFS = [
        "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "VEA", "VWO", "EFA", "EEM",
        "XLF", "XLK", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE",
        "XLC", "XBI", "IBB", "IHI", "IYH", "VHT", "ARKG", "LABU", "XHS", "IHE",
        "SMH", "SOXX", "PSI", "FTEC", "VGT", "IYW", "CIBR", "HACK", "BUG", "WCLD",
        "GLD", "SLV", "GDX", "GDXJ", "SIL", "PPLT", "PALL", "GLTR", "IAU", "SGOL",
        "TLT", "HYG", "LQD", "BND", "AGG", "VCIT", "VCSH", "JNK", "BNDX", "EMB",
        "VNQ", "IYR", "XLRE", "SCHH", "RWR", "ICF", "USRT", "REZ", "HOMZ", "REET",
        "ARKK", "ARKG", "ARKF", "ARKW", "ARKQ", "ARKX", "IZRL", "PRNT", "CTRU", "KOMP",
        "ICLN", "TAN", "QCLN", "PBW", "SMOG", "ACES", "FAN", "LIT", "DRIV", "IDRV",
        "SKYY", "CLOU", "WCLD", "IGV", "CIBR", "HACK", "FINX", "IPAY", "BOTZ", "ROBO",
        # Leveraged & Inverse ETFs for day trading
        "TQQQ", "SQQQ", "SPXL", "SPXS", "UPRO", "UVXY", "SOXL", "SOXS", "LABD",
        "FAS", "FAZ", "TNA", "TZA", "NUGT", "DUST", "JNUG", "JDST", "ERX", "ERY",
        "TVIX", "VXX", "VIXY", "SVXY", "TECL", "TECS", "FNGU", "FNGD", "WEBL", "WEBS"
    ]
    
    # Market cap tiers
    MARKET_CAP_TIERS = {
        "mega": 200e9,
        "large": 10e9,
        "mid": 2e9,
        "small": 300e6,
        "micro": 50e6,
        "nano": 0
    }
    
    def get_market_cap_label(self, market_cap: float) -> str:
        if not market_cap:
            return "unknown"
        if market_cap >= self.MARKET_CAP_TIERS["mega"]:
            return "Mega Cap"
        elif market_cap >= self.MARKET_CAP_TIERS["large"]:
            return "Large Cap"
        elif market_cap >= self.MARKET_CAP_TIERS["mid"]:
            return "Mid Cap"
        elif market_cap >= self.MARKET_CAP_TIERS["small"]:
            return "Small Cap"
        elif market_cap >= self.MARKET_CAP_TIERS["micro"]:
            return "Micro Cap"
        return "Nano Cap"
    
    async def load_universe(self, force_refresh: bool = False) -> List[UniverseStock]:
        """Load the full investment universe"""
        
        # Check MongoDB cache first
        if not force_refresh:
            cached = await db.universe.find_one({"_id": "stock_universe"})
            if cached and cached.get("updated_at"):
                age = datetime.now(timezone.utc) - cached["updated_at"].replace(tzinfo=timezone.utc)
                if age < timedelta(hours=6):
                    return [UniverseStock(**s) for s in cached.get("stocks", [])]
        
        logger.info("Loading comprehensive stock universe...")
        universe = {}
        
        # Load core universe stocks
        all_symbols = list(set(self.CORE_UNIVERSE + self.CORE_ETFS))
        logger.info(f"Processing {len(all_symbols)} symbols...")
        
        # Fetch profiles in batches to get sector/industry info
        for i in range(0, len(all_symbols), 20):
            batch = all_symbols[i:i+20]
            
            profiles = await asyncio.gather(
                *[api_client.fmp_profile(symbol) for symbol in batch],
                return_exceptions=True
            )
            
            for symbol, profile in zip(batch, profiles):
                if isinstance(profile, Exception) or not profile:
                    # Still add the stock with minimal info
                    is_etf = symbol in self.CORE_ETFS
                    universe[symbol] = UniverseStock(
                        symbol=symbol,
                        name=symbol,
                        exchange="UNKNOWN",
                        sector="ETF" if is_etf else None,
                        industry="Exchange Traded Fund" if is_etf else None,
                        country="US",
                        market_cap=None,
                        is_etf=is_etf,
                        is_actively_trading=True
                    )
                else:
                    is_etf = symbol in self.CORE_ETFS or profile.get('isEtf', False)
                    universe[symbol] = UniverseStock(
                        symbol=symbol,
                        name=profile.get('companyName', symbol),
                        exchange=profile.get('exchangeShortName', 'UNKNOWN'),
                        sector=profile.get('sector') or ("ETF" if is_etf else None),
                        industry=profile.get('industry') or ("Exchange Traded Fund" if is_etf else None),
                        country=profile.get('country', 'US'),
                        market_cap=profile.get('mktCap'),
                        is_etf=is_etf,
                        is_actively_trading=not profile.get('isDelisted', False)
                    )
            
            # Small delay between batches
            if i + 20 < len(all_symbols):
                await asyncio.sleep(0.3)
        
        # Store in MongoDB
        stocks_list = [s.dict() for s in universe.values()]
        await db.universe.update_one(
            {"_id": "stock_universe"},
            {
                "$set": {
                    "stocks": stocks_list,
                    "count": len(stocks_list),
                    "updated_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        logger.info(f"Loaded {len(universe)} stocks into universe")
        return list(universe.values())
    
    async def get_universe_stats(self) -> Dict:
        """Get statistics about the current universe"""
        cached = await db.universe.find_one({"_id": "stock_universe"})
        if not cached:
            return {"count": 0, "updated_at": None}
        
        stocks = cached.get("stocks", [])
        sectors = {}
        countries = {}
        market_caps = {"mega": 0, "large": 0, "mid": 0, "small": 0, "micro": 0, "unknown": 0}
        
        for s in stocks:
            sector = s.get("sector") or "Unknown"
            sectors[sector] = sectors.get(sector, 0) + 1
            
            country = s.get("country") or "Unknown"
            countries[country] = countries.get(country, 0) + 1
            
            mc = s.get("market_cap")
            if mc:
                label = self.get_market_cap_label(mc).lower().replace(" ", "_").replace("_cap", "")
                market_caps[label] = market_caps.get(label, 0) + 1
            else:
                market_caps["unknown"] += 1
        
        return {
            "count": len(stocks),
            "updated_at": cached.get("updated_at"),
            "sectors": sectors,
            "countries": countries,
            "market_caps": market_caps
        }

universe_manager = UniverseManager()

# ===================== TRADING SIGNAL ENGINE (Quality-Focused) =====================

class TradingEngine:
    """High-quality short-term trading signal generation - Quality over Quantity"""
    
    # Minimum requirements for signal generation
    MIN_VOLUME = 500000  # Minimum daily volume
    MIN_PRICE = 5.0  # Avoid penny stocks
    MIN_ATR_PCT = 1.5  # Minimum volatility (ATR as % of price)
    MIN_RR_RATIO = 2.0  # Minimum risk/reward ratio
    
    async def calculate_atr(self, historical: List[Dict], periods: int = 14) -> float:
        """Calculate Average True Range for volatility assessment"""
        if not historical or len(historical) < periods + 1:
            return 0
        
        true_ranges = []
        for i in range(1, min(periods + 1, len(historical))):
            high = historical[i].get('high', 0)
            low = historical[i].get('low', 0)
            prev_close = historical[i-1].get('close', 0)
            
            if high and low and prev_close:
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                true_ranges.append(tr)
        
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0
    
    async def detect_structure(self, price: float, historical: List[Dict], sma20: float, sma50: float) -> Dict:
        """Detect price structure: breakout, support/resistance, trend continuation"""
        structure = {
            "type": None,
            "strength": 0,
            "description": ""
        }
        
        if not historical or len(historical) < 20:
            return structure
        
        recent_highs = [h.get('high', 0) for h in historical[:20] if h.get('high')]
        recent_lows = [h.get('low', 0) for h in historical[:20] if h.get('low')]
        
        if not recent_highs or not recent_lows:
            return structure
        
        resistance = max(recent_highs)
        support = min(recent_lows)
        
        # Breakout detection: price above recent resistance with momentum
        if price > resistance * 0.98:
            structure["type"] = "breakout"
            structure["strength"] = min((price / resistance - 1) * 100, 10)
            structure["description"] = f"Breaking above ${resistance:.2f} resistance"
        
        # Support bounce: price near support with reversal
        elif price < support * 1.05 and price > support * 0.98:
            structure["type"] = "support_bounce"
            structure["strength"] = 5
            structure["description"] = f"Bouncing from ${support:.2f} support"
        
        # Trend continuation: price above rising MAs
        elif sma20 > sma50 and price > sma20:
            structure["type"] = "trend_continuation"
            structure["strength"] = 7
            structure["description"] = "Uptrend continuation above moving averages"
        
        # Pullback to MA: price pulled back to rising MA
        elif sma20 > sma50 and price <= sma20 * 1.02 and price >= sma20 * 0.98:
            structure["type"] = "ma_pullback"
            structure["strength"] = 6
            structure["description"] = f"Pullback to 20-day MA (${sma20:.2f})"
        
        return structure
    
    async def analyze_for_trading(self, symbol: str) -> Optional[Dict]:
        """
        Analyze stock for HIGH-QUALITY trading opportunities only.
        Returns detailed analysis including why stock was included/excluded.
        """
        analysis = {
            "symbol": symbol,
            "included": False,
            "exclusion_reason": None,
            "signal": None
        }
        
        try:
            quote, profile, historical = await asyncio.gather(
                api_client.fmp_quote(symbol),
                api_client.fmp_profile(symbol),
                api_client.fmp_historical(symbol, days=50),
                return_exceptions=True
            )
            
            if isinstance(quote, Exception) or not quote:
                analysis["exclusion_reason"] = "No quote data available"
                return analysis
            if isinstance(profile, Exception):
                profile = None
            if isinstance(historical, Exception) or not historical:
                historical = []
            
            price = quote.get('price', 0)
            volume = quote.get('volume', 0)
            change_pct = quote.get('changePercentage', quote.get('changesPercentage', 0)) or 0
            
            # ===== STRICT FILTERS =====
            
            # Filter 1: Minimum price (avoid penny stocks)
            if price < self.MIN_PRICE:
                analysis["exclusion_reason"] = f"Price ${price:.2f} below minimum ${self.MIN_PRICE}"
                return analysis
            
            # Filter 2: Minimum volume (liquidity)
            if volume < self.MIN_VOLUME:
                analysis["exclusion_reason"] = f"Volume {volume:,} below minimum {self.MIN_VOLUME:,}"
                return analysis
            
            # Filter 3: Calculate ATR for volatility
            atr = await self.calculate_atr(historical)
            atr_pct = (atr / price * 100) if price > 0 else 0
            
            if atr_pct < self.MIN_ATR_PCT and atr_pct > 0:
                analysis["exclusion_reason"] = f"Low volatility (ATR {atr_pct:.1f}% < {self.MIN_ATR_PCT}%)"
                return analysis
            
            # ===== CALCULATE INDICATORS =====
            
            avg_volume = quote.get('avgVolume') or volume
            vol_ratio = volume / avg_volume if avg_volume > 0 else 1.0
            
            # Calculate SMAs
            prices_list = [h.get('close', 0) for h in historical if h.get('close')]
            sma20 = sum(prices_list[:20]) / 20 if len(prices_list) >= 20 else price
            sma50 = sum(prices_list[:50]) / 50 if len(prices_list) >= 50 else price
            sma200 = quote.get('priceAvg200', 0) or price
            
            high_52 = quote.get('yearHigh', price)
            low_52 = quote.get('yearLow', price)
            range_52 = high_52 - low_52 if high_52 > low_52 else 1
            position_52 = ((price - low_52) / range_52) * 100
            
            # ===== CONFLUENCE CHECK =====
            # Require multiple factors aligning for a quality signal
            # Start with base score of 30 (neutral baseline)
            
            confluence_score = 30
            confluence_factors = []
            
            # Factor 1: Momentum (price trend strength)
            momentum_score = 0
            if change_pct >= 3:
                momentum_score = 30
                confluence_factors.append(f"Strong momentum (+{change_pct:.1f}%)")
            elif change_pct >= 1.5:
                momentum_score = 20
                confluence_factors.append(f"Good momentum (+{change_pct:.1f}%)")
            elif change_pct >= 0.5:
                momentum_score = 10
                confluence_factors.append(f"Positive momentum (+{change_pct:.1f}%)")
            elif change_pct >= 0:
                momentum_score = 5
            elif change_pct > -1:
                momentum_score = 0  # Flat/slightly negative - neutral
            elif change_pct > -2:
                momentum_score = -5
            else:
                momentum_score = -15  # Reduced penalty from -20
            
            confluence_score += momentum_score
            
            # Factor 2: Volume confirmation
            volume_score = 0
            if vol_ratio >= 2.0:
                volume_score = 25
                confluence_factors.append(f"Volume spike ({vol_ratio:.1f}x average)")
            elif vol_ratio >= 1.5:
                volume_score = 15
                confluence_factors.append(f"Above-average volume ({vol_ratio:.1f}x)")
            elif vol_ratio < 0.7:
                volume_score = -10
            
            confluence_score += volume_score
            
            # Factor 3: Price structure
            structure = await self.detect_structure(price, historical, sma20, sma50)
            structure_score = 0
            if structure["type"]:
                structure_score = structure["strength"] * 3
                confluence_factors.append(structure["description"])
            
            confluence_score += structure_score
            
            # Factor 4: Trend alignment
            trend_score = 0
            if price > sma20 > sma50:
                trend_score = 20
                if "trend" not in " ".join(confluence_factors).lower():
                    confluence_factors.append("Bullish trend alignment (Price > SMA20 > SMA50)")
            elif price > sma50:
                trend_score = 10
            elif price < sma20 < sma50:
                trend_score = -15
            
            confluence_score += trend_score
            
            # Factor 5: 52-week position (breakout potential)
            position_score = 0
            if position_52 > 85:
                position_score = 15
                confluence_factors.append(f"Near 52-week high ({position_52:.0f}% of range)")
            elif position_52 < 20:
                position_score = -10
            
            confluence_score += position_score
            
            # ===== QUALITY GATE =====
            # Require minimum confluence score AND at least 1 strong factor
            # Base score is 30, so 45 means at least +15 from factors
            
            min_confluence = 45
            min_factors = 1
            
            if confluence_score < min_confluence:
                analysis["exclusion_reason"] = f"Low confluence score ({confluence_score} < {min_confluence})"
                return analysis
            
            if len(confluence_factors) < min_factors:
                analysis["exclusion_reason"] = f"Insufficient confluence factors ({len(confluence_factors)} < {min_factors})"
                return analysis
            
            # ===== CALCULATE TRADE SETUP =====
            
            # Dynamic stop-loss based on ATR
            atr_stop = atr * 1.5 if atr > 0 else price * 0.03
            stop_loss = round(price - atr_stop, 2)
            
            # Take profit based on R:R target
            risk = price - stop_loss
            target_rr = 2.5  # Target 2.5:1 R:R
            take_profit = round(price + (risk * target_rr), 2)
            
            # Verify R:R meets minimum
            actual_rr = (take_profit - price) / risk if risk > 0 else 0
            if actual_rr < self.MIN_RR_RATIO:
                analysis["exclusion_reason"] = f"R:R ratio {actual_rr:.1f} below minimum {self.MIN_RR_RATIO}"
                return analysis
            
            # Entry zone (pullback entry preferred)
            entry_low = round(price * 0.995, 2)
            entry_high = round(price * 1.005, 2)
            entry_zone = f"${entry_low} - ${entry_high}"
            
            # ===== CONFIDENCE SCORE =====
            # Normalized 0-100 based on confluence
            confidence = min(max(confluence_score + 30, 50), 95) / 100
            
            # ===== SIGNAL CATEGORIZATION =====
            if confidence >= 0.75 and len(confluence_factors) >= 3:
                signal_type = "Strong Buy"
                category = "Hot"
            elif confidence >= 0.65 and structure["type"] == "breakout":
                signal_type = "Buy"
                category = "Breakout"
            elif confidence >= 0.60 and momentum_score >= 20:
                signal_type = "Buy"
                category = "Momentum"
            elif confidence >= 0.55 and volume_score >= 15:
                signal_type = "Buy"
                category = "High Volume"
            else:
                signal_type = "Watch"
                category = "Watch"
            
            # Build reasoning
            reasoning = "; ".join(confluence_factors) if confluence_factors else "Technical setup"
            
            # ===== GET NEWS SENTIMENT =====
            news_data = await news_engine.get_news_sentiment_score(symbol)
            news_sentiment = news_data.get('overall_sentiment', 'Neutral')
            news_impact = news_data.get('sentiment_impact', 0)
            
            # Adjust confidence based on news sentiment
            if news_impact > 5:
                confidence = min(confidence + 0.05, 0.95)  # Boost for very positive news
                reasoning += f"; News sentiment: {news_sentiment} (+{news_impact})"
            elif news_impact < -5:
                confidence = max(confidence - 0.05, 0.50)  # Reduce for very negative news
                reasoning += f"; News sentiment: {news_sentiment} ({news_impact})"
            elif news_impact != 0:
                reasoning += f"; News: {news_sentiment}"
            
            # ===== CREATE SIGNAL =====
            signal = TradingSignal(
                symbol=symbol,
                name=profile.get('companyName', symbol) if profile else symbol,
                price=price,
                signal=signal_type,
                confidence=confidence,
                entry_zone=entry_zone,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size="2-3% of portfolio",
                risk_reward=f"1:{actual_rr:.1f}",
                reasoning=reasoning,
                indicators={
                    "change_pct": round(change_pct, 2),
                    "volume_ratio": round(vol_ratio, 2),
                    "atr": round(atr, 2),
                    "atr_pct": round(atr_pct, 2),
                    "price_vs_50ma": round(((price / sma50) - 1) * 100, 2) if sma50 else 0,
                    "price_vs_200ma": round(((price / sma200) - 1) * 100, 2) if sma200 else 0,
                    "52_week_position": round(position_52, 1),
                    "confluence_score": confluence_score,
                    "structure_type": structure["type"]
                },
                category=category,
                news_sentiment=news_sentiment,
                news_impact=news_impact,
                news_headlines=news_data.get('recent_headlines', [])[:3]
            )
            
            analysis["included"] = True
            analysis["signal"] = signal
            return analysis
            
        except Exception as e:
            logger.error(f"Trading analysis error for {symbol}: {e}")
            analysis["exclusion_reason"] = f"Analysis error: {str(e)}"
            return analysis
    
    def _quality_score(self, s):
        """Compute quality score for ranking signals"""
        if isinstance(s, dict):
            base = s.get("confidence", 0)
            indicators = s.get("indicators", {})
        else:
            base = s.confidence
            indicators = s.indicators if hasattr(s, 'indicators') else {}
        if indicators.get("structure_type"):
            base += 0.1
        if indicators.get("volume_ratio", 0) >= 1.5:
            base += 0.05
        return base

    async def batch_analyze_trading(self, symbols: List[str], batch_size: int = 5) -> tuple:
        """Analyze multiple symbols for trading in batches to avoid rate limits"""
        included = []
        excluded = []
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            try:
                analyses = await asyncio.gather(
                    *[self.analyze_for_trading(s) for s in batch],
                    return_exceptions=True
                )
                for analysis in analyses:
                    if isinstance(analysis, Exception):
                        continue
                    if analysis and analysis.get("included") and analysis.get("signal"):
                        included.append(analysis["signal"])
                    elif analysis:
                        excluded.append({
                            "symbol": analysis.get("symbol"),
                            "reason": analysis.get("exclusion_reason", "Unknown")
                        })
            except Exception as e:
                logger.error(f"Trading batch {i//batch_size + 1} error: {e}")
            
            if i + batch_size < len(symbols):
                await asyncio.sleep(1.2)
        
        return included, excluded

    async def refresh_trading_signals(self, limit: int = 1000) -> int:
        """Background task: scan full universe and cache trading signals in MongoDB"""
        try:
            symbols = list(dict.fromkeys(universe_manager.CORE_UNIVERSE[:limit]))
            logger.info(f"Trading refresh: scanning {len(symbols)} stocks in batches...")
            
            all_included = []
            batch_size = 5
            delay = 1.5
            
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                try:
                    analyses = await asyncio.gather(
                        *[self.analyze_for_trading(s) for s in batch],
                        return_exceptions=True
                    )
                    for analysis in analyses:
                        if isinstance(analysis, Exception):
                            continue
                        if analysis and analysis.get("included") and analysis.get("signal"):
                            sig = analysis["signal"]
                            sig_dict = sig.dict() if hasattr(sig, 'dict') else sig
                            sig_dict["last_updated"] = datetime.now(timezone.utc).isoformat()
                            await db.trading_signals.update_one(
                                {"symbol": sig_dict["symbol"]},
                                {"$set": sig_dict},
                                upsert=True
                            )
                            all_included.append(sig_dict)
                    
                    if (i // batch_size) % 20 == 0:
                        logger.info(f"Trading refresh batch {i//batch_size + 1}/{(len(symbols) + batch_size - 1)//batch_size}, signals so far: {len(all_included)}")
                except Exception as e:
                    logger.error(f"Trading refresh batch {i//batch_size + 1} failed: {e}")
                
                if i + batch_size < len(symbols):
                    await asyncio.sleep(delay)
            
            logger.info(f"Trading refresh complete: {len(all_included)} signals stored from {len(symbols)} stocks")
            return len(all_included)
        except Exception as e:
            logger.error(f"Trading refresh error: {e}")
            return 0

    async def scan_trading_opportunities(self) -> Dict:
        """
        Scan market for HIGH-QUALITY trading opportunities.
        Uses cached signals from full universe if available, otherwise quick scan.
        """
        # Check for cached trading signals from full universe scan
        cached_count = await db.trading_signals.count_documents({})
        
        if cached_count >= 10:
            # Use cached data from background scan
            cursor = db.trading_signals.find({}, {"_id": 0}).sort("confidence", -1)
            all_cached = await cursor.to_list(length=2000)
            
            all_cached.sort(key=self._quality_score, reverse=True)
            all_signals = all_cached
            # Show the full universe size that was scanned, not just signals found
            stocks_scanned = len(universe_manager.CORE_UNIVERSE)
            source = "cached"
        else:
            # Fallback: quick scan of core stocks
            quick_universe = [
                "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
                "AMD", "NFLX", "CRM", "SHOP", "SQ", "COIN", "PLTR", "SNOW",
                "ROKU", "SNAP", "UBER", "ABNB", "RIVN", "LCID", "NIO",
                "MARA", "RIOT", "HOOD", "SOFI", "AFRM", "UPST",
                "XOM", "CVX", "JPM", "GS", "BA", "CAT", "DE"
            ]
            included, excluded = await self.batch_analyze_trading(quick_universe, batch_size=10)
            included.sort(key=self._quality_score, reverse=True)
            all_signals = [s.dict() if hasattr(s, 'dict') else s for s in included]
            stocks_scanned = len(quick_universe)
            source = "live"
        
        # Categorize
        hot = [s for s in all_signals if s.get("category") == "Hot"]
        breakout = [s for s in all_signals if s.get("category") == "Breakout"]
        momentum = [s for s in all_signals if s.get("category") == "Momentum"]
        high_volume = [s for s in all_signals if s.get("category") == "High Volume"]
        watch = [s for s in all_signals if s.get("category") == "Watch"]
        
        # Top Trades Today: Best 5 regardless of category
        top_trades = sorted(all_signals, key=self._quality_score, reverse=True)[:5]
        
        return {
            "top_trades": top_trades,
            "hot": hot,
            "breakout": breakout,
            "momentum": momentum,
            "high_volume": high_volume,
            "watch": watch,
            "all": all_signals,
            "diagnostics": {
                "stocks_scanned": stocks_scanned,
                "signals_generated": len(all_signals),
                "source": source,
                "excluded_count": stocks_scanned - len(all_signals),
                "excluded_reasons": [],
                "filters_applied": [
                    f"Min Volume: {self.MIN_VOLUME:,}",
                    f"Min Price: ${self.MIN_PRICE}",
                    f"Min ATR%: {self.MIN_ATR_PCT}%",
                    f"Min R:R: {self.MIN_RR_RATIO}:1",
                    "Confluence: 2+ factors required"
                ]
            }
        }

trading_engine = TradingEngine()

# ===================== INVESTMENT SIGNAL ENGINE (ENHANCED) =====================

class InvestmentEngine:
    """Long-term investment analysis with broad universe support"""
    
    SECTOR_BENCHMARKS = {
        "Technology": {"pe": 28, "roe": 20, "growth": 15, "margin": 22},
        "Healthcare": {"pe": 22, "roe": 15, "growth": 10, "margin": 18},
        "Financial Services": {"pe": 12, "roe": 12, "growth": 6, "margin": 28},
        "Consumer Cyclical": {"pe": 20, "roe": 16, "growth": 8, "margin": 12},
        "Consumer Defensive": {"pe": 24, "roe": 18, "growth": 5, "margin": 14},
        "Industrials": {"pe": 20, "roe": 15, "growth": 7, "margin": 12},
        "Energy": {"pe": 12, "roe": 12, "growth": 5, "margin": 15},
        "Basic Materials": {"pe": 15, "roe": 12, "growth": 5, "margin": 12},
        "Real Estate": {"pe": 35, "roe": 8, "growth": 5, "margin": 30},
        "Utilities": {"pe": 18, "roe": 10, "growth": 3, "margin": 15},
        "Communication Services": {"pe": 20, "roe": 15, "growth": 8, "margin": 20},
        "default": {"pe": 20, "roe": 15, "growth": 8, "margin": 15}
    }
    
    async def analyze_for_investment(self, symbol: str, include_incomplete: bool = True) -> Optional[InvestmentSignal]:
        """Analyze stock for long-term investment with graceful fallback handling"""
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
            
            # Calculate data completeness
            data_sources = [quote, profile, ratios, metrics, growth]
            available_sources = sum(1 for d in data_sources if d)
            data_completeness = (available_sources / len(data_sources)) * 100
            
            # Require at least quote or profile
            if not quote and not profile:
                return None
            
            # Don't include if less than 40% data and not forcing incomplete
            if data_completeness < 40 and not include_incomplete:
                return None
            
            # Combine data
            data = {}
            for d in [ratios, metrics, growth, quote, profile]:
                if d:
                    data.update(d)
            
            sector = data.get('sector', 'default')
            benchmark = self.SECTOR_BENCHMARKS.get(sector, self.SECTOR_BENCHMARKS['default'])
            price = data.get('price', 0)
            market_cap = data.get('marketCap', 0)
            
            bull_case = []
            bear_case = []
            risks = []
            
            # Valuation Score (with fallback)
            valuation_score = 50
            pe = data.get('peRatioTTM') or data.get('pe')
            if pe and pe > 0:
                if pe < benchmark['pe'] * 0.7:
                    valuation_score += 25
                    bull_case.append(f"Attractive P/E of {pe:.1f} vs sector {benchmark['pe']}")
                elif pe < benchmark['pe']:
                    valuation_score += 12
                elif pe > benchmark['pe'] * 1.5:
                    valuation_score -= 20
                    bear_case.append(f"Premium valuation (P/E: {pe:.1f})")
            else:
                valuation_score = 45  # Neutral if missing
            
            ev_ebitda = data.get('enterpriseValueOverEBITDATTM')
            if ev_ebitda and 0 < ev_ebitda < 50:
                if ev_ebitda < 10:
                    valuation_score += 15
                    bull_case.append(f"Low EV/EBITDA of {ev_ebitda:.1f}")
                elif ev_ebitda > 20:
                    valuation_score -= 10
            
            # Quality Score
            quality_score = 50
            roe = data.get('returnOnEquityTTM') or data.get('roe')
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
            
            net_margin = data.get('netProfitMarginTTM') or data.get('netProfitMargin')
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
            de = data.get('debtEquityRatioTTM') or data.get('debtToEquity')
            if de is not None:
                if de < 0.3:
                    strength_score += 20
                    bull_case.append(f"Strong balance sheet (D/E: {de:.2f})")
                elif de > 1.5:
                    strength_score -= 20
                    risks.append(f"High debt (D/E: {de:.2f})")
            
            current = data.get('currentRatioTTM') or data.get('currentRatio')
            if current:
                if current > 2:
                    strength_score += 10
                elif current < 1:
                    strength_score -= 15
                    risks.append("Liquidity concerns")
            
            # Risk Score
            risk_score = 70
            beta = data.get('beta', 1)
            if beta and beta > 1.5:
                risk_score -= 20
                risks.append(f"High volatility (beta: {beta:.2f})")
            elif beta and beta < 0.8:
                risk_score += 10
            
            if market_cap < 2e9:
                risk_score -= 15
                risks.append("Small cap risk")
            elif market_cap > 100e9:
                risk_score += 10
            
            # Adjust scores for incomplete data
            if data_completeness < 60:
                # Reduce confidence for incomplete data
                valuation_score = valuation_score * 0.9
                quality_score = quality_score * 0.9
                growth_score = growth_score * 0.9
                strength_score = strength_score * 0.9
            
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
            
            # Intrinsic value estimate
            fcf = data.get('freeCashFlowPerShareTTM', 0)
            intrinsic = None
            upside = None
            if fcf and fcf > 0:
                growth_rate = min((rev_growth or 0.05), 0.25)  # Cap growth rate
                discount_rate = 0.10
                terminal_multiple = 15
                intrinsic = fcf * terminal_multiple * (1 + growth_rate)
                if price > 0:
                    upside_pct = ((intrinsic / price) - 1) * 100
                    upside = f"{upside_pct:+.1f}%"
                    if upside_pct > 30:
                        bull_case.append(f"Potential upside of {upside_pct:.0f}%")
                        if category not in ["Hot", "Bullish"]:
                            category = "Undervalued"
                    elif upside_pct < -20:
                        bear_case.append(f"Appears overvalued by {abs(upside_pct):.0f}%")
                        category = "Overpriced"
            
            reasoning = f"Overall score {overall:.0f}/100. "
            if bull_case:
                reasoning += f"Strengths: {'; '.join(bull_case[:2])}. "
            if bear_case:
                reasoning += f"Concerns: {'; '.join(bear_case[:2])}."
            
            # Market cap label
            market_cap_label = universe_manager.get_market_cap_label(market_cap)
            
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
                category=category,
                sector=sector,
                industry=data.get('industry'),
                country=data.get('country', 'US'),
                market_cap=market_cap,
                market_cap_label=market_cap_label,
                data_completeness=round(data_completeness, 1),
                last_updated=datetime.now(timezone.utc).isoformat()
            )
        except Exception as e:
            logger.error(f"Investment analysis error for {symbol}: {e}")
            return None
    
    async def batch_analyze(self, symbols: List[str], batch_size: int = 10) -> List[InvestmentSignal]:
        """Analyze multiple symbols in batches to avoid rate limits"""
        all_signals = []
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            signals = await asyncio.gather(*[self.analyze_for_investment(s) for s in batch])
            valid_signals = [s for s in signals if s]
            all_signals.extend(valid_signals)
            
            # Small delay between batches to avoid rate limits
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.5)
        
        return all_signals
    
    async def refresh_universe_signals(self, limit: int = 500) -> int:
        """Background task to refresh investment signals for the universe"""
        try:
            # Get symbols directly from the hardcoded universe (more reliable)
            symbols = universe_manager.CORE_UNIVERSE[:limit]
            logger.info(f"Refreshing signals for {len(symbols)} stocks from core universe...")
            
            signals = await self.batch_analyze(symbols, batch_size=10)
            
            # Store in MongoDB
            for signal in signals:
                await db.investment_signals.update_one(
                    {"symbol": signal.symbol},
                    {"$set": signal.dict()},
                    upsert=True
                )
            
            logger.info(f"Stored {len(signals)} investment signals")
            return len(signals)
        except Exception as e:
            logger.error(f"Refresh universe signals error: {e}")
            return 0
    
    async def get_cached_signals(
        self,
        page: int = 1,
        page_size: int = 50,
        filters: Optional[InvestmentFilters] = None,
        sort_by: str = "overall_score",
        sort_dir: str = "desc"
    ) -> Dict:
        """Get cached signals with filtering and pagination"""
        
        query = {}
        
        if filters:
            if filters.min_market_cap:
                query["market_cap"] = {"$gte": filters.min_market_cap}
            if filters.max_market_cap:
                if "market_cap" in query:
                    query["market_cap"]["$lte"] = filters.max_market_cap
                else:
                    query["market_cap"] = {"$lte": filters.max_market_cap}
            if filters.sectors:
                query["sector"] = {"$in": filters.sectors}
            if filters.countries:
                query["country"] = {"$in": filters.countries}
            if filters.min_valuation_score:
                query["valuation_score"] = {"$gte": filters.min_valuation_score}
            if filters.min_quality_score:
                query["quality_score"] = {"$gte": filters.min_quality_score}
            if filters.min_growth_score:
                query["growth_score"] = {"$gte": filters.min_growth_score}
            if filters.min_overall_score:
                query["overall_score"] = {"$gte": filters.min_overall_score}
            if filters.signals:
                query["signal"] = {"$in": filters.signals}
            if filters.categories:
                query["category"] = {"$in": filters.categories}
        
        # Get total count
        total = await db.investment_signals.count_documents(query)
        
        # Get paginated results
        sort_direction = -1 if sort_dir == "desc" else 1
        cursor = db.investment_signals.find(query, {"_id": 0})
        cursor = cursor.sort(sort_by, sort_direction)
        cursor = cursor.skip((page - 1) * page_size).limit(page_size)
        
        results = await cursor.to_list(length=page_size)
        
        # Get category counts for current filter
        pipeline = [
            {"$match": query},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        category_counts = {}
        async for doc in db.investment_signals.aggregate(pipeline):
            category_counts[doc["_id"]] = doc["count"]
        
        return {
            "signals": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "categories": category_counts
        }
    
    async def scan_investment_opportunities(self) -> Dict[str, List[InvestmentSignal]]:
        """Original scan method for backward compatibility - now uses cached data or analyzes on demand"""
        
        # Check if we have cached signals
        total = await db.investment_signals.count_documents({})
        
        if total > 50:
            # Use cached data
            all_signals = []
            cursor = db.investment_signals.find({}, {"_id": 0}).sort("overall_score", -1).limit(300)
            async for doc in cursor:
                all_signals.append(InvestmentSignal(**doc))
            
            signals = all_signals
        else:
            # Analyze a broader set of stocks on demand
            universe = universe_manager.CORE_UNIVERSE[:100]  # Use first 100 from core universe
            
            logger.info(f"No cache, analyzing {len(universe)} stocks on demand...")
            signals = await self.batch_analyze(universe, batch_size=10)
            signals = [s for s in signals if s]
            
            # Store these in cache for next time
            for signal in signals:
                await db.investment_signals.update_one(
                    {"symbol": signal.symbol},
                    {"$set": signal.dict()},
                    upsert=True
                )
            logger.info(f"Cached {len(signals)} signals")
        
        hot = [s for s in signals if s.category == "Hot"]
        bullish = [s for s in signals if s.category == "Bullish"]
        undervalued = [s for s in signals if s.category == "Undervalued"]
        bearish = [s for s in signals if s.category == "Bearish"]
        overpriced = [s for s in signals if s.category == "Overpriced"]
        watch = [s for s in signals if s.category == "Watch"]
        
        return {
            "hot": sorted(hot, key=lambda x: x.overall_score, reverse=True)[:15],
            "bullish": sorted(bullish, key=lambda x: x.overall_score, reverse=True)[:15],
            "undervalued": sorted(undervalued, key=lambda x: x.overall_score, reverse=True)[:15],
            "watch": sorted(watch, key=lambda x: x.overall_score, reverse=True)[:15],
            "bearish": bearish[:15],
            "overpriced": overpriced[:15],
            "avoid": [s for s in signals if s.signal == "Sell"][:15],
            "all": sorted(signals, key=lambda x: x.overall_score, reverse=True),
            "total_analyzed": len(signals)
        }

investment_engine = InvestmentEngine()

# Initialize enhanced investment engine
enhanced_investment_engine = EnhancedInvestmentEngine(api_client, db)

# Initialize long-term investing engine
lt_engine = LongTermInvestingEngine(db)

# Initialize execution transparency tracker
exec_transparency = ExecutionTransparencyTracker(db)

# ===================== NEWS & SENTIMENT =====================

class NewsSentimentEngine:
    """News aggregation and sentiment analysis"""
    
    POSITIVE_WORDS = ['surge', 'jump', 'beat', 'exceed', 'upgrade', 'buy', 'bullish', 'growth', 'profit', 'gain', 'rally', 'breakthrough', 'record', 'strong', 'soar', 'outperform', 'positive', 'boost', 'upside']
    NEGATIVE_WORDS = ['drop', 'fall', 'miss', 'downgrade', 'sell', 'bearish', 'loss', 'decline', 'crash', 'warning', 'lawsuit', 'investigation', 'weak', 'plunge', 'risk', 'concern', 'fear', 'cut', 'layoff', 'recall']
    
    def analyze_sentiment(self, text: str) -> Tuple[str, float]:
        """Simple rule-based sentiment analysis"""
        if not text:
            return "Neutral", 0.5
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
    
    async def get_news_sentiment_score(self, symbol: str) -> Dict[str, Any]:
        """Get aggregated news sentiment score for a symbol - used by trading/investment engines"""
        news_items = []
        sentiments = []
        
        # Try FMP news first (primary source)
        fmp_news = await api_client.fmp_news(symbol, limit=10)
        if fmp_news and isinstance(fmp_news, list):
            for item in fmp_news[:10]:
                headline = item.get('title', '') or item.get('text', '')
                sentiment, score = self.analyze_sentiment(headline)
                sentiments.append((sentiment, score))
                news_items.append({
                    'title': headline[:100],
                    'sentiment': sentiment,
                    'score': score
                })
        
        # Fallback to Finnhub if no FMP news
        if len(sentiments) < 3:
            finnhub_news = await api_client.finnhub_news(symbol)
            if finnhub_news:
                for item in finnhub_news[:5]:
                    headline = item.get('headline', '')
                    sentiment, score = self.analyze_sentiment(headline)
                    sentiments.append((sentiment, score))
                    news_items.append({
                        'title': headline[:100],
                        'sentiment': sentiment,
                        'score': score
                    })
        
        if not sentiments:
            return {
                'overall_sentiment': 'Neutral',
                'sentiment_score': 0.5,
                'news_count': 0,
                'positive_count': 0,
                'negative_count': 0,
                'sentiment_impact': 0,  # -10 to +10 scale for scoring
                'recent_headlines': []
            }
        
        # Calculate aggregate sentiment
        avg_score = sum(s[1] for s in sentiments) / len(sentiments)
        positive_count = sum(1 for s in sentiments if s[0] == 'Positive')
        negative_count = sum(1 for s in sentiments if s[0] == 'Negative')
        
        # Calculate sentiment impact on score (-10 to +10)
        # Positive news boosts, negative news penalizes
        sentiment_impact = 0
        if positive_count > negative_count * 2:
            sentiment_impact = min(10, (positive_count - negative_count) * 2)
        elif negative_count > positive_count * 2:
            sentiment_impact = max(-10, -(negative_count - positive_count) * 2)
        elif positive_count > negative_count:
            sentiment_impact = min(5, positive_count - negative_count)
        elif negative_count > positive_count:
            sentiment_impact = max(-5, -(negative_count - positive_count))
        
        # Determine overall sentiment
        if positive_count > negative_count + 2:
            overall = 'Bullish'
        elif negative_count > positive_count + 2:
            overall = 'Bearish'
        elif positive_count > negative_count:
            overall = 'Slightly Positive'
        elif negative_count > positive_count:
            overall = 'Slightly Negative'
        else:
            overall = 'Neutral'
        
        return {
            'overall_sentiment': overall,
            'sentiment_score': avg_score,
            'news_count': len(sentiments),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'sentiment_impact': sentiment_impact,
            'recent_headlines': news_items[:5]
        }
    
    async def get_news_for_symbol(self, symbol: str) -> List[NewsItem]:
        """Get news for a specific symbol"""
        news_items = []
        
        # Try FMP news first
        fmp_news = await api_client.fmp_news(symbol, limit=10)
        if fmp_news and isinstance(fmp_news, list):
            for item in fmp_news[:5]:
                headline = item.get('title', '') or item.get('text', '')
                sentiment, score = self.analyze_sentiment(headline)
                pub_date = item.get('publishedDate', '') or item.get('published', '')
                news_items.append(NewsItem(
                    title=headline,
                    source=item.get('site', 'FMP'),
                    url=item.get('url', ''),
                    published=str(pub_date),
                    sentiment=sentiment,
                    sentiment_score=score,
                    summary=item.get('text', '')[:300] if item.get('text') else '',
                    symbols=[symbol]
                ))
        
        # Add Finnhub news
        if len(news_items) < 5:
            finnhub_news = await api_client.finnhub_news(symbol)
            if finnhub_news:
                for item in finnhub_news[:5]:
                    sentiment, score = self.analyze_sentiment(item.get('headline', ''))
                    # Convert Unix timestamp to ISO string if needed
                    pub_date = item.get('datetime', '')
                    if isinstance(pub_date, (int, float)):
                        pub_date = datetime.fromtimestamp(pub_date, tz=timezone.utc).isoformat()
                    news_items.append(NewsItem(
                        title=item.get('headline', ''),
                        source=item.get('source', 'Unknown'),
                        url=item.get('url', ''),
                        published=str(pub_date),
                        sentiment=sentiment,
                        sentiment_score=score,
                        summary=item.get('summary', ''),
                        symbols=[symbol]
                    ))
        
        if len(news_items) < 5:
            polygon_news = await api_client.polygon_news(symbol, limit=5)
            if polygon_news:
                for item in polygon_news:
                    sentiment, score = self.analyze_sentiment(item.get('title', ''))
                    news_items.append(NewsItem(
                        title=item.get('title', ''),
                        source=item.get('publisher', {}).get('name', 'Unknown'),
                        url=item.get('article_url', ''),
                        published=str(item.get('published_utc', '')),
                        sentiment=sentiment,
                        sentiment_score=score,
                        summary=item.get('description', ''),
                        symbols=item.get('tickers', [])
                    ))
        
        return news_items[:10]
    
    async def get_market_news(self) -> List[NewsItem]:
        """Get general market news"""
        news_items = []
        
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
    import anthropic

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
        # Load conversation history from MongoDB (current user message already saved by route handler)
        history = await db.chat_history.find(
            {"session_id": session_id},
            {"role": 1, "content": 1, "timestamp": 1}
        ).sort("timestamp", 1).limit(50).to_list(50)

        messages = [{"role": h["role"], "content": h["content"]} for h in history]

        client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_message,
            messages=messages
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        return f"I apologize, but I encountered an error. Please try again. Error: {str(e)}"

# ===================== ROUTES =====================

# Access Control
@api_router.post("/auth/access", response_model=AccessResponse)
async def verify_access_code(request: AccessRequest):
    """Verify access code and return session token"""
    if validate_access_code(request.code, request.username):
        token = generate_token()
        _valid_tokens[token] = datetime.now() + timedelta(hours=24)
        
        await db.access_logs.insert_one({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": True
        })
        
        return AccessResponse(success=True, token=token, message="Access granted")
    
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

# Universe Management
@api_router.get("/universe/stats")
async def get_universe_stats(auth: bool = Depends(verify_access)):
    """Get universe statistics"""
    return await universe_manager.get_universe_stats()

@api_router.post("/universe/refresh")
async def refresh_universe(background_tasks: BackgroundTasks, auth: bool = Depends(verify_access)):
    """Trigger universe refresh in background"""
    background_tasks.add_task(universe_manager.load_universe, True)
    return {"message": "Universe refresh started", "status": "processing"}

@api_router.post("/investments/refresh")
async def refresh_investment_signals(
    background_tasks: BackgroundTasks,
    limit: int = Query(default=1000, ge=100, le=1500),
    auth: bool = Depends(verify_access)
):
    """Trigger investment signals refresh for 1000+ stocks using enhanced engine"""
    
    async def refresh_with_enhanced_engine(limit: int):
        """Background task to refresh signals using enhanced engine with rate limit handling"""
        symbols = universe_manager.CORE_UNIVERSE[:limit]
        logger.info(f"Enhanced refresh: analyzing {len(symbols)} stocks in batches...")
        
        all_signals = []
        batch_size = 5  # Smaller batch to avoid rate limits
        delay_between_batches = 1.5  # Longer delay between batches
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            try:
                batch_signals = await enhanced_investment_engine.batch_analyze(batch, batch_size=batch_size)
                all_signals.extend(batch_signals)
                
                # Store each batch immediately to preserve progress
                for signal in batch_signals:
                    await db.investment_signals.update_one(
                        {"symbol": signal.symbol},
                        {"$set": convert_to_legacy_format(signal)},
                        upsert=True
                    )
                
                logger.info(f"Processed batch {i//batch_size + 1}/{(len(symbols) + batch_size - 1)//batch_size}, total signals: {len(all_signals)}")
                
            except Exception as e:
                logger.error(f"Batch {i//batch_size + 1} failed: {e}")
                continue
            
            # Delay between batches to avoid rate limits
            if i + batch_size < len(symbols):
                await asyncio.sleep(delay_between_batches)
        
        logger.info(f"Completed refresh: {len(all_signals)} investment signals stored")
        return len(all_signals)
    
    background_tasks.add_task(refresh_with_enhanced_engine, limit)
    return {"message": f"Refreshing signals for up to {limit} stocks with enhanced engine (background task)", "status": "processing"}

# Trading
@api_router.get("/trading/scan")
async def scan_trading(auth: bool = Depends(verify_access)):
    """Scan market for trading opportunities"""
    return await trading_engine.scan_trading_opportunities()

@api_router.post("/trading/refresh")
async def refresh_trading_signals(
    background_tasks: BackgroundTasks,
    limit: int = Query(default=1000, ge=50, le=1500),
    auth: bool = Depends(verify_access)
):
    """Trigger trading signals refresh for full universe using background batching"""
    background_tasks.add_task(trading_engine.refresh_trading_signals, limit)
    return {"message": f"Scanning {limit} stocks for trading signals (background task)", "status": "processing"}

@api_router.get("/trading/analyze/{symbol}")
async def analyze_trading(symbol: str, auth: bool = Depends(verify_access)):
    """Analyze specific symbol for trading"""
    signal = await trading_engine.analyze_for_trading(symbol.upper())
    if not signal:
        raise HTTPException(status_code=404, detail=f"Unable to analyze {symbol}")
    return signal

# Investments (Enhanced)
@api_router.get("/investments/scan")
async def scan_investments(auth: bool = Depends(verify_access)):
    """Scan market for investment opportunities with dynamic thresholds"""
    # Check if we have cached signals
    total = await db.investment_signals.count_documents({})
    
    if total > 50:
        # Use cached data - get all available (up to 1500), excluding dead tickers
        cursor = db.investment_signals.find(
            {"dead_ticker": {"$ne": True}}, {"_id": 0}
        ).sort("overall_score", -1).limit(1500)
        all_signals = await cursor.to_list(length=1500)
        
        # Apply dynamic percentile-based categorization with valuation overrides
        for i, s in enumerate(all_signals):
            percentile = ((len(all_signals) - i) / len(all_signals)) * 100
            score = s.get("overall_score", 0)
            
            # Check valuation — extract upside
            val_summary = s.get("valuation_summary", {}) or {}
            upside_str = val_summary.get("upside_potential", "") or s.get("upside_potential", "")
            upside_val = None
            if upside_str:
                try:
                    upside_val = float(str(upside_str).replace("%", "").replace("+", ""))
                except (ValueError, TypeError):
                    pass
            
            val_class = val_summary.get("classification", "") or ""
            is_severely_overvalued = (upside_val is not None and upside_val < -25) or val_class == "Overvalued"
            
            # OVERRIDE: Never assign "Buy" to severely overvalued stocks
            if is_severely_overvalued:
                s["category"] = "Overpriced"
                s["signal"] = "Hold" if score >= 40 else "Sell"
            elif percentile >= 90 and score >= 60:
                s["category"] = "Hot"
                s["signal"] = "Buy"
            elif percentile >= 75 and score >= 55:
                s["category"] = "Bullish"
                s["signal"] = "Buy"
            # Keep existing category for others
        
        signals = all_signals
    else:
        # Analyze on demand - use larger universe
        universe = universe_manager.CORE_UNIVERSE[:500]
        logger.info(f"No cache, analyzing {len(universe)} stocks on demand...")
        
        analyzed = await enhanced_investment_engine.batch_analyze(universe, batch_size=10)
        signals = [convert_to_legacy_format(s) for s in analyzed]
        
        # Store in cache
        for signal in signals:
            await db.investment_signals.update_one(
                {"symbol": signal["symbol"]},
                {"$set": signal},
                upsert=True
            )
    
    # Categorize results - return ALL stocks in each category
    hot = [s for s in signals if s.get("category") == "Hot"]
    bullish = [s for s in signals if s.get("category") == "Bullish"]
    undervalued = [s for s in signals if s.get("category") == "Undervalued"]
    bearish = [s for s in signals if s.get("category") == "Bearish"]
    overpriced = [s for s in signals if s.get("category") == "Overpriced"]
    watch = [s for s in signals if s.get("category") == "Watch"]
    avoid = [s for s in signals if s.get("signal") == "Sell"]
    
    return {
        "hot": sorted(hot, key=lambda x: x.get("overall_score", 0), reverse=True),
        "bullish": sorted(bullish, key=lambda x: x.get("overall_score", 0), reverse=True),
        "undervalued": sorted(undervalued, key=lambda x: x.get("overall_score", 0), reverse=True),
        "watch": sorted(watch, key=lambda x: x.get("overall_score", 0), reverse=True),
        "bearish": sorted(bearish, key=lambda x: x.get("overall_score", 0), reverse=True),
        "overpriced": sorted(overpriced, key=lambda x: x.get("overall_score", 0), reverse=True),
        "avoid": sorted(avoid, key=lambda x: x.get("overall_score", 0), reverse=True),
        "all": sorted(signals, key=lambda x: x.get("overall_score", 0), reverse=True),
        "total_analyzed": len(signals),
        "category_counts": {
            "hot": len(hot),
            "bullish": len(bullish),
            "undervalued": len(undervalued),
            "watch": len(watch),
            "bearish": len(bearish),
            "overpriced": len(overpriced),
            "avoid": len(avoid)
        }
    }

@api_router.get("/investments/browse")
async def browse_investments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=10, le=100),
    sort_by: str = Query(default="overall_score"),
    sort_dir: str = Query(default="desc"),
    min_market_cap: Optional[float] = None,
    max_market_cap: Optional[float] = None,
    sectors: Optional[str] = None,  # Comma-separated
    countries: Optional[str] = None,  # Comma-separated
    min_valuation: Optional[float] = None,
    min_quality: Optional[float] = None,
    min_growth: Optional[float] = None,
    min_score: Optional[float] = None,
    signals: Optional[str] = None,  # Comma-separated
    categories: Optional[str] = None,  # Comma-separated
    auth: bool = Depends(verify_access)
):
    """Browse investment signals with filtering and pagination"""
    
    filters = InvestmentFilters(
        min_market_cap=min_market_cap,
        max_market_cap=max_market_cap,
        sectors=sectors.split(",") if sectors else None,
        countries=countries.split(",") if countries else None,
        min_valuation_score=min_valuation,
        min_quality_score=min_quality,
        min_growth_score=min_growth,
        min_overall_score=min_score,
        signals=signals.split(",") if signals else None,
        categories=categories.split(",") if categories else None
    )
    
    return await investment_engine.get_cached_signals(
        page=page,
        page_size=page_size,
        filters=filters,
        sort_by=sort_by,
        sort_dir=sort_dir
    )

@api_router.get("/investments/filters")
async def get_investment_filters(auth: bool = Depends(verify_access)):
    """Get available filter options"""
    
    # Get unique sectors
    sectors = await db.investment_signals.distinct("sector")
    sectors = [s for s in sectors if s]
    
    # Get unique countries
    countries = await db.investment_signals.distinct("country")
    countries = [c for c in countries if c]
    
    # Get signal and category counts
    pipeline = [
        {"$group": {"_id": "$signal", "count": {"$sum": 1}}}
    ]
    signal_counts = {}
    async for doc in db.investment_signals.aggregate(pipeline):
        if doc["_id"]:
            signal_counts[doc["_id"]] = doc["count"]
    
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]
    category_counts = {}
    async for doc in db.investment_signals.aggregate(pipeline):
        if doc["_id"]:
            category_counts[doc["_id"]] = doc["count"]
    
    # Market cap ranges
    market_cap_ranges = [
        {"label": "Mega Cap (>$200B)", "min": 200e9, "max": None},
        {"label": "Large Cap ($10B-$200B)", "min": 10e9, "max": 200e9},
        {"label": "Mid Cap ($2B-$10B)", "min": 2e9, "max": 10e9},
        {"label": "Small Cap ($300M-$2B)", "min": 300e6, "max": 2e9},
        {"label": "Micro Cap (<$300M)", "min": 0, "max": 300e6},
    ]
    
    total = await db.investment_signals.count_documents({})
    
    return {
        "total_signals": total,
        "sectors": sorted(sectors),
        "countries": sorted(countries),
        "signals": signal_counts,
        "categories": category_counts,
        "market_cap_ranges": market_cap_ranges
    }

@api_router.get("/investments/analyze/{symbol}")
async def analyze_investment(symbol: str, auth: bool = Depends(verify_access)):
    """Analyze specific symbol for investment with full explanations"""
    signal = await enhanced_investment_engine.analyze_stock(symbol.upper())
    if not signal:
        raise HTTPException(status_code=404, detail=f"Unable to analyze {symbol}")
    return convert_to_legacy_format(signal)

@api_router.get("/investments/detailed/{symbol}")
async def detailed_investment_analysis(symbol: str, auth: bool = Depends(verify_access)):
    """Get comprehensive investment analysis with all explanations"""
    signal = await enhanced_investment_engine.analyze_stock(symbol.upper())
    if not signal:
        raise HTTPException(status_code=404, detail=f"Unable to analyze {symbol}")
    return signal.dict()

@api_router.get("/investments/audit")
async def audit_investment_scores(auth: bool = Depends(verify_access)):
    """Audit score distribution across all cached signals"""
    import statistics
    
    cursor = db.investment_signals.find({}, {"_id": 0, "symbol": 1, "overall_score": 1, "valuation_score": 1, 
                                             "quality_score": 1, "growth_score": 1, "financial_strength": 1,
                                             "risk_score": 1, "category": 1, "signal": 1})
    signals = await cursor.to_list(length=500)
    
    if not signals:
        return {"error": "No signals found"}
    
    scores = [s.get("overall_score", 0) for s in signals]
    
    # Score bands
    bands = {
        "80+": len([s for s in scores if s >= 80]),
        "70-79": len([s for s in scores if 70 <= s < 80]),
        "60-69": len([s for s in scores if 60 <= s < 70]),
        "50-59": len([s for s in scores if 50 <= s < 60]),
        "40-49": len([s for s in scores if 40 <= s < 50]),
        "0-39": len([s for s in scores if s < 40]),
    }
    
    # Categories
    categories = {}
    for s in signals:
        cat = s.get("category", "Unknown")
        categories[cat] = categories.get(cat, 0) + 1
    
    # Signals
    signal_types = {}
    for s in signals:
        sig = s.get("signal", "Unknown")
        signal_types[sig] = signal_types.get(sig, 0) + 1
    
    # Top/bottom
    sorted_signals = sorted(signals, key=lambda x: x.get("overall_score", 0), reverse=True)
    
    return {
        "total_stocks": len(signals),
        "statistics": {
            "average_score": round(statistics.mean(scores), 1),
            "median_score": round(statistics.median(scores), 1),
            "min_score": round(min(scores), 1),
            "max_score": round(max(scores), 1),
            "std_dev": round(statistics.stdev(scores), 1) if len(scores) > 1 else 0
        },
        "score_bands": bands,
        "categories": categories,
        "signals": signal_types,
        "top_10": [{"symbol": s["symbol"], "score": s.get("overall_score")} for s in sorted_signals[:10]],
        "bottom_10": [{"symbol": s["symbol"], "score": s.get("overall_score")} for s in sorted_signals[-10:]]
    }

@api_router.get("/investments/sanity-check")
async def sanity_check_stocks(auth: bool = Depends(verify_access)):
    """Run sanity check on specific benchmark stocks"""
    test_stocks = ["GOOGL", "MSFT", "JPM", "V", "COST", "JNJ", "XOM", "AAPL"]
    
    results = []
    for symbol in test_stocks:
        signal = await enhanced_investment_engine.analyze_stock(symbol)
        if signal:
            results.append({
                "symbol": symbol,
                "overall_score": signal.overall_score,
                "category": signal.category,
                "signal": signal.signal,
                "percentile_rank": signal.percentile_rank,
                "scores": {
                    "valuation": signal.valuation_score,
                    "quality": signal.quality_score,
                    "growth": signal.growth_score,
                    "financial_strength": signal.financial_strength,
                    "risk": signal.risk_score
                },
                "valuation_summary": signal.valuation_summary.dict(),
                "business_quality": signal.business_quality.dict(),
                "score_drivers": signal.score_drivers.dict(),
                "bull_case": signal.bull_case,
                "bear_case": signal.bear_case,
                "explanation": signal.reasoning
            })
        await asyncio.sleep(0.3)  # Rate limiting
    
    # Apply dynamic thresholds to the batch
    if results:
        # Sort and rank
        results = sorted(results, key=lambda x: x["overall_score"], reverse=True)
        for i, r in enumerate(results):
            r["rank"] = i + 1
            r["percentile"] = ((len(results) - i) / len(results)) * 100
    
    return {
        "test_stocks": results,
        "summary": {
            "average_score": sum(r["overall_score"] for r in results) / len(results) if results else 0,
            "recommended_buys": [r["symbol"] for r in results if r["overall_score"] >= 60],
            "watch_list": [r["symbol"] for r in results if 50 <= r["overall_score"] < 60],
            "avoid": [r["symbol"] for r in results if r["overall_score"] < 50]
        }
    }

# News & Sentiment (Enhanced AI-powered engine)
@api_router.get("/news/breaking")
async def get_breaking_news(auth: bool = Depends(verify_access)):
    """Get high-impact breaking news with catalysts"""
    return await enhanced_news_engine.get_breaking_news()

@api_router.get("/news/overview")
async def get_news_overview(auth: bool = Depends(verify_access)):
    """Get sentiment distribution across all analyzed stocks"""
    return await enhanced_news_engine.get_sentiment_overview()

@api_router.get("/news/analyze/{symbol}")
async def analyze_stock_news(symbol: str, auth: bool = Depends(verify_access)):
    """Get AI-powered news analysis for a stock"""
    return await enhanced_news_engine.analyze_stock(symbol.upper())

@api_router.post("/news/refresh")
async def refresh_news(
    background_tasks: BackgroundTasks,
    symbols: str = Query(default=""),
    auth: bool = Depends(verify_access)
):
    """Refresh news for specific symbols or top trading candidates"""
    if symbols:
        sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    else:
        trading = await db.trading_signals.find(
            {}, {"_id": 0, "symbol": 1}
        ).sort("confidence", -1).limit(30).to_list(30)
        investing = await db.investment_signals.find(
            {"overall_score": {"$gte": 70}}, {"_id": 0, "symbol": 1}
        ).sort("overall_score", -1).limit(30).to_list(30)
        sym_list = list(dict.fromkeys(
            [s["symbol"] for s in trading] + [s["symbol"] for s in investing]
        ))[:50]
    background_tasks.add_task(enhanced_news_engine.batch_analyze, sym_list)
    return {"message": f"Analyzing news for {len(sym_list)} stocks", "symbols": sym_list[:10]}

@api_router.get("/news/{symbol}")
async def get_symbol_news(symbol: str, auth: bool = Depends(verify_access)):
    """Get news for specific symbol (redirects to enhanced analysis)"""
    return await enhanced_news_engine.analyze_stock(symbol.upper())

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
    """Get current positions enriched with ownership/strategy labels."""
    positions = await api_client.alpaca_positions()
    if not positions:
        return []

    # Enrich with ownership + strategy_type from trade log
    symbols = [p.get("symbol", "") for p in positions if p.get("symbol")]
    ownership_map = {}
    if symbols:
        # Get the most recent trade log entry for each symbol to determine ownership
        pipeline = [
            {"$match": {"symbol": {"$in": symbols}}},
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$symbol",
                "ownership": {"$first": "$ownership"},
                "strategy_type": {"$first": "$strategy_type"},
                "confidence": {"$first": "$confidence"},
                "best_setup": {"$first": "$best_setup"},
                "direction": {"$first": "$direction"},
                "entry_reasons": {"$first": "$entry_reasons"},
            }}
        ]
        try:
            cursor = db.auto_trade_log.aggregate(pipeline)
            async for doc in cursor:
                sym = doc["_id"]
                ownership_map[sym] = {
                    "ownership": doc.get("ownership", "unknown"),
                    "strategy_type": doc.get("strategy_type", "unknown"),
                    "confidence": doc.get("confidence", 0),
                    "best_setup": doc.get("best_setup", ""),
                    "direction": doc.get("direction", ""),
                    "entry_reasons": doc.get("entry_reasons", []),
                }
        except Exception:
            pass

        # Also check LT portfolio for long-term positions
        lt_positions = await db.lt_portfolio.find(
            {"symbol": {"$in": symbols}, "status": {"$ne": "closed"}},
            {"_id": 0, "symbol": 1, "bucket": 1, "stage": 1}
        ).to_list(100)
        for ltp in lt_positions:
            sym = ltp["symbol"]
            if sym not in ownership_map or ownership_map[sym].get("ownership") == "unknown":
                ownership_map[sym] = {
                    "ownership": "bot",
                    "strategy_type": "long_term",
                    "bucket": ltp.get("bucket", ""),
                    "stage": ltp.get("stage", 0),
                }

    # Merge into positions
    for p in positions:
        sym = p.get("symbol", "")
        meta = ownership_map.get(sym, {})
        p["ownership"] = meta.get("ownership", "manual")
        p["strategy_type"] = meta.get("strategy_type", "manual")
        p["confidence"] = meta.get("confidence", 0)
        p["best_setup"] = meta.get("best_setup", "")
        p["entry_reasons"] = meta.get("entry_reasons", [])
        # Compose display label
        own = p["ownership"]
        strat = p["strategy_type"]
        if own == "bot" and strat == "day_trade":
            p["position_label"] = "Day Trade (Bot)"
            p["label_color"] = "amber"
        elif own == "bot" and strat == "long_term":
            p["position_label"] = "Long-Term (Bot)"
            p["label_color"] = "blue"
        elif own == "manual" or strat == "manual":
            p["position_label"] = "Manual / Protected"
            p["label_color"] = "emerald"
        else:
            p["position_label"] = "Unknown"
            p["label_color"] = "slate"

    return positions

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

# ===================== RISK MANAGEMENT =====================

class RiskCalculator:
    """Risk management calculations"""
    
    @staticmethod
    def calculate_position_size(
        account_value: float,
        entry_price: float,
        stop_loss_price: float,
        risk_per_trade: float = 0.02,  # 2% risk per trade
        max_position_pct: float = 0.10  # Max 10% of portfolio
    ) -> Dict:
        """Calculate optimal position size based on risk parameters"""
        
        risk_amount = account_value * risk_per_trade
        risk_per_share = abs(entry_price - stop_loss_price)
        
        if risk_per_share <= 0:
            return {"error": "Stop loss must be different from entry price"}
        
        shares = int(risk_amount / risk_per_share)
        position_value = shares * entry_price
        position_pct = position_value / account_value
        
        # Apply max position limit
        if position_pct > max_position_pct:
            shares = int((account_value * max_position_pct) / entry_price)
            position_value = shares * entry_price
            position_pct = position_value / account_value
        
        return {
            "shares": shares,
            "position_value": round(position_value, 2),
            "position_pct": round(position_pct * 100, 2),
            "risk_amount": round(shares * risk_per_share, 2),
            "risk_pct": round((shares * risk_per_share / account_value) * 100, 2)
        }
    
    @staticmethod
    def calculate_risk_reward(
        entry_price: float,
        stop_loss_price: float,
        take_profit_price: float
    ) -> Dict:
        """Calculate risk/reward ratio"""
        
        risk = abs(entry_price - stop_loss_price)
        reward = abs(take_profit_price - entry_price)
        
        if risk <= 0:
            return {"error": "Invalid stop loss"}
        
        ratio = reward / risk
        
        return {
            "risk": round(risk, 2),
            "reward": round(reward, 2),
            "ratio": round(ratio, 2),
            "ratio_display": f"1:{ratio:.1f}",
            "risk_pct": round((risk / entry_price) * 100, 2),
            "reward_pct": round((reward / entry_price) * 100, 2),
            "quality": "Excellent" if ratio >= 3 else "Good" if ratio >= 2 else "Fair" if ratio >= 1.5 else "Poor"
        }

risk_calculator = RiskCalculator()

class RiskSettingsModel(BaseModel):
    max_position_size: float = Field(default=0.05, ge=0.01, le=0.25)
    max_daily_loss: float = Field(default=0.02, ge=0.01, le=0.10)
    max_weekly_loss: float = Field(default=0.05, ge=0.02, le=0.20)
    max_drawdown: float = Field(default=0.10, ge=0.05, le=0.30)
    min_confidence: float = Field(default=0.60, ge=0.40, le=0.90)
    cash_buffer: float = Field(default=0.10, ge=0.0, le=0.50)
    default_stop_loss_pct: float = Field(default=0.05, ge=0.01, le=0.15)
    default_take_profit_pct: float = Field(default=0.10, ge=0.02, le=0.50)

class PositionSizeRequest(BaseModel):
    account_value: float
    entry_price: float
    stop_loss_price: float
    risk_per_trade: Optional[float] = 0.02
    max_position_pct: Optional[float] = 0.10

class RiskRewardRequest(BaseModel):
    entry_price: float
    stop_loss_price: float
    take_profit_price: float

@api_router.post("/risk/position-size")
async def calculate_position_size(request: PositionSizeRequest, auth: bool = Depends(verify_access)):
    """Calculate optimal position size based on risk parameters"""
    return risk_calculator.calculate_position_size(
        account_value=request.account_value,
        entry_price=request.entry_price,
        stop_loss_price=request.stop_loss_price,
        risk_per_trade=request.risk_per_trade,
        max_position_pct=request.max_position_pct
    )

@api_router.post("/risk/risk-reward")
async def calculate_risk_reward(request: RiskRewardRequest, auth: bool = Depends(verify_access)):
    """Calculate risk/reward ratio"""
    return risk_calculator.calculate_risk_reward(
        entry_price=request.entry_price,
        stop_loss_price=request.stop_loss_price,
        take_profit_price=request.take_profit_price
    )

@api_router.get("/risk/settings")
async def get_risk_settings(auth: bool = Depends(verify_access)):
    """Get user's risk settings"""
    settings = await db.risk_settings.find_one({"_id": "default"}, {"_id": 0})
    if not settings:
        settings = RiskSettingsModel().dict()
    return settings

@api_router.post("/risk/settings")
async def save_risk_settings(settings: RiskSettingsModel, auth: bool = Depends(verify_access)):
    """Save user's risk settings"""
    await db.risk_settings.update_one(
        {"_id": "default"},
        {"$set": settings.dict()},
        upsert=True
    )
    return {"success": True, "message": "Risk settings saved"}

@api_router.get("/risk/daily-status")
async def get_daily_risk_status(auth: bool = Depends(verify_access)):
    """Get current daily risk status"""
    # Get account info
    account = await api_client.alpaca_account()
    if not account:
        return {
            "account_value": 0,
            "daily_pnl": 0,
            "daily_pnl_pct": 0,
            "can_trade": True,
            "risk_status": "unknown"
        }
    
    equity = float(account.get("equity", 0))
    last_equity = float(account.get("last_equity", equity))
    daily_pnl = equity - last_equity
    daily_pnl_pct = (daily_pnl / last_equity * 100) if last_equity > 0 else 0
    
    # Get risk settings
    settings = await db.risk_settings.find_one({"_id": "default"})
    max_daily_loss = settings.get("max_daily_loss", 0.02) if settings else 0.02
    
    # Check if trading should be paused
    can_trade = daily_pnl_pct > -(max_daily_loss * 100)
    
    return {
        "account_value": round(equity, 2),
        "daily_pnl": round(daily_pnl, 2),
        "daily_pnl_pct": round(daily_pnl_pct, 2),
        "max_daily_loss_pct": round(max_daily_loss * 100, 2),
        "can_trade": can_trade,
        "risk_status": "safe" if daily_pnl_pct > 0 else "caution" if can_trade else "stopped"
    }

# ===================== BACKTESTING =====================

class BacktestRequest(BaseModel):
    symbol: str
    strategy: str = "momentum"  # momentum, mean_reversion, breakout, ma_crossover, value
    period: str = "1y"  # 3m, 6m, 1y, 2y, 5y
    initial_capital: float = 10000
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.10

class BacktestEngine:
    """Backtesting engine using up to 30 years of historical data"""
    
    PERIOD_DAYS = {
        "3m": 90,
        "6m": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825,
        "10y": 3650,
        "20y": 7300,
        "30y": 11000
    }
    
    async def get_historical_data(self, symbol: str, days: int) -> List[Dict]:
        """Get historical price data - uses 30yr fetch for longer periods"""
        cache_key = f"historical_{symbol}_{days}"
        cached = get_cached(cache_key, 3600)
        if cached:
            return cached
        
        try:
            if days > 1825:
                # Use 30yr fetch for periods longer than 5 years
                data = await api_client.fmp_historical_30yr(symbol)
            else:
                data = await api_client.fmp_historical(symbol, days=min(days + 50, 5000))
            
            if data and len(data) > 0:
                data = data[:days] if len(data) > days else data
                data = list(reversed(data))  # Oldest first
                set_cached(cache_key, data)
                return data
        except Exception as e:
            logger.error(f"Historical data error for {symbol}: {e}")
        
        return []
    
    async def get_benchmark_return(self, days: int) -> Optional[float]:
        """Get S&P 500 buy & hold return for comparison"""
        try:
            data = await self.get_historical_data("SPY", days)
            if data and len(data) >= 2:
                start = data[0].get("close", 0)
                end = data[-1].get("close", 0)
                if start > 0:
                    return round(((end / start) - 1) * 100, 2)
        except:
            pass
        return None
    
    async def run_backtest(self, request: BacktestRequest) -> Dict:
        """Run a backtest simulation"""
        days = self.PERIOD_DAYS.get(request.period, 365)
        data = await self.get_historical_data(request.symbol.upper(), days)
        
        if len(data) < 20:
            return {"error": f"Insufficient historical data for {request.symbol}"}
        
        # Initialize tracking
        capital = request.initial_capital
        position = None
        trades = []
        equity_curve = []
        wins = 0
        losses = 0
        
        # Calculate indicators
        prices = [d.get("close", d.get("adjClose", 0)) for d in data]
        
        # Simple moving averages
        def sma(data, period):
            if len(data) < period:
                return None
            return sum(data[-period:]) / period
        
        for i in range(20, len(data)):
            current_price = prices[i]
            prev_price = prices[i-1]
            
            # Calculate signals based on strategy
            signal = None
            
            if request.strategy == "momentum":
                # Buy on strong upward momentum
                change_5d = (current_price / prices[i-5] - 1) * 100 if prices[i-5] > 0 else 0
                change_20d = (current_price / prices[i-20] - 1) * 100 if prices[i-20] > 0 else 0
                
                if position is None and change_5d > 3 and change_20d > 5:
                    signal = "buy"
                elif position and (change_5d < -2 or change_20d < 0):
                    signal = "sell"
            
            elif request.strategy == "mean_reversion":
                # Buy when oversold, sell when overbought
                sma20 = sma(prices[:i+1], 20)
                if sma20:
                    deviation = (current_price / sma20 - 1) * 100
                    if position is None and deviation < -5:
                        signal = "buy"
                    elif position and deviation > 3:
                        signal = "sell"
            
            elif request.strategy == "breakout":
                # Buy on breakout above 20-day high
                high_20 = max(prices[i-20:i])
                low_20 = min(prices[i-20:i])
                
                if position is None and current_price > high_20:
                    signal = "buy"
                elif position and current_price < low_20:
                    signal = "sell"
            
            elif request.strategy == "ma_crossover":
                # Buy when 10 SMA crosses above 30 SMA
                sma10 = sma(prices[:i+1], 10)
                sma30 = sma(prices[:i+1], 30) if len(prices[:i+1]) >= 30 else None
                prev_sma10 = sma(prices[:i], 10)
                prev_sma30 = sma(prices[:i], 30) if len(prices[:i]) >= 30 else None
                
                if sma10 and sma30 and prev_sma10 and prev_sma30:
                    if position is None and sma10 > sma30 and prev_sma10 <= prev_sma30:
                        signal = "buy"
                    elif position and sma10 < sma30 and prev_sma10 >= prev_sma30:
                        signal = "sell"
            
            elif request.strategy == "value":
                # Simple value approach - buy dips, hold
                sma50 = sma(prices[:i+1], 50) if len(prices[:i+1]) >= 50 else None
                if sma50:
                    if position is None and current_price < sma50 * 0.95:
                        signal = "buy"
                    elif position and current_price > position["entry"] * (1 + request.take_profit_pct):
                        signal = "sell"
            
            # Check stop loss / take profit
            if position:
                pnl_pct = (current_price / position["entry"] - 1) * 100
                if pnl_pct <= -request.stop_loss_pct * 100:
                    signal = "sell"  # Stop loss hit
                elif pnl_pct >= request.take_profit_pct * 100:
                    signal = "sell"  # Take profit hit
            
            # Execute signals
            if signal == "buy" and position is None:
                shares = int(capital * 0.95 / current_price)  # Use 95% of capital
                if shares > 0:
                    position = {
                        "entry": current_price,
                        "shares": shares,
                        "date": data[i].get("date", "")
                    }
                    capital -= shares * current_price
            
            elif signal == "sell" and position:
                sale_value = position["shares"] * current_price
                pnl = sale_value - (position["shares"] * position["entry"])
                pnl_pct = (current_price / position["entry"] - 1) * 100
                
                trades.append({
                    "entry_date": position["date"],
                    "exit_date": data[i].get("date", ""),
                    "entry_price": round(position["entry"], 2),
                    "exit_price": round(current_price, 2),
                    "shares": position["shares"],
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2)
                })
                
                capital += sale_value
                if pnl > 0:
                    wins += 1
                else:
                    losses += 1
                position = None
            
            # Track equity
            current_equity = capital
            if position:
                current_equity += position["shares"] * current_price
            
            if i % 5 == 0:  # Sample every 5 days
                equity_curve.append({
                    "date": data[i].get("date", ""),
                    "equity": round(current_equity, 2)
                })
        
        # Close any open position
        if position:
            final_price = prices[-1]
            sale_value = position["shares"] * final_price
            pnl = sale_value - (position["shares"] * position["entry"])
            trades.append({
                "entry_date": position["date"],
                "exit_date": data[-1].get("date", ""),
                "entry_price": round(position["entry"], 2),
                "exit_price": round(final_price, 2),
                "shares": position["shares"],
                "pnl": round(pnl, 2),
                "pnl_pct": round((final_price / position["entry"] - 1) * 100, 2)
            })
            capital += sale_value
            if pnl > 0:
                wins += 1
            else:
                losses += 1
        
        # Calculate metrics
        final_value = capital
        total_return = ((final_value / request.initial_capital) - 1) * 100
        total_trades = len(trades)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate max drawdown
        max_equity = request.initial_capital
        max_drawdown = 0
        for point in equity_curve:
            if point["equity"] > max_equity:
                max_equity = point["equity"]
            drawdown = ((max_equity - point["equity"]) / max_equity) * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Calculate Sharpe ratio (simplified)
        if len(trades) > 1:
            returns = [t["pnl_pct"] for t in trades]
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
            std_dev = variance ** 0.5
            sharpe = (avg_return / std_dev) * (12 ** 0.5) if std_dev > 0 else 0
        else:
            sharpe = 0
        
        best_trade = max([t["pnl_pct"] for t in trades]) if trades else 0
        worst_trade = min([t["pnl_pct"] for t in trades]) if trades else 0
        
        # Get S&P 500 benchmark
        benchmark_return = await self.get_benchmark_return(days)
        alpha = round(total_return - (benchmark_return or 0), 2) if benchmark_return is not None else None
        
        # Annualized return
        years = max(days / 365, 0.25)
        annualized = round(((1 + total_return / 100) ** (1 / years) - 1) * 100, 2) if total_return > -100 else -100
        
        return {
            "symbol": request.symbol.upper(),
            "strategy": request.strategy,
            "period": request.period,
            "initial_capital": request.initial_capital,
            "final_value": round(final_value, 2),
            "total_return": round(total_return, 2),
            "annualized_return": annualized,
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe, 2),
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "wins": wins,
            "losses": losses,
            "best_trade": round(best_trade, 2),
            "worst_trade": round(worst_trade, 2),
            "benchmark_return": benchmark_return,
            "alpha": alpha,
            "data_points": len(data),
            "years_tested": round(years, 1),
            "trades": trades[-20:],
            "equity_curve": equity_curve
        }

backtest_engine = BacktestEngine()

@api_router.post("/backtest/run")
async def run_backtest(request: BacktestRequest, auth: bool = Depends(verify_access)):
    """Run a backtest simulation"""
    result = await backtest_engine.run_backtest(request)
    
    # Store backtest result
    await db.backtests.insert_one({
        "symbol": request.symbol.upper(),
        "strategy": request.strategy,
        "period": request.period,
        "result": result,
        "created_at": datetime.now(timezone.utc)
    })
    
    return result

@api_router.get("/backtest/history")
async def get_backtest_history(
    limit: int = Query(default=10, ge=1, le=50),
    auth: bool = Depends(verify_access)
):
    """Get backtest history"""
    cursor = db.backtests.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    results = await cursor.to_list(length=limit)
    return results

@api_router.get("/backtest/strategies")
async def get_backtest_strategies(auth: bool = Depends(verify_access)):
    """Get available backtest strategies"""
    return [
        {
            "id": "momentum",
            "name": "Momentum",
            "description": "Buy on strong upward price momentum, sell on momentum reversal"
        },
        {
            "id": "mean_reversion",
            "name": "Mean Reversion",
            "description": "Buy when price deviates below average, sell when it returns"
        },
        {
            "id": "breakout",
            "name": "Breakout",
            "description": "Buy on breakout above 20-day high, sell on breakdown"
        },
        {
            "id": "ma_crossover",
            "name": "MA Crossover",
            "description": "Buy when 10-day SMA crosses above 30-day SMA"
        },
        {
            "id": "value",
            "name": "Value",
            "description": "Buy on significant dips below 50-day SMA, hold for target"
        }
    ]

# ===================== ALERTS =====================

class AlertType:
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    CHANGE_PCT = "change_pct"
    VOLUME_SPIKE = "volume_spike"
    SIGNAL_CHANGE = "signal_change"

class AlertModel(BaseModel):
    symbol: str
    alert_type: str
    value: float
    enabled: bool = True
    note: Optional[str] = None

class AlertUpdateModel(BaseModel):
    enabled: Optional[bool] = None
    value: Optional[float] = None
    note: Optional[str] = None

@api_router.get("/alerts")
async def get_alerts(auth: bool = Depends(verify_access)):
    """Get all alerts"""
    cursor = db.alerts.find({}, {"_id": 0}).sort("created_at", -1)
    alerts = await cursor.to_list(length=100)
    return alerts

@api_router.post("/alerts")
async def create_alert(alert: AlertModel, auth: bool = Depends(verify_access)):
    """Create a new alert"""
    alert_data = alert.dict()
    alert_data["id"] = str(uuid.uuid4())
    alert_data["symbol"] = alert.symbol.upper()
    alert_data["created_at"] = datetime.now(timezone.utc).isoformat()
    alert_data["triggered"] = False
    alert_data["triggered_at"] = None
    
    await db.alerts.insert_one(alert_data)
    
    # Remove MongoDB _id before returning
    alert_data.pop("_id", None)
    return alert_data

@api_router.put("/alerts/{alert_id}")
async def update_alert(alert_id: str, update: AlertUpdateModel, auth: bool = Depends(verify_access)):
    """Update an alert"""
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    
    if update_data:
        await db.alerts.update_one(
            {"id": alert_id},
            {"$set": update_data}
        )
    
    updated = await db.alerts.find_one({"id": alert_id}, {"_id": 0})
    return updated

@api_router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str, auth: bool = Depends(verify_access)):
    """Delete an alert"""
    result = await db.alerts.delete_one({"id": alert_id})
    return {"success": result.deleted_count > 0}

@api_router.get("/alerts/check")
async def check_alerts(auth: bool = Depends(verify_access)):
    """Check all alerts against current prices and return triggered ones"""
    triggered = []
    
    # Get all enabled alerts
    cursor = db.alerts.find({"enabled": True, "triggered": False})
    alerts = await cursor.to_list(length=100)
    
    if not alerts:
        return {"triggered": [], "checked": 0}
    
    # Group by symbol
    symbols = list(set(a["symbol"] for a in alerts))
    
    # Get current prices
    quotes = {}
    for symbol in symbols:
        quote = await api_client.fmp_quote(symbol)
        if quote:
            quotes[symbol] = quote
    
    # Check each alert
    for alert in alerts:
        symbol = alert["symbol"]
        quote = quotes.get(symbol)
        
        if not quote:
            continue
        
        current_price = quote.get("price", 0)
        change_pct = quote.get("changesPercentage", 0)
        volume = quote.get("volume", 0)
        avg_volume = quote.get("avgVolume", 1)
        
        should_trigger = False
        trigger_message = ""
        
        if alert["alert_type"] == AlertType.PRICE_ABOVE:
            if current_price >= alert["value"]:
                should_trigger = True
                trigger_message = f"{symbol} reached ${current_price:.2f} (target: ${alert['value']:.2f})"
        
        elif alert["alert_type"] == AlertType.PRICE_BELOW:
            if current_price <= alert["value"]:
                should_trigger = True
                trigger_message = f"{symbol} dropped to ${current_price:.2f} (target: ${alert['value']:.2f})"
        
        elif alert["alert_type"] == AlertType.CHANGE_PCT:
            if abs(change_pct) >= alert["value"]:
                should_trigger = True
                trigger_message = f"{symbol} moved {change_pct:+.1f}% (threshold: {alert['value']}%)"
        
        elif alert["alert_type"] == AlertType.VOLUME_SPIKE:
            vol_ratio = volume / avg_volume if avg_volume > 0 else 1
            if vol_ratio >= alert["value"]:
                should_trigger = True
                trigger_message = f"{symbol} volume spike: {vol_ratio:.1f}x average"
        
        if should_trigger:
            # Mark as triggered
            await db.alerts.update_one(
                {"id": alert["id"]},
                {
                    "$set": {
                        "triggered": True,
                        "triggered_at": datetime.now(timezone.utc).isoformat(),
                        "trigger_price": current_price,
                        "trigger_message": trigger_message
                    }
                }
            )
            
            # Add to alert history
            await db.alert_history.insert_one({
                "alert_id": alert["id"],
                "symbol": symbol,
                "alert_type": alert["alert_type"],
                "value": alert["value"],
                "trigger_price": current_price,
                "trigger_message": trigger_message,
                "triggered_at": datetime.now(timezone.utc).isoformat()
            })
            
            triggered.append({
                "id": alert["id"],
                "symbol": symbol,
                "message": trigger_message,
                "price": current_price
            })
    
    return {"triggered": triggered, "checked": len(alerts)}

@api_router.get("/alerts/history")
async def get_alert_history(
    limit: int = Query(default=50, ge=1, le=200),
    auth: bool = Depends(verify_access)
):
    """Get alert trigger history"""
    cursor = db.alert_history.find({}, {"_id": 0}).sort("triggered_at", -1).limit(limit)
    history = await cursor.to_list(length=limit)
    return history

@api_router.post("/alerts/{alert_id}/reset")
async def reset_alert(alert_id: str, auth: bool = Depends(verify_access)):
    """Reset a triggered alert so it can trigger again"""
    await db.alerts.update_one(
        {"id": alert_id},
        {
            "$set": {
                "triggered": False,
                "triggered_at": None,
                "trigger_price": None,
                "trigger_message": None
            }
        }
    )
    return {"success": True}

@api_router.get("/alerts/types")
async def get_alert_types(auth: bool = Depends(verify_access)):
    """Get available alert types"""
    return [
        {"id": "price_above", "name": "Price Above", "description": "Trigger when price rises above target", "unit": "$"},
        {"id": "price_below", "name": "Price Below", "description": "Trigger when price drops below target", "unit": "$"},
        {"id": "change_pct", "name": "% Change", "description": "Trigger on daily percentage change", "unit": "%"},
        {"id": "volume_spike", "name": "Volume Spike", "description": "Trigger when volume exceeds X times average", "unit": "x"}
    ]

# ===================== WATCHLIST =====================

class WatchlistAddModel(BaseModel):
    symbol: str
    source: str = "manual"  # manual, trading, investments
    note: Optional[str] = None

@api_router.get("/watchlist")
async def get_watchlist(auth: bool = Depends(verify_access)):
    """Get all watchlist items with current data"""
    cursor = db.watchlist.find({}, {"_id": 0}).sort("added_at", -1)
    items = await cursor.to_list(length=100)
    
    if not items:
        return []
    
    # Enrich with current data
    enriched = []
    for item in items:
        symbol = item["symbol"]
        
        # Get cached investment signal if available
        signal = await db.investment_signals.find_one({"symbol": symbol}, {"_id": 0})
        
        # Get current quote
        quote = await api_client.fmp_quote(symbol)
        
        enriched_item = {
            "id": item["id"],
            "symbol": symbol,
            "source": item.get("source", "manual"),
            "note": item.get("note"),
            "added_at": item["added_at"],
            # Quote data
            "name": quote.get("name", item.get("name", symbol)) if quote else item.get("name", symbol),
            "price": quote.get("price", 0) if quote else 0,
            "change": quote.get("change", 0) if quote else 0,
            "change_pct": quote.get("changesPercentage", 0) if quote else 0,
            # Signal data (if available)
            "score": signal.get("total_score", 0) if signal else None,
            "signal": signal.get("signal", "N/A") if signal else "N/A",
            "category": signal.get("category", "Unknown") if signal else "Unknown",
            "confidence": signal.get("confidence", 0) if signal else None,
            "upside": signal.get("upside_potential", 0) if signal else None,
            "sector": signal.get("sector", "Unknown") if signal else (quote.get("sector") if quote else "Unknown")
        }
        enriched.append(enriched_item)
    
    return enriched

@api_router.post("/watchlist")
async def add_to_watchlist(item: WatchlistAddModel, auth: bool = Depends(verify_access)):
    """Add a stock to watchlist"""
    symbol = item.symbol.upper()
    
    # Check if already in watchlist
    existing = await db.watchlist.find_one({"symbol": symbol})
    if existing:
        return {"success": False, "message": f"{symbol} is already in your watchlist"}
    
    # Get basic info
    quote = await api_client.fmp_quote(symbol)
    if not quote:
        return {"success": False, "message": f"Could not find stock: {symbol}"}
    
    watchlist_item = {
        "id": str(uuid.uuid4()),
        "symbol": symbol,
        "name": quote.get("name", symbol),
        "source": item.source,
        "note": item.note,
        "added_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.watchlist.insert_one(watchlist_item)
    watchlist_item.pop("_id", None)
    
    return {"success": True, "item": watchlist_item, "message": f"{symbol} added to watchlist"}

@api_router.delete("/watchlist/all")
async def clear_watchlist(auth: bool = Depends(verify_access)):
    """Remove all stocks from watchlist"""
    result = await db.watchlist.delete_many({})
    return {"success": True, "removed": result.deleted_count}

@api_router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str, auth: bool = Depends(verify_access)):
    """Remove a stock from watchlist"""
    symbol = symbol.upper()
    result = await db.watchlist.delete_one({"symbol": symbol})
    return {"success": result.deleted_count > 0, "message": f"{symbol} removed from watchlist" if result.deleted_count > 0 else f"{symbol} not found in watchlist"}

@api_router.get("/watchlist/check/{symbol}")
async def check_watchlist(symbol: str, auth: bool = Depends(verify_access)):
    """Check if a symbol is in watchlist"""
    symbol = symbol.upper()
    exists = await db.watchlist.find_one({"symbol": symbol})
    return {"in_watchlist": exists is not None}

@api_router.post("/watchlist/refresh")
async def refresh_watchlist(auth: bool = Depends(verify_access)):
    """Refresh all watchlist items with latest data"""
    cursor = db.watchlist.find({}, {"_id": 0})
    items = await cursor.to_list(length=100)
    
    refreshed = []
    for item in items:
        symbol = item["symbol"]
        
        # Get fresh quote
        quote = await api_client.fmp_quote(symbol)
        
        # Get cached signal
        signal = await db.investment_signals.find_one({"symbol": symbol}, {"_id": 0})
        
        refreshed.append({
            "symbol": symbol,
            "name": quote.get("name", symbol) if quote else symbol,
            "price": quote.get("price", 0) if quote else 0,
            "change": quote.get("change", 0) if quote else 0,
            "change_pct": quote.get("changesPercentage", 0) if quote else 0,
            "score": signal.get("total_score") if signal else None,
            "signal": signal.get("signal", "N/A") if signal else "N/A",
            "category": signal.get("category", "Unknown") if signal else "Unknown"
        })
    
    return {"items": refreshed, "count": len(refreshed)}

@api_router.put("/watchlist/{symbol}/note")
async def update_watchlist_note(symbol: str, note: str = "", auth: bool = Depends(verify_access)):
    """Update note for a watchlist item"""
    symbol = symbol.upper()
    result = await db.watchlist.update_one(
        {"symbol": symbol},
        {"$set": {"note": note}}
    )
    return {"success": result.modified_count > 0}

# ===================== PORTFOLIO ANALYTICS =====================

class PortfolioAnalytics:
    """Portfolio analytics and performance calculations"""
    
    async def get_portfolio_history(self, period: str = "1M") -> List[Dict]:
        """Get portfolio history from Alpaca"""
        period_map = {"1D": "1D", "1W": "1W", "1M": "1M", "3M": "3M", "1Y": "1A", "ALL": "all"}
        alpaca_period = period_map.get(period, "1M")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{api_client.alpaca_url}/v2/account/portfolio/history",
                    headers=api_client.alpaca_headers,
                    params={"period": alpaca_period, "timeframe": "1D"}
                )
                if response.status_code == 200:
                    data = response.json()
                    timestamps = data.get("timestamp", [])
                    equity = data.get("equity", [])
                    profit_loss = data.get("profit_loss", [])
                    profit_loss_pct = data.get("profit_loss_pct", [])
                    
                    history = []
                    for i in range(len(timestamps)):
                        if timestamps[i] and equity[i]:
                            history.append({
                                "date": datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d"),
                                "equity": equity[i],
                                "pnl": profit_loss[i] if i < len(profit_loss) else 0,
                                "pnl_pct": profit_loss_pct[i] * 100 if i < len(profit_loss_pct) else 0
                            })
                    return history
        except Exception as e:
            logger.error(f"Portfolio history error: {e}")
        
        return []
    
    async def get_trade_history(self) -> List[Dict]:
        """Get closed trades from Alpaca"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{api_client.alpaca_url}/v2/orders",
                    headers=api_client.alpaca_headers,
                    params={"status": "closed", "limit": 500}
                )
                if response.status_code == 200:
                    orders = response.json()
                    trades = []
                    for order in orders:
                        if order.get("filled_at"):
                            trades.append({
                                "id": order.get("id"),
                                "symbol": order.get("symbol"),
                                "side": order.get("side"),
                                "qty": float(order.get("filled_qty", 0)),
                                "avg_price": float(order.get("filled_avg_price", 0)),
                                "filled_at": order.get("filled_at"),
                                "order_type": order.get("type")
                            })
                    return trades
        except Exception as e:
            logger.error(f"Trade history error: {e}")
        
        return []
    
    def calculate_drawdown(self, equity_history: List[Dict]) -> List[Dict]:
        """Calculate drawdown series"""
        if not equity_history:
            return []
        
        drawdowns = []
        peak = equity_history[0]["equity"]
        
        for point in equity_history:
            equity = point["equity"]
            if equity > peak:
                peak = equity
            
            drawdown = ((peak - equity) / peak) * 100 if peak > 0 else 0
            drawdowns.append({
                "date": point["date"],
                "drawdown": round(drawdown, 2),
                "equity": equity,
                "peak": peak
            })
        
        return drawdowns
    
    def calculate_win_rate_trend(self, trades: List[Dict]) -> Dict:
        """Calculate win rate trends"""
        if not trades:
            return {"overall": 0, "trend": [], "by_strategy": {}}
        
        # Match buys and sells by symbol
        positions = {}
        completed_trades = []
        
        for trade in sorted(trades, key=lambda x: x.get("filled_at", "")):
            symbol = trade["symbol"]
            
            if trade["side"] == "buy":
                if symbol not in positions:
                    positions[symbol] = []
                positions[symbol].append(trade)
            elif trade["side"] == "sell" and symbol in positions and positions[symbol]:
                buy_trade = positions[symbol].pop(0)
                buy_price = buy_trade["avg_price"]
                sell_price = trade["avg_price"]
                pnl = (sell_price - buy_price) * trade["qty"]
                pnl_pct = ((sell_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0
                
                completed_trades.append({
                    "symbol": symbol,
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "qty": trade["qty"],
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "date": trade.get("filled_at", "")[:10],
                    "win": pnl > 0
                })
        
        if not completed_trades:
            return {"overall": 0, "trend": [], "by_strategy": {}, "total_trades": 0}
        
        # Overall win rate
        wins = sum(1 for t in completed_trades if t["win"])
        total = len(completed_trades)
        overall_win_rate = (wins / total) * 100 if total > 0 else 0
        
        # Rolling win rate (last 20 trades)
        rolling_window = 20
        trend = []
        for i in range(min(rolling_window, len(completed_trades)), len(completed_trades) + 1):
            window = completed_trades[max(0, i - rolling_window):i]
            window_wins = sum(1 for t in window if t["win"])
            window_rate = (window_wins / len(window)) * 100 if window else 0
            if i <= len(completed_trades) and i > 0:
                trend.append({
                    "trade_num": i,
                    "win_rate": round(window_rate, 1),
                    "date": completed_trades[i-1]["date"] if i > 0 else ""
                })
        
        return {
            "overall": round(overall_win_rate, 1),
            "wins": wins,
            "losses": total - wins,
            "total_trades": total,
            "trend": trend,
            "completed_trades": completed_trades[-50:]  # Last 50 trades
        }
    
    async def get_sector_allocation(self, positions: List[Dict]) -> List[Dict]:
        """Calculate sector allocation from positions"""
        if not positions:
            return []
        
        sector_values = {}
        total_value = 0
        
        for pos in positions:
            symbol = pos.get("symbol", "")
            market_value = float(pos.get("market_value", 0))
            total_value += abs(market_value)
            
            # Get sector from cached investment signal
            signal = await db.investment_signals.find_one({"symbol": symbol})
            sector = signal.get("sector", "Unknown") if signal else "Unknown"
            
            if sector not in sector_values:
                sector_values[sector] = 0
            sector_values[sector] += abs(market_value)
        
        allocation = []
        for sector, value in sorted(sector_values.items(), key=lambda x: -x[1]):
            allocation.append({
                "sector": sector,
                "value": round(value, 2),
                "percentage": round((value / total_value) * 100, 1) if total_value > 0 else 0
            })
        
        return allocation
    
    def get_pnl_breakdown(self, positions: List[Dict], completed_trades: List[Dict]) -> Dict:
        """Get P&L breakdown: realized vs unrealized"""
        # Unrealized from current positions
        unrealized_pnl = sum(float(p.get("unrealized_pl", 0)) for p in positions)
        unrealized_pnl_pct = sum(float(p.get("unrealized_plpc", 0)) * 100 for p in positions) / len(positions) if positions else 0
        
        # Realized from completed trades
        realized_pnl = sum(t.get("pnl", 0) for t in completed_trades)
        total_invested = sum(t.get("buy_price", 0) * t.get("qty", 0) for t in completed_trades)
        realized_pnl_pct = (realized_pnl / total_invested) * 100 if total_invested > 0 else 0
        
        # Calculate average trade return
        avg_trade_return = sum(t.get("pnl_pct", 0) for t in completed_trades) / len(completed_trades) if completed_trades else 0
        
        # Best and worst trades
        best_trade = max(completed_trades, key=lambda x: x.get("pnl_pct", 0)) if completed_trades else None
        worst_trade = min(completed_trades, key=lambda x: x.get("pnl_pct", 0)) if completed_trades else None
        
        return {
            "realized_pnl": round(realized_pnl, 2),
            "realized_pnl_pct": round(realized_pnl_pct, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
            "total_pnl": round(realized_pnl + unrealized_pnl, 2),
            "avg_trade_return": round(avg_trade_return, 2),
            "best_trade": {
                "symbol": best_trade["symbol"],
                "pnl_pct": round(best_trade["pnl_pct"], 2)
            } if best_trade else None,
            "worst_trade": {
                "symbol": worst_trade["symbol"],
                "pnl_pct": round(worst_trade["pnl_pct"], 2)
            } if worst_trade else None
        }
    
    def get_strategy_performance(self, backtests: List[Dict]) -> List[Dict]:
        """Get performance by strategy from backtest history"""
        strategy_stats = {}
        
        for bt in backtests:
            strategy = bt.get("strategy", "unknown")
            result = bt.get("result", {})
            
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {
                    "runs": 0,
                    "total_return": 0,
                    "total_win_rate": 0,
                    "avg_drawdown": 0
                }
            
            stats = strategy_stats[strategy]
            stats["runs"] += 1
            stats["total_return"] += result.get("total_return", 0)
            stats["total_win_rate"] += result.get("win_rate", 0)
            stats["avg_drawdown"] += result.get("max_drawdown", 0)
        
        performance = []
        for strategy, stats in strategy_stats.items():
            runs = stats["runs"]
            if runs > 0:
                performance.append({
                    "strategy": strategy,
                    "avg_return": round(stats["total_return"] / runs, 2),
                    "avg_win_rate": round(stats["total_win_rate"] / runs, 1),
                    "avg_drawdown": round(stats["avg_drawdown"] / runs, 2),
                    "runs": runs
                })
        
        return sorted(performance, key=lambda x: -x["avg_return"])

portfolio_analytics = PortfolioAnalytics()

@api_router.get("/portfolio/history")
async def get_portfolio_history(
    period: str = Query(default="1M", regex="^(1D|1W|1M|3M|1Y|ALL)$"),
    auth: bool = Depends(verify_access)
):
    """Get portfolio equity history"""
    history = await portfolio_analytics.get_portfolio_history(period)
    return {"history": history, "period": period}

@api_router.get("/portfolio/drawdown")
async def get_portfolio_drawdown(
    period: str = Query(default="1M"),
    auth: bool = Depends(verify_access)
):
    """Get portfolio drawdown history"""
    history = await portfolio_analytics.get_portfolio_history(period)
    drawdowns = portfolio_analytics.calculate_drawdown(history)
    
    max_drawdown = max((d["drawdown"] for d in drawdowns), default=0)
    
    return {
        "drawdowns": drawdowns,
        "max_drawdown": round(max_drawdown, 2),
        "period": period
    }

@api_router.get("/portfolio/win-rate")
async def get_portfolio_win_rate(auth: bool = Depends(verify_access)):
    """Get win rate analysis"""
    trades = await portfolio_analytics.get_trade_history()
    analysis = portfolio_analytics.calculate_win_rate_trend(trades)
    return analysis

@api_router.get("/portfolio/sector-allocation")
async def get_sector_allocation(auth: bool = Depends(verify_access)):
    """Get portfolio sector allocation"""
    positions = await api_client.alpaca_positions() or []
    allocation = await portfolio_analytics.get_sector_allocation(positions)
    return {"allocation": allocation, "position_count": len(positions)}

@api_router.get("/portfolio/pnl-breakdown")
async def get_pnl_breakdown(auth: bool = Depends(verify_access)):
    """Get P&L breakdown: realized vs unrealized"""
    positions = await api_client.alpaca_positions() or []
    trades = await portfolio_analytics.get_trade_history()
    win_analysis = portfolio_analytics.calculate_win_rate_trend(trades)
    completed_trades = win_analysis.get("completed_trades", [])
    
    breakdown = portfolio_analytics.get_pnl_breakdown(positions, completed_trades)
    return breakdown

@api_router.get("/portfolio/strategy-performance")
async def get_strategy_performance(auth: bool = Depends(verify_access)):
    """Get performance by backtest strategy"""
    cursor = db.backtests.find({}, {"_id": 0}).sort("created_at", -1).limit(100)
    backtests = await cursor.to_list(length=100)
    performance = portfolio_analytics.get_strategy_performance(backtests)
    return {"performance": performance}

@api_router.get("/portfolio/analytics")
async def get_portfolio_analytics(
    period: str = Query(default="1M"),
    auth: bool = Depends(verify_access)
):
    """Get comprehensive portfolio analytics"""
    # Fetch all data in parallel
    history_task = portfolio_analytics.get_portfolio_history(period)
    trades_task = portfolio_analytics.get_trade_history()
    positions_task = api_client.alpaca_positions()
    backtests_cursor = db.backtests.find({}, {"_id": 0}).sort("created_at", -1).limit(100)
    
    history = await history_task
    trades = await trades_task
    positions = await positions_task or []
    backtests = await backtests_cursor.to_list(length=100)
    
    # Calculate all analytics
    drawdowns = portfolio_analytics.calculate_drawdown(history)
    win_analysis = portfolio_analytics.calculate_win_rate_trend(trades)
    sector_allocation = await portfolio_analytics.get_sector_allocation(positions)
    pnl_breakdown = portfolio_analytics.get_pnl_breakdown(positions, win_analysis.get("completed_trades", []))
    strategy_performance = portfolio_analytics.get_strategy_performance(backtests)
    
    return {
        "period": period,
        "history": history,
        "drawdowns": drawdowns,
        "max_drawdown": max((d["drawdown"] for d in drawdowns), default=0),
        "win_rate": win_analysis,
        "sector_allocation": sector_allocation,
        "pnl_breakdown": pnl_breakdown,
        "strategy_performance": strategy_performance
    }

# ===================== PAPER EXECUTION =====================

class OrderStatus:
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    EXECUTED = "executed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    FAILED = "failed"

class OrderSide:
    BUY = "buy"
    SELL = "sell"

class PaperTradeModel(BaseModel):
    symbol: str
    side: str = "buy"
    qty: Optional[float] = None
    notional: Optional[float] = None  # Dollar amount
    reason: str = ""
    strategy: str = "manual"
    confidence: Optional[float] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    signal_data: Optional[Dict] = None

class PaperExecutionEngine:
    """Paper trading execution engine with safety controls"""
    
    # Risky stocks to exclude from auto-trading (meme stocks, high-volatility, leveraged ETFs)
    RISKY_STOCKS = {
        # Meme stocks
        "GME", "AMC", "BBBY", "BB", "CLOV", "WISH", "WKHS", "SPCE", "HYMC", "MULN",
        # Cannabis stocks (highly volatile)
        "TLRY", "SNDL", "CGC", "ACB", "CRON", "HEXO", "OGI", "VFF",
        # Crypto-related (extreme volatility)
        "MSTR", "RIOT", "MARA", "BITF", "CLSK", "BTBT", "HIVE", "HUT", "COIN",
        # SPACs & speculative
        "DWAC", "PHUN", "BKKT", "IRNT", "TMC", "DNA",
        # Leveraged ETFs (NOT for holding)
        "TQQQ", "SQQQ", "SPXL", "SPXS", "UPRO", "UVXY", "SOXL", "SOXS", "LABU", "LABD",
        "FAS", "FAZ", "TNA", "TZA", "NUGT", "DUST", "JNUG", "JDST", "ERX", "ERY",
        "TVIX", "VXX", "VIXY", "SVXY", "TECL", "TECS", "FNGU", "FNGD", "WEBL", "WEBS",
        # Penny stocks / high-risk biotech
        "ATOS", "SESN", "CRVS", "OCGN", "INO", "SRNE", "NRXP", "VXRT",
        # EV SPACs (mostly unprofitable)
        "LCID", "RIVN", "FSR", "ARVL", "GOEV", "RIDE", "NKLA", "HYLN",
        # Other high-risk
        "WISH", "OPEN", "HOOD", "UPST", "AFRM"
    }
    
    def __init__(self):
        # Use consistent env var names - ALPACA_BASE_URL and ALPACA_SECRET_KEY
        self.alpaca_url = os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets/v2")
        # Strip /v2 if present (we add it in API calls)
        self.alpaca_url = self.alpaca_url.rstrip("/").replace("/v2", "")
        self.alpaca_key = os.environ.get("ALPACA_API_KEY", "")
        self.alpaca_secret = os.environ.get("ALPACA_SECRET_KEY", "")
        self.headers = {
            "APCA-API-KEY-ID": self.alpaca_key,
            "APCA-API-SECRET-KEY": self.alpaca_secret,
            "Content-Type": "application/json"
        }
    
    async def get_system_settings(self) -> Dict:
        """Get paper execution system settings"""
        settings = await db.paper_execution_settings.find_one({"_id": "default"}, {"_id": 0})
        if not settings:
            # Default settings: SAFE MODE (but allow extended hours for paper trading)
            settings = {
                "kill_switch": False,
                "auto_execution": False,  # OFF by default
                "manual_approval": True,   # ON by default
                "min_confidence": 0.60,
                "max_position_pct": 0.05,
                "cash_buffer": 0.10,
                "max_daily_loss_pct": 0.02,
                "block_extended_hours": True,  # Only allow regular market hours by default
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.paper_execution_settings.insert_one({"_id": "default", **settings})
        return settings
    
    async def update_system_settings(self, settings: Dict) -> Dict:
        """Update paper execution settings"""
        settings["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.paper_execution_settings.update_one(
            {"_id": "default"},
            {"$set": settings},
            upsert=True
        )
        return settings
    
    async def get_kill_switch_state(self) -> bool:
        """Check if kill switch is active"""
        settings = await self.get_system_settings()
        return settings.get("kill_switch", False)
    
    async def set_kill_switch(self, active: bool) -> Dict:
        """Set kill switch state"""
        await db.paper_execution_settings.update_one(
            {"_id": "default"},
            {"$set": {"kill_switch": active, "kill_switch_updated": datetime.now(timezone.utc).isoformat()}},
            upsert=True
        )
        
        # Log kill switch action
        await db.paper_audit_log.insert_one({
            "action": "kill_switch_toggle",
            "active": active,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {"kill_switch": active}
    
    async def check_risk_controls(self, trade: Dict, account: Dict) -> Dict:
        """Check all risk controls before execution"""
        settings = await self.get_system_settings()
        violations = []
        
        # 0. Risky stock check (FIRST CHECK - block high-risk stocks)
        symbol = trade.get("symbol", "").upper()
        if symbol in self.RISKY_STOCKS:
            violations.append(f"{symbol} is a high-risk stock (meme/leveraged/speculative) - blocked for safety")
        
        # 1. Kill switch check
        if settings.get("kill_switch", False):
            violations.append("Kill switch is active")
        
        # 2. Auto execution disabled check
        if not settings.get("auto_execution", False) and trade.get("auto_submitted", False):
            violations.append("Auto execution is disabled")
        
        # 3. Confidence check
        confidence = trade.get("confidence")
        if confidence is None:
            confidence = 1.0  # Default to 1.0 if not specified
        min_confidence = settings.get("min_confidence", 0.60)
        if confidence < min_confidence:
            violations.append(f"Confidence {confidence:.2f} below minimum {min_confidence:.2f}")
        
        # 4. Position size check
        if account:
            equity = float(account.get("equity", 0))
            max_position_pct = settings.get("max_position_pct", 0.05)
            qty = float(trade.get("qty") or 0)
            entry_price = float(trade.get("entry_price") or 0)
            notional = trade.get("notional") or (qty * entry_price if entry_price > 0 else 0)
            
            if equity > 0 and notional > 0:
                position_pct = notional / equity
                if position_pct > max_position_pct:
                    violations.append(f"Position size {position_pct:.1%} exceeds max {max_position_pct:.1%}")
        
        # 5. Cash buffer check
        if account:
            cash = float(account.get("cash", 0))
            equity = float(account.get("equity", 0))
            cash_buffer = settings.get("cash_buffer", 0.10)
            qty = float(trade.get("qty") or 0)
            entry_price = float(trade.get("entry_price") or 0)
            notional = trade.get("notional") or (qty * entry_price if entry_price > 0 else 0)
            
            # Skip cash buffer check if we can't calculate notional
            if equity > 0 and notional > 0:
                remaining_cash_pct = (cash - notional) / equity
                if remaining_cash_pct < cash_buffer:
                    violations.append(f"Trade would reduce cash below buffer ({cash_buffer:.0%})")
        
        # 6. Daily loss limit check
        if account:
            equity = float(account.get("equity", 0))
            last_equity = float(account.get("last_equity", equity))
            if last_equity > 0:
                daily_pnl_pct = (equity - last_equity) / last_equity
                max_daily_loss = settings.get("max_daily_loss_pct", 0.02)
                if daily_pnl_pct < -max_daily_loss:
                    violations.append(f"Daily loss limit ({max_daily_loss:.0%}) exceeded")
        
        # 7. Extended hours check
        if settings.get("block_extended_hours", True):
            market_status = self.get_market_status()
            if market_status["status"] != "open":
                status_name = market_status["status"].replace("_", " ").title()
                violations.append(f"Market is currently {status_name}. Extended hours trading is disabled. Enable 'Allow Extended Hours' in settings to trade outside regular hours (9:30 AM - 4:00 PM ET).")
        
        return {
            "passed": len(violations) == 0,
            "violations": violations
        }
    
    def get_market_status(self) -> Dict:
        """Get current market status based on US Eastern Time"""
        from zoneinfo import ZoneInfo
        
        # Get current time in ET
        et_tz = ZoneInfo("America/New_York")
        now_et = datetime.now(et_tz)
        
        hour = now_et.hour
        minute = now_et.minute
        weekday = now_et.weekday()  # Monday = 0, Sunday = 6
        
        # Weekend check
        if weekday >= 5:  # Saturday or Sunday
            return {
                "status": "closed",
                "label": "Market Closed",
                "message": "Markets are closed on weekends",
                "next_open": "Monday 9:30 AM ET",
                "is_trading_allowed": False
            }
        
        # Convert to minutes since midnight for easier comparison
        current_minutes = hour * 60 + minute
        
        # Market times in minutes
        premarket_start = 4 * 60  # 4:00 AM ET
        market_open = 9 * 60 + 30  # 9:30 AM ET
        market_close = 16 * 60  # 4:00 PM ET
        afterhours_end = 20 * 60  # 8:00 PM ET
        
        if current_minutes < premarket_start:
            return {
                "status": "closed",
                "label": "Market Closed",
                "message": "Markets open at 9:30 AM ET",
                "next_open": "9:30 AM ET today",
                "is_trading_allowed": False
            }
        elif current_minutes < market_open:
            return {
                "status": "pre_market",
                "label": "Pre-Market",
                "message": f"Pre-market trading (4:00 AM - 9:30 AM ET). Regular session opens in {(market_open - current_minutes) // 60}h {(market_open - current_minutes) % 60}m",
                "next_open": "9:30 AM ET today",
                "is_trading_allowed": False  # Extended hours only
            }
        elif current_minutes < market_close:
            return {
                "status": "open",
                "label": "Market Open",
                "message": f"Regular trading hours (9:30 AM - 4:00 PM ET). Closes in {(market_close - current_minutes) // 60}h {(market_close - current_minutes) % 60}m",
                "next_open": None,
                "is_trading_allowed": True
            }
        elif current_minutes < afterhours_end:
            return {
                "status": "after_hours",
                "label": "After-Hours",
                "message": "After-hours trading (4:00 PM - 8:00 PM ET). Regular session opens tomorrow at 9:30 AM ET",
                "next_open": "9:30 AM ET tomorrow",
                "is_trading_allowed": False  # Extended hours only
            }
        else:
            return {
                "status": "closed",
                "label": "Market Closed",
                "message": "Markets open tomorrow at 9:30 AM ET",
                "next_open": "9:30 AM ET tomorrow",
                "is_trading_allowed": False
            }
    
    async def queue_trade(self, trade_data: Dict) -> Dict:
        """Add a trade to the queue for review"""
        settings = await self.get_system_settings()
        
        trade = {
            "id": str(uuid.uuid4()),
            "symbol": trade_data["symbol"].upper(),
            "side": trade_data.get("side", "buy"),
            "qty": trade_data.get("qty"),
            "notional": trade_data.get("notional"),
            "reason": trade_data.get("reason", ""),
            "strategy": trade_data.get("strategy", "manual"),
            "confidence": trade_data.get("confidence"),
            "entry_price": trade_data.get("entry_price"),
            "stop_loss": trade_data.get("stop_loss"),
            "take_profit": trade_data.get("take_profit"),
            "signal_data": trade_data.get("signal_data"),
            "status": OrderStatus.PENDING,
            "auto_submitted": trade_data.get("auto_submitted", False),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status_history": [
                {"status": OrderStatus.PENDING, "timestamp": datetime.now(timezone.utc).isoformat()}
            ]
        }
        
        await db.paper_trade_queue.insert_one(trade)
        trade.pop("_id", None)
        
        # Log the queue action
        await self._log_audit("trade_queued", trade["id"], trade)
        
        return trade
    
    async def approve_trade(self, trade_id: str) -> Dict:
        """Approve a pending trade for execution"""
        trade = await db.paper_trade_queue.find_one({"id": trade_id})
        if not trade:
            return {"success": False, "error": "Trade not found"}
        
        if trade["status"] != OrderStatus.PENDING:
            return {"success": False, "error": f"Trade is not pending (status: {trade['status']})"}
        
        # Update status to approved
        await db.paper_trade_queue.update_one(
            {"id": trade_id},
            {
                "$set": {"status": OrderStatus.APPROVED, "approved_at": datetime.now(timezone.utc).isoformat()},
                "$push": {"status_history": {"status": OrderStatus.APPROVED, "timestamp": datetime.now(timezone.utc).isoformat()}}
            }
        )
        
        await self._log_audit("trade_approved", trade_id, {"symbol": trade["symbol"]})
        
        return {"success": True, "trade_id": trade_id, "status": OrderStatus.APPROVED}
    
    async def reject_trade(self, trade_id: str, reason: str = "") -> Dict:
        """Reject a pending trade"""
        trade = await db.paper_trade_queue.find_one({"id": trade_id})
        if not trade:
            return {"success": False, "error": "Trade not found"}
        
        await db.paper_trade_queue.update_one(
            {"id": trade_id},
            {
                "$set": {"status": OrderStatus.REJECTED, "rejection_reason": reason, "rejected_at": datetime.now(timezone.utc).isoformat()},
                "$push": {"status_history": {"status": OrderStatus.REJECTED, "timestamp": datetime.now(timezone.utc).isoformat(), "reason": reason}}
            }
        )
        
        await self._log_audit("trade_rejected", trade_id, {"symbol": trade["symbol"], "reason": reason})
        
        return {"success": True, "trade_id": trade_id, "status": OrderStatus.REJECTED}
    
    async def cancel_trade(self, trade_id: str) -> Dict:
        """Cancel a pending or approved trade"""
        trade = await db.paper_trade_queue.find_one({"id": trade_id})
        if not trade:
            return {"success": False, "error": "Trade not found"}
        
        if trade["status"] in [OrderStatus.EXECUTED, OrderStatus.FAILED]:
            return {"success": False, "error": f"Cannot cancel {trade['status']} trade"}
        
        await db.paper_trade_queue.update_one(
            {"id": trade_id},
            {
                "$set": {"status": OrderStatus.CANCELLED, "cancelled_at": datetime.now(timezone.utc).isoformat()},
                "$push": {"status_history": {"status": OrderStatus.CANCELLED, "timestamp": datetime.now(timezone.utc).isoformat()}}
            }
        )
        
        await self._log_audit("trade_cancelled", trade_id, {"symbol": trade["symbol"]})
        
        return {"success": True, "trade_id": trade_id, "status": OrderStatus.CANCELLED}
    
    async def execute_trade(self, trade_id: str) -> Dict:
        """Execute an approved trade on Alpaca Paper"""
        trade = await db.paper_trade_queue.find_one({"id": trade_id})
        if not trade:
            return {"success": False, "error": "Trade not found"}
        
        if trade["status"] != OrderStatus.APPROVED:
            return {"success": False, "error": f"Trade must be approved first (status: {trade['status']})"}
        
        # Check risk controls
        account = await api_client.alpaca_account()
        risk_check = await self.check_risk_controls(trade, account)
        
        if not risk_check["passed"]:
            # Mark as failed with risk violations
            await db.paper_trade_queue.update_one(
                {"id": trade_id},
                {
                    "$set": {
                        "status": OrderStatus.FAILED,
                        "failure_reason": f"Risk violations: {', '.join(risk_check['violations'])}",
                        "failed_at": datetime.now(timezone.utc).isoformat()
                    },
                    "$push": {"status_history": {"status": OrderStatus.FAILED, "timestamp": datetime.now(timezone.utc).isoformat(), "violations": risk_check["violations"]}}
                }
            )
            await self._log_audit("trade_blocked", trade_id, {"violations": risk_check["violations"]})
            return {"success": False, "error": "Risk controls failed", "violations": risk_check["violations"]}
        
        # Update status to executing
        await db.paper_trade_queue.update_one(
            {"id": trade_id},
            {
                "$set": {"status": OrderStatus.EXECUTING},
                "$push": {"status_history": {"status": OrderStatus.EXECUTING, "timestamp": datetime.now(timezone.utc).isoformat()}}
            }
        )
        
        # Submit to Alpaca Paper
        try:
            order_data = {
                "symbol": trade["symbol"],
                "side": trade["side"],
                "type": "market",
                "time_in_force": "day"
            }
            
            if trade.get("qty"):
                order_data["qty"] = str(trade["qty"])
            elif trade.get("notional"):
                order_data["notional"] = str(trade["notional"])
            else:
                return {"success": False, "error": "No quantity or notional specified"}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.alpaca_url}/v2/orders",
                    headers=self.headers,
                    json=order_data
                )
                
                if response.status_code in [200, 201]:
                    alpaca_order = response.json()
                    
                    # Update with execution details
                    await db.paper_trade_queue.update_one(
                        {"id": trade_id},
                        {
                            "$set": {
                                "status": OrderStatus.EXECUTED,
                                "alpaca_order_id": alpaca_order.get("id"),
                                "alpaca_status": alpaca_order.get("status"),
                                "filled_qty": alpaca_order.get("filled_qty"),
                                "filled_avg_price": alpaca_order.get("filled_avg_price"),
                                "executed_at": datetime.now(timezone.utc).isoformat()
                            },
                            "$push": {"status_history": {"status": OrderStatus.EXECUTED, "timestamp": datetime.now(timezone.utc).isoformat(), "alpaca_order_id": alpaca_order.get("id")}}
                        }
                    )
                    
                    await self._log_audit("trade_executed", trade_id, {
                        "symbol": trade["symbol"],
                        "alpaca_order_id": alpaca_order.get("id"),
                        "filled_qty": alpaca_order.get("filled_qty")
                    })
                    
                    return {"success": True, "trade_id": trade_id, "alpaca_order": alpaca_order}
                else:
                    error_msg = response.text
                    await db.paper_trade_queue.update_one(
                        {"id": trade_id},
                        {
                            "$set": {
                                "status": OrderStatus.FAILED,
                                "failure_reason": f"Alpaca error: {error_msg}",
                                "failed_at": datetime.now(timezone.utc).isoformat()
                            },
                            "$push": {"status_history": {"status": OrderStatus.FAILED, "timestamp": datetime.now(timezone.utc).isoformat(), "error": error_msg}}
                        }
                    )
                    
                    await self._log_audit("trade_failed", trade_id, {"error": error_msg})
                    
                    return {"success": False, "error": f"Alpaca error: {error_msg}"}
        
        except Exception as e:
            error_msg = str(e)
            await db.paper_trade_queue.update_one(
                {"id": trade_id},
                {
                    "$set": {
                        "status": OrderStatus.FAILED,
                        "failure_reason": error_msg,
                        "failed_at": datetime.now(timezone.utc).isoformat()
                    },
                    "$push": {"status_history": {"status": OrderStatus.FAILED, "timestamp": datetime.now(timezone.utc).isoformat(), "error": error_msg}}
                }
            )
            
            await self._log_audit("trade_error", trade_id, {"error": error_msg})
            
            return {"success": False, "error": error_msg}
    
    async def get_trade_queue(self, status: Optional[str] = None) -> List[Dict]:
        """Get trades from queue, optionally filtered by status"""
        query = {}
        if status:
            query["status"] = status
        
        cursor = db.paper_trade_queue.find(query, {"_id": 0}).sort("created_at", -1)
        trades = await cursor.to_list(length=100)
        return trades
    
    async def get_trade_by_id(self, trade_id: str) -> Optional[Dict]:
        """Get a specific trade by ID"""
        trade = await db.paper_trade_queue.find_one({"id": trade_id}, {"_id": 0})
        return trade
    
    async def get_audit_log(self, limit: int = 50) -> List[Dict]:
        """Get audit log entries"""
        cursor = db.paper_audit_log.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
        logs = await cursor.to_list(length=limit)
        return logs
    
    async def _log_audit(self, action: str, trade_id: str, data: Dict):
        """Log an audit entry"""
        await db.paper_audit_log.insert_one({
            "action": action,
            "trade_id": trade_id,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

paper_execution = PaperExecutionEngine()

# AI Auto-Trade Orchestrator
auto_orchestrator = AutoTradeOrchestrator(db, api_client, paper_execution)

# Auto-Trade Scheduler
auto_scheduler = AutoTradeScheduler(db, auto_orchestrator, enhanced_news_engine)

# Live Price Engine
live_price_engine = LivePriceEngine()
auto_orchestrator.live_price_engine = live_price_engine

# Price Integrity Service (single source of truth)
price_integrity = PriceIntegrityService()

# Live Re-Evaluation Engine
live_reeval_engine = LiveReEvaluationEngine(db, auto_orchestrator)
live_price_engine.set_reeval_callback(live_reeval_engine.on_price_change)

# Re-Evaluation Verifier (auto-starts at market open)
reeval_verifier = ReEvalVerifier()
live_reeval_engine.set_verifier(reeval_verifier)

# Top Movers Scanner
top_movers_scanner = TopMoversScanner(db, config.FMP_API_KEY)
auto_orchestrator.top_movers_scanner = top_movers_scanner

# Performance Tracker
performance_tracker = PerformanceTracker(db)
auto_orchestrator.performance_tracker = performance_tracker


# ===================== TOP MOVERS SCANNER ENDPOINTS =====================

@api_router.get("/top-movers/scan")
async def scan_top_movers(force: bool = False, auth: bool = Depends(verify_access)):
    """Scan for top gainers/losers/actives from FMP."""
    result = await top_movers_scanner.scan(force=force)
    return {k: v for k, v in result.items() if k != "_id"}

@api_router.get("/top-movers/status")
async def get_top_movers_status(auth: bool = Depends(verify_access)):
    """Get current top movers state and scan history."""
    return {
        "has_data": bool(top_movers_scanner._cache),
        "last_refresh": top_movers_scanner._last_refresh.isoformat() if top_movers_scanner._last_refresh else None,
        "needs_refresh": top_movers_scanner.should_refresh(),
        "accepted_count": len(top_movers_scanner.get_accepted_symbols()),
        "accepted_symbols": top_movers_scanner.get_accepted_symbols(),
        "config": {
            "max_gainers": top_movers_scanner.MAX_GAINERS,
            "max_losers": top_movers_scanner.MAX_LOSERS,
            "max_actives": top_movers_scanner.MAX_ACTIVES,
            "refresh_interval_minutes": top_movers_scanner.REFRESH_INTERVAL_MINUTES,
            "price_range": f"${top_movers_scanner.MIN_PRICE}-${top_movers_scanner.MAX_PRICE}",
            "min_volume": f"{top_movers_scanner.MIN_VOLUME:,}",
            "min_market_cap": f"${top_movers_scanner.MIN_MARKET_CAP/1e6:.0f}M",
        },
        "scan_history": top_movers_scanner.get_scan_history(5),
    }

@api_router.get("/top-movers/performance")
async def get_top_movers_performance(auth: bool = Depends(verify_access)):
    """Get today's top movers scanning performance summary."""
    return await top_movers_scanner.get_performance_summary()


# ===================== PERFORMANCE ANALYTICS ENDPOINTS =====================

@api_router.get("/analytics/session-summary")
async def get_session_summary(date: str = None, auth: bool = Depends(verify_access)):
    """Get session performance summary: trades, win rate, P&L, drawdown, by time window."""
    return await performance_tracker.get_session_summary(date)

@api_router.get("/analytics/trade-quality")
async def get_trade_quality(date: str = None, auth: bool = Depends(verify_access)):
    """Analyze signal quality: which signals led to wins vs losses."""
    return await performance_tracker.get_trade_quality_analysis(date)

@api_router.get("/analytics/pipeline-efficiency")
async def get_pipeline_efficiency(date: str = None, auth: bool = Depends(verify_access)):
    """Pipeline conversion rates and top rejection reasons."""
    return await performance_tracker.get_pipeline_efficiency(date)

@api_router.get("/analytics/best-worst-trades")
async def get_best_worst_trades(date: str = None, count: int = 3, auth: bool = Depends(verify_access)):
    """Get top N best and worst trades with full reasoning."""
    return await performance_tracker.get_best_worst_trades(date, count)

@api_router.get("/analytics/risk-compliance")
async def get_risk_compliance(date: str = None, auth: bool = Depends(verify_access)):
    """Verify risk rule compliance: stop-loss, trailing stops, position sizing."""
    return await performance_tracker.get_risk_compliance(date)

@api_router.get("/analytics/regime-performance")
async def get_regime_performance(date: str = None, auth: bool = Depends(verify_access)):
    """Compare performance across market regimes."""
    return await performance_tracker.get_regime_performance(date)

@api_router.get("/analytics/full-report")
async def get_full_report(date: str = None, auth: bool = Depends(verify_access)):
    """Generate complete performance report: session, quality, pipeline, risk, regime."""
    return await performance_tracker.get_full_report(date)




# ===================== AUTO-TRADE AI ENDPOINTS =====================

@api_router.get("/auto-trade/status")
async def get_auto_trade_status(auth: bool = Depends(verify_access)):
    """Get full auto-trade system status"""
    return await auto_orchestrator.get_status()

@api_router.get("/auto-trade/settings")
async def get_auto_trade_settings(auth: bool = Depends(verify_access)):
    """Get auto-trade settings"""
    settings = await auto_orchestrator.get_settings()
    return settings.dict()

@api_router.post("/auto-trade/settings")
async def update_auto_trade_settings(data: Dict, auth: bool = Depends(verify_access)):
    """Update auto-trade settings"""
    current = await auto_orchestrator.get_settings()
    update_data = current.dict()
    update_data.update({k: v for k, v in data.items() if k in AutoTradeSettings.__fields__})
    new_settings = AutoTradeSettings(**update_data)
    return await auto_orchestrator.save_settings(new_settings)

@api_router.post("/auto-trade/toggle")
async def toggle_auto_trade(enabled: bool, auth: bool = Depends(verify_access)):
    """Toggle auto-trade ON/OFF"""
    settings = await auto_orchestrator.get_settings()
    settings.auto_enabled = enabled
    await auto_orchestrator.save_settings(settings)
    return {"auto_enabled": enabled, "message": f"Auto-trading {'ENABLED' if enabled else 'DISABLED'}"}

@api_router.get("/auto-trade/scan")
async def scan_auto_opportunities(auth: bool = Depends(verify_access)):
    """Scan for auto-trade opportunities with AI classification"""
    return await auto_orchestrator.scan_opportunities()

_ta_refresh_running = False

@api_router.post("/auto-trade/refresh-ta")
async def refresh_ta_signals(background_tasks: BackgroundTasks, auth: bool = Depends(verify_access)):
    """Trigger background TA analysis refresh on liquid stocks.
    This runs in background and caches results to DB for fast scan reads.
    Only one refresh can run at a time."""
    global _ta_refresh_running
    from technical_analysis_engine import TechnicalSignalGenerator, TACache

    if _ta_refresh_running:
        cached_count = await db.ta_signals.count_documents({})
        return {"message": "TA refresh already running", "db_cached": cached_count, "mem_cache": TACache.stats()}

    async def _run_ta_refresh():
        global _ta_refresh_running
        _ta_refresh_running = True
        try:
            trading_sigs = await db.trading_signals.find(
                {"dead_ticker": {"$ne": True}}, {"_id": 0, "symbol": 1, "indicators.volume_ratio": 1}
            ).to_list(2000)
            # Sort by volume, take top 80 (Starter plan supports high throughput)
            symbols = sorted(
                [s for s in trading_sigs if s.get("indicators", {}).get("volume_ratio", 0) >= 0.5],
                key=lambda x: x.get("indicators", {}).get("volume_ratio", 0),
                reverse=True
            )[:80]
            symbol_list = [s["symbol"] for s in symbols]
            logger.info(f"TA refresh starting for {len(symbol_list)} stocks...")
            results = await TechnicalSignalGenerator.batch_analyze_fast(symbol_list, max_concurrent=10)
            saved = 0
            for r in results:
                r["last_updated"] = datetime.now(timezone.utc).isoformat()
                await db.ta_signals.update_one({"symbol": r["symbol"]}, {"$set": r}, upsert=True)
                saved += 1
            logger.info(f"TA refresh complete: {saved} signals cached from {len(symbol_list)} stocks")
        except Exception as e:
            logger.error(f"TA refresh error: {e}")
        finally:
            _ta_refresh_running = False

    background_tasks.add_task(_run_ta_refresh)
    cached_count = await db.ta_signals.count_documents({})
    mem_cache = TACache.stats()
    return {"message": "TA refresh triggered in background", "db_cached": cached_count, "mem_cache": mem_cache}


@api_router.post("/auto-trade/execute-cycle")
async def execute_auto_cycle(background_tasks: BackgroundTasks, auth: bool = Depends(verify_access)):
    """Execute one auto-trade cycle (scan → classify → risk → execute)"""
    background_tasks.add_task(auto_orchestrator.execute_auto_cycle)
    return {"message": "Auto-trade cycle triggered", "status": "processing"}

@api_router.get("/auto-trade/history")
async def get_auto_trade_history(limit: int = Query(default=50, ge=1, le=200), auth: bool = Depends(verify_access)):
    """Get auto-trade execution history"""
    return await auto_orchestrator.get_trade_history(limit)

@api_router.get("/auto-trade/trade-log")
async def get_trade_log(limit: int = Query(default=50, ge=1, le=200), auth: bool = Depends(verify_access)):
    """Get comprehensive trade log from auto_trade_log collection.
    Includes entry reasons, confidence, setup, direction, P&L, ownership, strategy_type."""
    from ai_trading_system import ConfidenceScoringEngine

    trades = await db.auto_trade_log.find(
        {}, {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)

    # Enrich each trade with confidence breakdown if it has signal data
    for t in trades:
        confidence = t.get("confidence", 0)
        if confidence > 0:
            # Try to get signal from explanation
            sig = t.get("explanation", {}).get("signal", {})
            if not sig:
                sig = t.get("signal_data", {})
            if sig:
                try:
                    _, breakdown = ConfidenceScoringEngine.score_day_trade(
                        sig, {"regime": "neutral", "score": 50}, return_breakdown=True
                    )
                    t["confidence_breakdown"] = breakdown
                except Exception:
                    pass

        # Extract key fields from explanation for easy frontend access
        exp = t.get("explanation", {})
        if isinstance(exp, dict):
            t["entry_reasons"] = exp.get("entry_reasons", [])
            t["exit_plan"] = exp.get("exit_plan", {})
            ki = exp.get("key_indicators", {})
            t["best_setup"] = ki.get("best_setup", t.get("best_setup", ""))
            t["direction"] = ki.get("direction", t.get("direction", ""))
            t["signal_count"] = ki.get("signal_count", 0)

    return {"trades": trades, "total": len(trades)}


@api_router.get("/auto-trade/analytics")
async def get_trade_analytics(auth: bool = Depends(verify_access)):
    """Comprehensive trade log analytics dashboard.
    Returns win rate, P&L, drawdown, performance by setup/confidence/session,
    skip reasons, rejection reasons, slippage stats, and execution timing."""
    return await auto_orchestrator.get_trade_analytics()



@api_router.get("/auto-trade/mtf-heatmap")
async def get_mtf_heatmap(auth: bool = Depends(verify_access)):
    """Get MTF heatmap data from the latest scan results.
    Returns classified stocks with MTF alignment status, reusing cached scan data."""
    scan = await auto_orchestrator.scan_opportunities()
    return {
        "heatmap": scan.get("mtf_heatmap", []),
        "distribution": scan.get("mtf_heatmap_distribution", {}),
        "stats": scan.get("stats", {}),
        "market_session": scan.get("market_session", "unknown"),
    }


# ===================== LIVE PRICE ENDPOINTS =====================

@api_router.post("/live-prices/start")
async def start_live_prices(auth: bool = Depends(verify_access)):
    """Start live price streaming for currently tracked symbols."""
    # Get symbols from latest scan watchlist + open positions
    scan = await auto_orchestrator.scan_opportunities()
    symbols = set()
    for c in scan.get("watchlist", []):
        symbols.add(c.get("symbol", ""))
    for c in scan.get("long_term_candidates", []):
        symbols.add(c.get("symbol", ""))
    # Add open position symbols
    try:
        positions = await auto_orchestrator.alpaca._get_positions()
        for p in positions:
            symbols.add(p.get("symbol", ""))
    except Exception:
        pass
    symbols.discard("")
    
    if not symbols:
        # Default to top scanned universe
        symbols = {"AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "AMD", "SPY", "QQQ"}
    
    await live_price_engine.start(list(symbols))
    return {"status": "started", "symbols": len(symbols)}

@api_router.post("/live-prices/stop")
async def stop_live_prices(auth: bool = Depends(verify_access)):
    """Stop live price streaming."""
    await live_price_engine.stop()
    return {"status": "stopped"}

@api_router.get("/live-prices/all")
async def get_all_live_prices(auth: bool = Depends(verify_access)):
    """Get all tracked symbol prices with full bid/ask/spread data."""
    prices = live_price_engine.get_all_prices()
    status = live_price_engine.get_status()
    return {"prices": prices, "engine": status}

@api_router.get("/live-prices/status/engine")
async def get_live_price_status(auth: bool = Depends(verify_access)):
    """Get live price engine status (connection, stats, stale counts)."""
    return live_price_engine.get_status()

@api_router.get("/live-prices/stream")
async def live_price_stream(token: str = None, auth: bool = None):
    """Server-Sent Events stream for real-time price updates to the frontend.
    Accepts auth via query param ?token=xxx since EventSource doesn't support headers."""
    # Validate token from query param
    if not token or not validate_token(token):
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    async def event_generator():
        last_data = {}
        while True:
            await asyncio.sleep(2)
            prices = live_price_engine.get_all_prices()
            engine = live_price_engine.get_status()
            
            changed = {}
            for sym, data in prices.items():
                prev = last_data.get(sym, {})
                if (data.get("display_price") != prev.get("display_price") or
                    data.get("bid") != prev.get("bid") or
                    data.get("source") != prev.get("source")):
                    changed[sym] = data
            
            if changed or not last_data:
                reeval_stats = live_reeval_engine.get_stats()
                recent_reevals = live_reeval_engine.get_recent_events(5)
                payload = json.dumps({
                    "prices": changed or prices,
                    "engine": engine,
                    "reeval": {"stats": reeval_stats, "recent": recent_reevals},
                })
                yield f"data: {payload}\n\n"
                last_data = prices
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )

@api_router.get("/live-prices/{symbol}")
async def get_live_price(symbol: str, auth: bool = Depends(verify_access)):
    """Get live price data for a specific symbol."""
    state = live_price_engine.get_price(symbol.upper())
    if not state:
        return {"symbol": symbol.upper(), "source": "none", "stale": True}
    return state.to_dict()

# ===================== LIVE RE-EVALUATION ENDPOINTS =====================

@api_router.get("/reeval/events")
async def get_reeval_events(limit: int = 50, auth: bool = Depends(verify_access)):
    """Get recent re-evaluation events from in-memory buffer."""
    return {"events": live_reeval_engine.get_recent_events(limit)}

@api_router.get("/reeval/stats")
async def get_reeval_stats(auth: bool = Depends(verify_access)):
    """Get re-evaluation engine statistics."""
    return live_reeval_engine.get_stats()

@api_router.get("/reeval/history")
async def get_reeval_history(limit: int = 50, auth: bool = Depends(verify_access)):
    """Get persisted re-evaluation events from MongoDB."""
    cursor = db.reeval_events.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
    events = await cursor.to_list(length=limit)
    return {"events": events, "count": len(events)}


@api_router.get("/reeval/verify")
async def get_reeval_verification(auth: bool = Depends(verify_access)):
    """Get the live re-evaluation verification report. Auto-activates at market open."""
    # Update engine status snapshot
    reeval_verifier.update_engine_status(live_price_engine.get_status())
    return reeval_verifier.get_report()

@api_router.post("/reeval/verify/start")
async def start_reeval_verification(auth: bool = Depends(verify_access)):
    """Manually start the re-evaluation verifier."""
    engine_status = live_price_engine.get_status()
    reeval_verifier.start(engine_status)
    return {"message": "Verifier started", "engine_status": engine_status}

@api_router.post("/reeval/verify/stop")
async def stop_reeval_verification(auth: bool = Depends(verify_access)):
    """Manually stop the re-evaluation verifier."""
    reeval_verifier.stop()
    return {"message": "Verifier stopped", "report": reeval_verifier.get_report()}


@api_router.get("/auto-trade/confidence-distribution")
async def get_confidence_distribution(date: str = None, auth: bool = Depends(verify_access)):
    """Get confidence distribution data for threshold analysis."""
    from auto_trade_scheduler import _now_et
    query = {}
    if date:
        query["date"] = date
    else:
        query["date"] = _now_et().date().isoformat()
    
    cursor = db.confidence_distribution.find(query, {"_id": 0}).sort("timestamp", -1).limit(50)
    records = await cursor.to_list(length=50)
    
    # Aggregate
    total_above_65 = sum(r.get("above_65", 0) for r in records)
    total_above_70 = sum(r.get("above_70", 0) for r in records)
    total_above_80 = sum(r.get("above_80", 0) for r in records)
    total_blocked = sum(r.get("blocked_only_by_threshold", 0) for r in records)
    total_executed = sum(r.get("executed", 0) for r in records)
    
    return {
        "date": query["date"],
        "scan_cycles": len(records),
        "aggregate": {
            "total_above_65": total_above_65,
            "total_above_70": total_above_70,
            "total_above_80": total_above_80,
            "total_blocked_by_threshold": total_blocked,
            "total_executed": total_executed,
        },
        "latest_cycle": records[0] if records else None,
        "cycles": records[:10],
    }




@api_router.post("/auto-trade/emergency-pause")
async def emergency_pause(pause: bool = True, auth: bool = Depends(verify_access)):
    """Emergency pause/resume auto-trading"""
    settings = await auto_orchestrator.get_settings()
    settings.emergency_pause = pause
    await auto_orchestrator.save_settings(settings)
    return {"emergency_pause": pause, "message": f"Auto-trading {'PAUSED' if pause else 'RESUMED'}"}

# ===================== SCHEDULER ENDPOINTS =====================

@api_router.post("/scheduler/start")
async def start_scheduler(auth: bool = Depends(verify_access)):
    """Start the auto-trade scheduler"""
    await auto_scheduler.initialize()
    return await auto_scheduler.start()

@api_router.post("/scheduler/stop")
async def stop_scheduler(auth: bool = Depends(verify_access)):
    """Stop the auto-trade scheduler"""
    return await auto_scheduler.stop()

@api_router.post("/scheduler/emergency-stop")
async def scheduler_emergency_stop(auth: bool = Depends(verify_access)):
    """Emergency stop - halt all trading immediately"""
    return await auto_scheduler.emergency_stop()

@api_router.post("/scheduler/clear-emergency")
async def scheduler_clear_emergency(auth: bool = Depends(verify_access)):
    """Clear emergency stop state"""
    return await auto_scheduler.clear_emergency()

@api_router.get("/scheduler/status")
async def get_scheduler_status(auth: bool = Depends(verify_access)):
    """Get scheduler status, next run timer, deployment mode"""
    return await auto_scheduler.get_status()

@api_router.post("/scheduler/deploy-mode")
async def set_deploy_mode(mode: str = Query(...), auth: bool = Depends(verify_access)):
    """Set deployment mode: paper, shadow, limited_live, full_live"""
    return await auto_scheduler.set_deployment_mode(mode)

@api_router.get("/scheduler/notifications")
async def get_scheduler_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    auth: bool = Depends(verify_access)
):
    """Get scheduler notifications"""
    return await auto_scheduler.get_notifications(limit)

@api_router.post("/scheduler/notifications/read")
async def mark_notifications_read(auth: bool = Depends(verify_access)):
    """Mark all notifications as read"""
    count = await auto_scheduler.mark_notifications_read()
    return {"marked_read": count}

@api_router.get("/scheduler/execution-log")
async def get_scheduler_execution_log(
    limit: int = Query(default=50, ge=1, le=200),
    auth: bool = Depends(verify_access)
):
    """Get scheduler execution log"""
    return await auto_scheduler.get_execution_log(limit)

@api_router.post("/scheduler/settings")
async def update_scheduler_settings(data: Dict, auth: bool = Depends(verify_access)):
    """Update scheduler settings"""
    return await auto_scheduler.update_settings(data)

# Paper Execution Endpoints

@api_router.get("/paper/settings")
async def get_paper_settings(auth: bool = Depends(verify_access)):
    """Get paper execution settings"""
    return await paper_execution.get_system_settings()

@api_router.post("/paper/settings")
async def update_paper_settings(settings: Dict, auth: bool = Depends(verify_access)):
    """Update paper execution settings"""
    # Remove protected fields
    settings.pop("_id", None)
    settings.pop("created_at", None)
    return await paper_execution.update_system_settings(settings)

@api_router.get("/paper/kill-switch")
async def get_kill_switch(auth: bool = Depends(verify_access)):
    """Get kill switch state"""
    active = await paper_execution.get_kill_switch_state()
    return {"kill_switch": active}

@api_router.post("/paper/kill-switch")
async def set_kill_switch(active: bool = True, auth: bool = Depends(verify_access)):
    """Set kill switch state"""
    return await paper_execution.set_kill_switch(active)

@api_router.post("/paper/queue")
async def queue_paper_trade(trade: PaperTradeModel, auth: bool = Depends(verify_access)):
    """Queue a trade for review"""
    return await paper_execution.queue_trade(trade.dict())

@api_router.get("/paper/queue")
async def get_paper_queue(
    status: Optional[str] = Query(default=None),
    auth: bool = Depends(verify_access)
):
    """Get trade queue"""
    return await paper_execution.get_trade_queue(status)

@api_router.get("/paper/trade/{trade_id}")
async def get_paper_trade(trade_id: str, auth: bool = Depends(verify_access)):
    """Get a specific trade"""
    trade = await paper_execution.get_trade_by_id(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade

@api_router.post("/paper/trade/{trade_id}/approve")
async def approve_paper_trade(trade_id: str, auth: bool = Depends(verify_access)):
    """Approve a pending trade"""
    return await paper_execution.approve_trade(trade_id)

@api_router.post("/paper/trade/{trade_id}/reject")
async def reject_paper_trade(
    trade_id: str,
    reason: str = Query(default=""),
    auth: bool = Depends(verify_access)
):
    """Reject a pending trade"""
    return await paper_execution.reject_trade(trade_id, reason)

@api_router.post("/paper/trade/{trade_id}/cancel")
async def cancel_paper_trade(trade_id: str, auth: bool = Depends(verify_access)):
    """Cancel a pending or approved trade"""
    return await paper_execution.cancel_trade(trade_id)

@api_router.post("/paper/trade/{trade_id}/execute")
async def execute_paper_trade(trade_id: str, auth: bool = Depends(verify_access)):
    """Execute an approved trade"""
    return await paper_execution.execute_trade(trade_id)

@api_router.post("/paper/risk-check")
async def check_risk(trade: PaperTradeModel, auth: bool = Depends(verify_access)):
    """Check risk controls for a potential trade"""
    account = await api_client.alpaca_account()
    return await paper_execution.check_risk_controls(trade.dict(), account)

@api_router.get("/paper/audit")
async def get_paper_audit(
    limit: int = Query(default=50, ge=1, le=200),
    auth: bool = Depends(verify_access)
):
    """Get paper execution audit log"""
    return await paper_execution.get_audit_log(limit)

@api_router.get("/paper/stats")
async def get_paper_stats(auth: bool = Depends(verify_access)):
    """Get paper execution statistics"""
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    stats_cursor = db.paper_trade_queue.aggregate(pipeline)
    stats_list = await stats_cursor.to_list(length=20)
    
    stats = {item["_id"]: item["count"] for item in stats_list}
    
    return {
        "pending": stats.get(OrderStatus.PENDING, 0),
        "approved": stats.get(OrderStatus.APPROVED, 0),
        "executed": stats.get(OrderStatus.EXECUTED, 0),
        "rejected": stats.get(OrderStatus.REJECTED, 0),
        "cancelled": stats.get(OrderStatus.CANCELLED, 0),
        "failed": stats.get(OrderStatus.FAILED, 0),
        "total": sum(stats.values())
    }

@api_router.get("/paper/market-status")
async def get_market_status(auth: bool = Depends(verify_access)):
    """Get current market status and trading availability"""
    market_status = paper_execution.get_market_status()
    settings = await paper_execution.get_system_settings()
    
    # Add extended hours setting to response
    market_status["extended_hours_enabled"] = not settings.get("block_extended_hours", True)
    market_status["can_trade_now"] = (
        market_status["is_trading_allowed"] or 
        market_status["extended_hours_enabled"]
    )
    
    return market_status

@api_router.get("/paper/risky-stocks")
async def get_risky_stocks(auth: bool = Depends(verify_access)):
    """Get list of risky stocks that are blocked from auto-trading"""
    return {
        "risky_stocks": list(PaperExecutionEngine.RISKY_STOCKS),
        "count": len(PaperExecutionEngine.RISKY_STOCKS),
        "reason": "These stocks are blocked from auto-trading due to high volatility, speculative nature, or leveraged structure"
    }

@api_router.get("/paper/check-symbol/{symbol}")
async def check_symbol_risk(symbol: str, auth: bool = Depends(verify_access)):
    """Check if a symbol is considered risky"""
    symbol_upper = symbol.upper()
    is_risky = symbol_upper in PaperExecutionEngine.RISKY_STOCKS
    return {
        "symbol": symbol_upper,
        "is_risky": is_risky,
        "can_auto_trade": not is_risky,
        "message": f"{symbol_upper} is {'BLOCKED (high-risk)' if is_risky else 'ALLOWED'} for auto-trading"
    }

@api_router.get("/paper/safe-stocks")
async def get_safe_tradeable_stocks(
    category: Optional[str] = Query(default=None, description="Filter by category: hot, bullish, undervalued"),
    limit: int = Query(default=100, ge=10, le=500),
    auth: bool = Depends(verify_access)
):
    """Get list of safe (non-risky) stocks suitable for auto-trading with investment signals"""
    # Get all investment signals
    cursor = db.investment_signals.find({}, {"_id": 0}).sort("overall_score", -1)
    all_signals = await cursor.to_list(length=2000)
    
    # Filter out risky stocks
    safe_signals = [
        s for s in all_signals 
        if s.get("symbol", "").upper() not in PaperExecutionEngine.RISKY_STOCKS
    ]
    
    # Filter by category if specified
    if category:
        category_lower = category.lower()
        if category_lower == "hot":
            safe_signals = [s for s in safe_signals if s.get("category") == "Hot"]
        elif category_lower == "bullish":
            safe_signals = [s for s in safe_signals if s.get("category") in ["Hot", "Bullish"]]
        elif category_lower == "undervalued":
            safe_signals = [s for s in safe_signals if s.get("category") == "Undervalued"]
        elif category_lower == "buy":
            safe_signals = [s for s in safe_signals if s.get("signal") == "Buy"]
    
    # Limit results
    safe_signals = safe_signals[:limit]
    
    return {
        "stocks": safe_signals,
        "count": len(safe_signals),
        "total_safe": len([s for s in all_signals if s.get("symbol", "").upper() not in PaperExecutionEngine.RISKY_STOCKS]),
        "total_risky_excluded": len(PaperExecutionEngine.RISKY_STOCKS),
        "category_filter": category
    }

@api_router.get("/paper/recommended-trades")
async def get_recommended_trades(
    limit: int = Query(default=20, ge=5, le=50),
    auth: bool = Depends(verify_access)
):
    """Get recommended trades for Auto Trade - only safe, high-quality stocks"""
    # Get trading signals
    trading_data = await trading_engine.scan_trading_opportunities()
    top_trades = trading_data.get("top_trades", [])
    
    # Get investment signals for context
    cursor = db.investment_signals.find({}, {"_id": 0}).sort("overall_score", -1).limit(200)
    investment_signals = {s["symbol"]: s for s in await cursor.to_list(length=200)}
    
    # Filter to only safe stocks and enrich with investment data
    recommended = []
    for trade in top_trades:
        # Handle both dict and Pydantic model
        if hasattr(trade, 'dict'):
            trade_dict = trade.dict()
        else:
            trade_dict = trade
            
        symbol = trade_dict.get("symbol", "").upper()
        if symbol not in PaperExecutionEngine.RISKY_STOCKS:
            # Enrich with investment data
            inv_data = investment_signals.get(symbol, {})
            trade_dict["investment_score"] = inv_data.get("overall_score")
            trade_dict["investment_category"] = inv_data.get("category")
            trade_dict["is_safe"] = True
            recommended.append(trade_dict)
    
    # Also add top investment ideas that are safe
    for symbol, inv in list(investment_signals.items())[:30]:
        if symbol not in PaperExecutionEngine.RISKY_STOCKS:
            if symbol not in [r.get("symbol") for r in recommended]:
                if inv.get("signal") == "Buy" and inv.get("overall_score", 0) >= 70:
                    recommended.append({
                        "symbol": symbol,
                        "name": inv.get("name", symbol),
                        "signal": "Buy",
                        "confidence": inv.get("confidence", 0.7),
                        "reasoning": inv.get("reasoning", "Strong fundamentals"),
                        "investment_score": inv.get("overall_score"),
                        "investment_category": inv.get("category"),
                        "is_safe": True,
                        "source": "investment"
                    })
    
    return {
        "recommended": recommended[:limit],
        "count": len(recommended[:limit]),
        "risky_excluded": len(PaperExecutionEngine.RISKY_STOCKS)
    }

# ===================== LIVE PRICES =====================

class LivePriceService:
    """Service for fetching live prices efficiently"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 5  # 5 seconds cache
        self.last_fetch = {}
    
    async def get_batch_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get quotes for multiple symbols efficiently"""
        if not symbols:
            return {}
        
        results = {}
        symbols_to_fetch = []
        current_time = datetime.now(timezone.utc).timestamp()
        
        # Check cache first
        for symbol in symbols:
            symbol = symbol.upper()
            if symbol in self.cache:
                cache_time = self.last_fetch.get(symbol, 0)
                if current_time - cache_time < self.cache_ttl:
                    results[symbol] = self.cache[symbol]
                    continue
            symbols_to_fetch.append(symbol)
        
        # Fetch missing symbols - FMP stable API requires individual calls
        if symbols_to_fetch:
            fmp_key = os.environ.get("FMP_API_KEY", "")
            
            async def fetch_single(client: httpx.AsyncClient, symbol: str):
                try:
                    response = await client.get(
                        "https://financialmodelingprep.com/stable/quote",
                        headers={"apikey": fmp_key},
                        params={"symbol": symbol},
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        quotes = response.json()
                        if quotes:
                            return quotes[0]
                except Exception as e:
                    logger.error(f"Quote fetch error for {symbol}: {e}")
                return None
            
            # Batch requests in groups of 10 to avoid rate limiting
            batch_size = 10
            async with httpx.AsyncClient() as client:
                for i in range(0, len(symbols_to_fetch), batch_size):
                    batch = symbols_to_fetch[i:i + batch_size]
                    tasks = [fetch_single(client, symbol) for symbol in batch]
                    responses = await asyncio.gather(*tasks)
                    
                    for quote in responses:
                        if quote:
                            symbol = quote.get("symbol", "")
                            price_data = {
                                "symbol": symbol,
                                "price": quote.get("price", 0),
                                "change": quote.get("change", 0),
                                "change_pct": quote.get("changePercentage", 0),
                                "day_high": quote.get("dayHigh", 0),
                                "day_low": quote.get("dayLow", 0),
                                "volume": quote.get("volume", 0),
                                "avg_volume": quote.get("avgVolume", 0),
                                "open": quote.get("open", 0),
                                "previous_close": quote.get("previousClose", 0),
                                "timestamp": current_time
                            }
                            self.cache[symbol] = price_data
                            self.last_fetch[symbol] = current_time
                            results[symbol] = price_data
                    
                    # Small delay between batches to avoid rate limiting
                    if i + batch_size < len(symbols_to_fetch):
                        await asyncio.sleep(0.1)
        
        return results
    
    async def get_single_quote(self, symbol: str) -> Optional[Dict]:
        """Get a single quote"""
        results = await self.get_batch_quotes([symbol])
        return results.get(symbol.upper())

live_price_service = LivePriceService()

@api_router.post("/prices/batch")
async def get_batch_prices(
    symbols: List[str],
    auth: bool = Depends(verify_access)
):
    """Get live prices for multiple symbols"""
    if len(symbols) > 100:
        symbols = symbols[:100]  # Limit to 100 symbols
    
    prices = await live_price_service.get_batch_quotes(symbols)
    return {"prices": prices, "count": len(prices)}

# NOTE: Specific routes must come BEFORE parameterized routes to avoid matching issues
@api_router.get("/prices/watchlist")
async def get_watchlist_prices(auth: bool = Depends(verify_access)):
    """Get live prices for all watchlist symbols"""
    cursor = db.watchlist.find({}, {"symbol": 1, "_id": 0})
    items = await cursor.to_list(length=100)
    
    if not items:
        return {"prices": {}, "count": 0}
    
    symbols = [item["symbol"] for item in items]
    prices = await live_price_service.get_batch_quotes(symbols)
    return {"prices": prices, "count": len(prices)}

@api_router.get("/prices/positions")
async def get_positions_prices(auth: bool = Depends(verify_access)):
    """Get live prices for all position symbols"""
    positions = await api_client.alpaca_positions() or []
    
    if not positions:
        return {"prices": {}, "count": 0}
    
    symbols = [pos.get("symbol", "") for pos in positions if pos.get("symbol")]
    prices = await live_price_service.get_batch_quotes(symbols)
    return {"prices": prices, "count": len(prices)}

@api_router.get("/prices/{symbol}")
async def get_single_price(symbol: str, auth: bool = Depends(verify_access)):
    """Get live price for a single symbol"""
    quote = await live_price_service.get_single_quote(symbol)
    if quote:
        return quote
    return {"symbol": symbol.upper(), "price": 0, "change": 0, "change_pct": 0}

@api_router.post("/prices/sync-signals")
async def sync_signal_prices(auth: bool = Depends(verify_access)):
    """Refresh cached signal prices using Price Integrity Service (validates freshness, rejects dead tickers)."""
    result = await price_integrity.sync_signal_prices(db)
    return result

# ===================== PRICE INTEGRITY / DIAGNOSTICS =====================

@api_router.get("/debug/price_integrity")
async def debug_price_integrity(symbols: str = None, auth: bool = Depends(verify_access)):
    """
    Diagnostics endpoint: returns validated price data for each symbol.
    If no symbols specified, audits the full universe.
    """
    if symbols:
        sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    else:
        # Get all symbols from DB
        ts_cursor = db.trading_signals.find({}, {"_id": 0, "symbol": 1})
        is_cursor = db.investment_signals.find({}, {"_id": 0, "symbol": 1})
        ts_docs = await ts_cursor.to_list(length=2000)
        is_docs = await is_cursor.to_list(length=2000)
        sym_list = list(set(
            [d["symbol"] for d in ts_docs if d.get("symbol")] +
            [d["symbol"] for d in is_docs if d.get("symbol")]
        ))

    audit = await price_integrity.audit_universe(sym_list)
    return audit

@api_router.get("/debug/price_integrity/{symbol}")
async def debug_single_price_integrity(symbol: str, auth: bool = Depends(verify_access)):
    """Detailed price integrity check for a single symbol."""
    sym = symbol.upper()
    rec = await price_integrity.get_validated_price(sym)

    # Also check what's in DB
    ts = await db.trading_signals.find_one({"symbol": sym}, {"_id": 0, "symbol": 1, "price": 1, "price_synced_at": 1, "price_source": 1, "dead_ticker": 1, "price_status": 1})
    inv = await db.investment_signals.find_one({"symbol": sym}, {"_id": 0, "symbol": 1, "price": 1, "current_price": 1, "price_synced_at": 1, "price_source": 1, "dead_ticker": 1, "price_status": 1})

    return {
        "validated": rec.to_dict(),
        "cached_trading_signal": ts,
        "cached_investment_signal": inv,
        "mismatch": ts and abs(rec.price - (ts.get("price") or 0)) > 0.01 if rec.price > 0 else False,
        "ticker_canonical": price_integrity.get_canonical_symbol(sym),
        "is_renamed": price_integrity.get_canonical_symbol(sym) != sym,
        "integrity_stats": price_integrity.get_stats(),
    }

@api_router.get("/debug/ticker_mappings")
async def get_ticker_mappings(auth: bool = Depends(verify_access)):
    """Show all known ticker renames and dead tickers."""
    return {
        "ticker_mappings": price_integrity.get_ticker_mappings(),
        "dead_tickers": price_integrity.get_dead_ticker_list(),
        "stats": price_integrity.get_stats(),
    }

# ===================== EXECUTION TRANSPARENCY ROUTES =====================

@api_router.get("/execution/rejection-report")
async def get_rejection_report(
    date: str = None, engine: str = None, limit: int = 100,
    auth: bool = Depends(verify_access)
):
    """Full candidate-to-execution rejection report showing why setups weren't traded."""
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report = await exec_transparency.get_rejection_report(date, engine, limit)
    return report


@api_router.get("/execution/pipeline-stages")
async def get_pipeline_stages(date: str = None, auth: bool = Depends(verify_access)):
    """Breakdown of how many candidates reached each pipeline stage."""
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stages = await exec_transparency.get_pipeline_stages(date)
    return stages


@api_router.get("/execution/diagnostics")
async def get_execution_diagnostics(auth: bool = Depends(verify_access)):
    """Live execution diagnostics — score breakdowns, pipeline health, confidence distribution.
    Shows exactly why signals pass or fail, with per-component scoring detail."""
    from ai_trading_system import (
        ConfidenceScoringEngine, StockClassifier, DynamicThresholdManager
    )

    # Get current settings and regime
    settings = await auto_orchestrator.get_settings()
    market_regime = await auto_orchestrator.regime_detector.detect()
    dynamic = DynamicThresholdManager.get_thresholds(market_regime, settings)
    threshold = dynamic["dt_threshold"]

    # Get current trading signals
    trading_signals = await db.trading_signals.find(
        {"dead_ticker": {"$ne": True}}, {"_id": 0}
    ).to_list(2000)
    investment_signals = await db.investment_signals.find(
        {"dead_ticker": {"$ne": True}}, {"_id": 0}
    ).to_list(2000)
    inv_lookup = {s["symbol"]: s for s in investment_signals if s.get("symbol")}

    # Score every signal with full breakdown
    all_breakdowns = []
    classification_counts = {"DAY_TRADE": 0, "LONG_TERM": 0, "WATCHLIST": 0, "NO_TRADE": 0}
    for sig in trading_signals:
        symbol = sig.get("symbol", "")
        if not symbol:
            continue
        cls_result = StockClassifier.classify(sig, inv_lookup.get(symbol))
        cls = cls_result["classification"]
        classification_counts[cls] = classification_counts.get(cls, 0) + 1

        if cls != "DAY_TRADE":
            continue

        confidence, breakdown = ConfidenceScoringEngine.score_day_trade(sig, market_regime, return_breakdown=True)
        all_breakdowns.append({
            "symbol": symbol,
            "confidence": confidence,
            "passes_threshold": confidence >= threshold,
            "gap_to_threshold": confidence - threshold,
            "breakdown": breakdown,
            "price": sig.get("price", 0),
            "signal_type": sig.get("signal", ""),
            "structure_type": sig.get("indicators", {}).get("structure_type", ""),
        })

    all_breakdowns.sort(key=lambda x: x["confidence"], reverse=True)

    # Distribution analysis
    passing = [b for b in all_breakdowns if b["passes_threshold"]]
    near_miss = [b for b in all_breakdowns if -12 <= b["gap_to_threshold"] < 0]

    # Component weakness analysis: which scoring categories are weakest across all signals?
    component_totals = {}
    for b in all_breakdowns:
        bd = b["breakdown"]
        for comp_name, comp_data in bd.items():
            if isinstance(comp_data, dict) and "pts" in comp_data and "max" in comp_data:
                if comp_name not in component_totals:
                    component_totals[comp_name] = {"total_pts": 0, "total_max": 0, "count": 0}
                component_totals[comp_name]["total_pts"] += comp_data["pts"]
                component_totals[comp_name]["total_max"] += comp_data["max"]
                component_totals[comp_name]["count"] += 1

    component_avg = {}
    for comp, data in component_totals.items():
        avg_pts = data["total_pts"] / data["count"] if data["count"] > 0 else 0
        max_pts = data["total_max"] / data["count"] if data["count"] > 0 else 0
        pct = (avg_pts / max_pts * 100) if max_pts > 0 else 0
        component_avg[comp] = {
            "avg_pts": round(avg_pts, 1),
            "max_pts": round(max_pts, 1),
            "utilization_pct": round(pct, 1),
        }

    # Recent scheduler cycles
    recent_cycles = await db.scheduler_execution_log.find(
        {"action": "day_trade_cycle"}, {"_id": 0}
    ).sort("timestamp", -1).limit(5).to_list(5)

    # Recent confidence distributions
    recent_conf = await db.confidence_distribution.find(
        {}, {"_id": 0}
    ).sort("timestamp", -1).limit(5).to_list(5)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_regime": market_regime,
        "dynamic_thresholds": dynamic,
        "threshold_used": threshold,
        "total_signals": len(trading_signals),
        "classification_counts": classification_counts,
        "dt_classified": len(all_breakdowns),
        "passing_threshold": len(passing),
        "near_miss_count": len(near_miss),
        "top_signals": all_breakdowns[:15],
        "near_misses": near_miss[:10],
        "component_utilization": component_avg,
        "recent_cycles": recent_cycles,
        "recent_confidence_distributions": recent_conf,
        "scheduler_status": (await auto_scheduler.get_status()),
    }


# ===================== SEPARATED ANALYTICS ROUTES =====================

@api_router.get("/analytics/by-strategy")
async def get_analytics_by_strategy(auth: bool = Depends(verify_access)):
    """Completely separated analytics: Day Trading vs Long-Term vs Manual positions."""

    # --- Day Trading Analytics from Alpaca fills ---
    dt_round_trips = []
    try:
        # Get all fills from Alpaca
        async with httpx.AsyncClient() as hclient:
            fills_resp = await hclient.get(
                f"{api_client.alpaca_url}/v2/account/activities/FILL",
                headers=api_client.alpaca_headers,
                params={"limit": 200},
                timeout=10
            )
            if fills_resp.status_code == 200:
                fills = fills_resp.json()
                # Group by order_id → then match buys to sells per symbol
                buy_fills = {}  # symbol → [{price, qty, time}]
                sell_fills = {}

                for f in fills:
                    sym = f.get("symbol", "")
                    side = f.get("side", "")
                    price = float(f.get("price", 0))
                    qty = float(f.get("qty", 0))
                    time = f.get("transaction_time", "")
                    entry = {"price": price, "qty": qty, "time": time}

                    if side == "buy":
                        buy_fills.setdefault(sym, []).append(entry)
                    elif side == "sell":
                        sell_fills.setdefault(sym, []).append(entry)

                # Build round trips (buy → sell matches)
                for sym in sell_fills:
                    if sym not in buy_fills:
                        continue
                    total_buy_qty = sum(b["qty"] for b in buy_fills[sym])
                    total_sell_qty = sum(s["qty"] for s in sell_fills[sym])
                    avg_buy = sum(b["price"] * b["qty"] for b in buy_fills[sym]) / total_buy_qty if total_buy_qty else 0
                    avg_sell = sum(s["price"] * s["qty"] for s in sell_fills[sym]) / total_sell_qty if total_sell_qty else 0
                    closed_qty = min(total_buy_qty, total_sell_qty)
                    pnl_per_share = avg_sell - avg_buy
                    pnl_dollars = round(pnl_per_share * closed_qty, 2)
                    pnl_pct = round((pnl_per_share / avg_buy) * 100, 2) if avg_buy > 0 else 0

                    dt_round_trips.append({
                        "symbol": sym,
                        "qty": closed_qty,
                        "avg_buy": round(avg_buy, 2),
                        "avg_sell": round(avg_sell, 2),
                        "pnl_dollars": pnl_dollars,
                        "pnl_pct": pnl_pct,
                        "buy_time": buy_fills[sym][0]["time"][:19] if buy_fills[sym] else "",
                        "sell_time": sell_fills[sym][0]["time"][:19] if sell_fills[sym] else "",
                    })
    except Exception as e:
        logger.warning(f"Alpaca fills fetch failed: {e}")

    dt_wins = [t for t in dt_round_trips if t["pnl_dollars"] > 0]
    dt_losses = [t for t in dt_round_trips if t["pnl_dollars"] < 0]
    dt_total_pnl = sum(t["pnl_dollars"] for t in dt_round_trips)
    dt_avg_win = sum(t["pnl_pct"] for t in dt_wins) / len(dt_wins) if dt_wins else 0
    dt_avg_loss = sum(t["pnl_pct"] for t in dt_losses) / len(dt_losses) if dt_losses else 0
    dt_best = max(dt_round_trips, key=lambda t: t["pnl_pct"], default={})
    dt_worst = min(dt_round_trips, key=lambda t: t["pnl_pct"], default={})

    # Setup type breakdown - not available from Alpaca fills, skip for now

    # --- Long-Term Analytics ---
    lt_positions = await lt_engine.get_positions()
    lt_closed_cursor = db.lt_portfolio.find({"status": "closed"}, {"_id": 0}).sort("closed_at", -1).limit(100)
    lt_closed = await lt_closed_cursor.to_list(length=100)

    lt_total_value = sum(p.get("current_value", 0) for p in lt_positions)
    lt_total_cost = sum(p.get("shares", 0) * p.get("avg_cost", 0) for p in lt_positions)
    lt_pnl = lt_total_value - lt_total_cost if lt_total_cost > 0 else 0

    lt_rebalance_cursor = db.lt_rebalance_log.find({}, {"_id": 0}).sort("timestamp", -1).limit(50)
    lt_actions = await lt_rebalance_cursor.to_list(length=50)

    # --- Manual/External Positions ---
    manual_positions = []
    try:
        all_positions = await api_client.alpaca_positions()
        if all_positions:
            bot_symbols = set()
            cursor_bot = db.auto_trade_log.find(
                {"ownership": "bot", "action": "BUY"},
                {"_id": 0, "symbol": 1}
            )
            async for doc in cursor_bot:
                bot_symbols.add(doc.get("symbol", ""))
            lt_held = {p["symbol"] for p in lt_positions}

            for p in all_positions:
                sym = p.get("symbol", "")
                if sym not in bot_symbols and sym not in lt_held:
                    manual_positions.append({
                        "symbol": sym,
                        "qty": p.get("qty", 0),
                        "avg_entry_price": float(p.get("avg_entry_price", 0)),
                        "market_value": float(p.get("market_value", 0)),
                        "unrealized_pl": float(p.get("unrealized_pl", 0)),
                        "unrealized_plpc": round(float(p.get("unrealized_plpc", 0)) * 100, 2),
                        "classification": "manual",
                    })
    except Exception as e:
        logger.warning(f"Manual positions check failed: {e}")

    # --- Current open DT positions ---
    dt_open_positions = []
    try:
        all_pos = await api_client.alpaca_positions()
        if all_pos:
            for p in all_pos:
                sym = p.get("symbol", "")
                log = await db.auto_trade_log.find_one(
                    {"symbol": sym, "ownership": "bot", "strategy_type": "day_trade"},
                    sort=[("timestamp", -1)]
                )
                if log:
                    dt_open_positions.append({
                        "symbol": sym,
                        "qty": p.get("qty", 0),
                        "avg_entry_price": float(p.get("avg_entry_price", 0)),
                        "market_value": float(p.get("market_value", 0)),
                        "unrealized_pl": float(p.get("unrealized_pl", 0)),
                        "unrealized_plpc": round(float(p.get("unrealized_plpc", 0)) * 100, 2),
                        "confidence": log.get("confidence", 0),
                    })
    except Exception:
        pass

    return {
        "day_trading": {
            "total_trades": len(dt_round_trips) + len(dt_open_positions),
            "closed_trades": len(dt_round_trips),
            "open_positions": dt_open_positions,
            "win_rate": round(len(dt_wins) / len(dt_round_trips) * 100, 1) if dt_round_trips else 0,
            "total_pnl": round(dt_total_pnl, 2),
            "average_win_pct": round(dt_avg_win, 2),
            "average_loss_pct": round(dt_avg_loss, 2),
            "best_trade": {"symbol": dt_best.get("symbol"), "pnl_pct": dt_best.get("pnl_pct", 0), "pnl_dollars": dt_best.get("pnl_dollars", 0)} if dt_best else {},
            "worst_trade": {"symbol": dt_worst.get("symbol"), "pnl_pct": dt_worst.get("pnl_pct", 0), "pnl_dollars": dt_worst.get("pnl_dollars", 0)} if dt_worst else {},
            "round_trips": dt_round_trips,
        },
        "long_term": {
            "active_positions": len(lt_positions),
            "closed_positions": len(lt_closed),
            "total_value": round(lt_total_value, 2),
            "total_cost": round(lt_total_cost, 2),
            "unrealized_pnl": round(lt_pnl, 2),
            "positions": [{
                "symbol": p.get("symbol"), "bucket": p.get("bucket"),
                "shares": p.get("shares"), "avg_cost": p.get("avg_cost"),
                "current_value": p.get("current_value", 0),
                "pnl_pct": p.get("pnl_pct", 0),
                "stage": p.get("stage", 0),
            } for p in lt_positions],
            "recent_actions": lt_actions[:10],
        },
        "manual_external": {
            "position_count": len(manual_positions),
            "positions": manual_positions,
            "total_value": round(sum(p.get("market_value", 0) for p in manual_positions), 2),
            "total_unrealized_pnl": round(sum(p.get("unrealized_pl", 0) for p in manual_positions), 2),
            "note": "These positions are PROTECTED — bot will never touch them",
        },
    }


# ===================== LONG-TERM INVESTING ROUTES =====================

@api_router.get("/lt-invest/portfolio")
async def get_lt_portfolio(auth: bool = Depends(verify_access)):
    """Get full long-term investment portfolio with live prices."""
    price_lookup = {}
    positions = await lt_engine.get_positions()
    if positions:
        symbols = [p["symbol"] for p in positions]
        try:
            batch = await price_integrity.get_batch_validated(symbols)
            for sym, record in batch.items():
                if record and record.price > 0:
                    price_lookup[sym] = record.price
        except Exception as e:
            logger.warning(f"LT price lookup partial failure: {e}")

    portfolio = await lt_engine.get_portfolio_summary(price_lookup)
    return portfolio


@api_router.get("/lt-invest/universe")
async def get_lt_universe(auth: bool = Depends(verify_access)):
    """Get the long-term investment universe organized by bucket."""
    return lt_engine.get_universe()


@api_router.get("/lt-invest/recommendations")
async def get_lt_recommendations(auth: bool = Depends(verify_access)):
    """Generate buy/add/trim recommendations for the LT portfolio."""
    price_lookup = {}
    positions = await lt_engine.get_positions()
    if positions:
        symbols = [p["symbol"] for p in positions]
        try:
            batch = await price_integrity.get_batch_validated(symbols)
            for sym, record in batch.items():
                if record and record.price > 0:
                    price_lookup[sym] = record.price
        except Exception as e:
            logger.warning(f"LT rec price lookup failure: {e}")

    investment_signals = {}
    try:
        cursor = db.investment_signals.find({}, {"_id": 0}).limit(300)
        async for doc in cursor:
            sym = doc.get("symbol", "")
            if sym:
                investment_signals[sym] = doc
    except Exception:
        pass

    recs = await lt_engine.generate_recommendations(price_lookup, investment_signals)
    return {"recommendations": recs, "count": len(recs)}


@api_router.post("/lt-invest/stage-buy")
async def lt_stage_buy(
    request: dict,
    auth: bool = Depends(verify_access)
):
    """Execute a staged buy (25% increment) for a long-term position."""
    symbol = request.get("symbol", "").upper()
    bucket = request.get("bucket", "")
    shares = float(request.get("shares", 0))
    price = float(request.get("price", 0))
    thesis = request.get("thesis", "")
    name = request.get("name", "")

    if not symbol or not bucket or shares <= 0 or price <= 0:
        return {"error": "Missing required fields: symbol, bucket, shares, price"}

    from long_term_engine import BUCKET_RULES
    if bucket not in BUCKET_RULES:
        return {"error": f"Invalid bucket: {bucket}. Must be one of: {list(BUCKET_RULES.keys())}"}

    result = await lt_engine.stage_buy(symbol, bucket, shares, price, thesis, name)
    return {"success": True, "position": result}


@api_router.post("/lt-invest/trim")
async def lt_trim_position(
    request: dict,
    auth: bool = Depends(verify_access)
):
    """Trim (partial sell) a long-term position."""
    symbol = request.get("symbol", "").upper()
    shares = float(request.get("shares", 0))
    price = float(request.get("price", 0))
    reason = request.get("reason", "")

    if not symbol or shares <= 0 or price <= 0:
        return {"error": "Missing required fields: symbol, shares, price"}

    result = await lt_engine.trim_position(symbol, shares, price, reason)
    return result


@api_router.post("/lt-invest/close")
async def lt_close_position(
    request: dict,
    auth: bool = Depends(verify_access)
):
    """Close a long-term position entirely."""
    symbol = request.get("symbol", "").upper()
    reason = request.get("reason", "")

    if not symbol:
        return {"error": "Missing required field: symbol"}

    await lt_engine.close_position(symbol, reason)
    return {"success": True, "symbol": symbol, "action": "closed"}


@api_router.get("/lt-invest/thesis/{symbol}")
async def get_lt_thesis(symbol: str, auth: bool = Depends(verify_access)):
    """Get thesis health for a specific long-term position."""
    investment_signal = None
    try:
        investment_signal = await db.investment_signals.find_one(
            {"symbol": symbol.upper()}, {"_id": 0}
        )
    except Exception:
        pass

    health = await lt_engine.get_thesis_health(symbol.upper(), investment_signal)
    return health


@api_router.get("/lt-invest/rebalance-check")
async def lt_rebalance_check(auth: bool = Depends(verify_access)):
    """Check if rebalancing is needed and return reasons."""
    price_lookup = {}
    positions = await lt_engine.get_positions()
    if positions:
        symbols = [p["symbol"] for p in positions]
        try:
            batch = await price_integrity.get_batch_validated(symbols)
            for sym, record in batch.items():
                if record and record.price > 0:
                    price_lookup[sym] = record.price
        except Exception as e:
            logger.warning(f"LT rebalance price lookup failure: {e}")

    portfolio = await lt_engine.get_portfolio_summary(price_lookup)
    summary = portfolio.get("summary", {})
    return {
        "needs_rebalance": summary.get("needs_rebalance", False),
        "reasons": summary.get("rebalance_reasons", []),
        "bucket_allocation": summary.get("bucket_allocation", {}),
        "diversification_score": summary.get("diversification_score", 0),
    }


@api_router.get("/lt-invest/market-overview")
async def get_lt_market_overview(auth: bool = Depends(verify_access)):
    """Unified market view merging trading signals + investment signals + live prices + ratings.
    Labels match the Trading Signals and Investment Ideas tabs."""

    # 1. Fetch all trading signals
    trading_signals = {}
    try:
        cursor = db.trading_signals.find({}, {"_id": 0})
        async for doc in cursor:
            sym = doc.get("symbol", "")
            if sym:
                trading_signals[sym] = doc
    except Exception as e:
        logger.warning(f"LT market overview trading signals error: {e}")

    # 2. Fetch all investment signals
    investment_signals = {}
    try:
        cursor = db.investment_signals.find({}, {"_id": 0})
        async for doc in cursor:
            sym = doc.get("symbol", "")
            if sym:
                investment_signals[sym] = doc
    except Exception as e:
        logger.warning(f"LT market overview investment signals error: {e}")

    # 3. Merge into unified list
    all_symbols = set(list(trading_signals.keys()) + list(investment_signals.keys()))

    # 4. Get live prices for all symbols
    price_lookup = {}
    sym_list = list(all_symbols)
    try:
        for i in range(0, len(sym_list), 50):
            batch_syms = sym_list[i:i+50]
            batch = await price_integrity.get_batch_validated(batch_syms)
            for sym, record in batch.items():
                if record and record.price > 0:
                    price_lookup[sym] = record.price
    except Exception as e:
        logger.warning(f"LT market overview price lookup failure: {e}")

    # 5. Get LT portfolio positions for held status
    positions = await lt_engine.get_positions()
    held_symbols = {p["symbol"] for p in positions}

    # 6. Build unified company entries
    companies = []
    for sym in sorted(all_symbols):
        t_sig = trading_signals.get(sym, {})
        i_sig = investment_signals.get(sym, {})

        live_price = price_lookup.get(sym, t_sig.get("price") or i_sig.get("price") or 0)

        # Trading signal data
        trade_signal = t_sig.get("signal", "")
        trade_confidence = t_sig.get("confidence", 0)
        if isinstance(trade_confidence, float) and trade_confidence <= 1:
            trade_confidence = round(trade_confidence * 100)
        entry_zone = t_sig.get("entry_zone", "")
        stop_loss = t_sig.get("stop_loss", "")
        take_profit = t_sig.get("take_profit", "")
        risk_reward = t_sig.get("risk_reward", "")
        trade_reasoning = t_sig.get("reasoning", "")
        trade_category = t_sig.get("category", "")
        trade_indicators = t_sig.get("indicators", {})

        # Investment signal data
        inv_signal = i_sig.get("signal", "")
        inv_score = i_sig.get("overall_score", 0)
        inv_category = i_sig.get("category", "")
        inv_reasoning = i_sig.get("reasoning", "")
        bull_case = i_sig.get("bull_case", [])
        bear_case = i_sig.get("bear_case", [])
        valuation = i_sig.get("valuation_summary", {})
        quality = i_sig.get("business_quality", {})
        growth = i_sig.get("growth_profile", {})
        historical = i_sig.get("historical_performance", {})

        # Performance rating (0-100, combines trading + investment scores)
        rating_score = 0
        rating_label = "Unrated"
        rating_sources = []
        if inv_score > 0:
            rating_score = inv_score
            rating_sources.append(f"Investment: {inv_score:.0f}")
        if trade_confidence > 0:
            if rating_score > 0:
                rating_score = round((rating_score + trade_confidence) / 2)
            else:
                rating_score = trade_confidence
            rating_sources.append(f"Trading: {trade_confidence}")

        if rating_score >= 80:
            rating_label = "Strong"
        elif rating_score >= 65:
            rating_label = "Good"
        elif rating_score >= 50:
            rating_label = "Average"
        elif rating_score >= 35:
            rating_label = "Weak"
        elif rating_score > 0:
            rating_label = "Poor"

        # Determine primary label (matches Trading/Investments tabs)
        primary_label = trade_category or inv_category or "Unclassified"
        primary_signal = trade_signal or inv_signal or "N/A"

        entry = {
            "symbol": sym,
            "name": t_sig.get("name") or i_sig.get("name", sym),
            "sector": i_sig.get("sector", ""),
            "industry": i_sig.get("industry", ""),
            "live_price": round(live_price, 2) if live_price else 0,
            "is_held": sym in held_symbols,
            # Labels (match Trading & Investments tabs)
            "primary_label": primary_label,
            "primary_signal": primary_signal,
            # Trading analysis
            "trade_signal": trade_signal,
            "trade_confidence": trade_confidence,
            "trade_category": trade_category,
            "entry_zone": entry_zone,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward": risk_reward,
            "trade_reasoning": trade_reasoning,
            "trade_indicators": {
                "change_pct": trade_indicators.get("change_pct", 0),
                "volume_ratio": trade_indicators.get("volume_ratio", 0),
                "atr_pct": trade_indicators.get("atr_pct", 0),
                "structure_type": trade_indicators.get("structure_type", ""),
                "confluence_score": trade_indicators.get("confluence_score", 0),
            },
            # Investment analysis
            "inv_signal": inv_signal,
            "inv_score": round(inv_score, 1) if inv_score else 0,
            "inv_category": inv_category,
            "inv_reasoning": inv_reasoning,
            "bull_case": bull_case[:3] if bull_case else [],
            "bear_case": bear_case[:3] if bear_case else [],
            "valuation": {
                "classification": valuation.get("classification", "N/A") if isinstance(valuation, dict) else "N/A",
                "pe_ratio": valuation.get("pe_ratio") if isinstance(valuation, dict) else None,
                "upside_potential": i_sig.get("upside_potential", ""),
                "fair_value": valuation.get("intrinsic_value") if isinstance(valuation, dict) else (i_sig.get("intrinsic_value")),
            },
            "quality_rating": quality.get("quality_rating", "N/A") if isinstance(quality, dict) else "N/A",
            "growth_trend": growth.get("growth_trend", "N/A") if isinstance(growth, dict) else "N/A",
            "historical_rating": historical.get("historical_rating", "N/A") if isinstance(historical, dict) else "N/A",
            # Combined rating
            "rating_score": rating_score,
            "rating_label": rating_label,
            "rating_sources": rating_sources,
            # Source flags
            "has_trading_signal": bool(t_sig),
            "has_investment_signal": bool(i_sig),
        }
        companies.append(entry)

    # Sort by rating score descending
    companies.sort(key=lambda x: x["rating_score"], reverse=True)

    # Category counts
    categories = {}
    for c in companies:
        lbl = c["primary_label"]
        categories[lbl] = categories.get(lbl, 0) + 1

    return {
        "companies": companies,
        "total": len(companies),
        "categories": categories,
        "sources": {
            "trading_signals": len(trading_signals),
            "investment_signals": len(investment_signals),
            "with_live_price": len(price_lookup),
        },
    }


# Health check (no auth required)
@api_router.get("/")
async def root():
    return {"name": "ObaidTradez API", "version": "3.0.0", "status": "running"}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event to initialize universe
@app.on_event("startup")
async def startup_event():
    """Initialize the investment universe and auto-recover scheduler on startup"""
    try:
        # Check if we have any cached signals
        count = await db.investment_signals.count_documents({})
        if count == 0:
            logger.info("No cached signals found, starting initial load...")
            asyncio.create_task(investment_engine.refresh_universe_signals(200))
        
        # Auto-recover scheduler if it was running before restart
        saved_state = await db.scheduler_state.find_one({"_id": "config"})
        auto_settings = await db.auto_trade_settings.find_one({})
        was_running = saved_state and saved_state.get("status") == "running"
        is_enabled = auto_settings and auto_settings.get("auto_enabled", False)
        
        if was_running or is_enabled:
            logger.info(f"AUTO-RECOVERY: was_running={was_running}, auto_enabled={is_enabled} — restarting scheduler")
            await auto_scheduler.initialize()
            result = await auto_scheduler.start()
            # Record recovery timestamp
            await db.scheduler_state.update_one(
                {"_id": "config"},
                {"$set": {"last_auto_recovery": datetime.now(timezone.utc).isoformat()}},
                upsert=True
            )
            logger.info(f"AUTO-RECOVERY: Scheduler restored: {result}")
            
            # Start live price engine with scanned symbols
            try:
                scan = await auto_orchestrator.scan_opportunities()
                symbols = set()
                for c in scan.get("watchlist", []):
                    symbols.add(c.get("symbol", ""))
                for c in scan.get("long_term_candidates", []):
                    symbols.add(c.get("symbol", ""))
                symbols.discard("")
                if symbols:
                    await live_price_engine.start(list(symbols))
                    logger.info(f"AUTO-RECOVERY: Live prices started for {len(symbols)} symbols")
            except Exception as lpe:
                logger.warning(f"Live price engine start failed (non-fatal): {lpe}")
        
        # Sync cached signal prices with validated freshness checks
        try:
            result = await price_integrity.sync_signal_prices(db)
            logger.info(f"Startup price sync: {result}")
        except Exception as e:
            logger.warning(f"Startup price sync failed (non-fatal): {e}")

        # Start periodic price sync background task
        asyncio.create_task(_periodic_price_sync())

        # Start market-open verifier watcher
        asyncio.create_task(_market_open_verifier_watcher())
        
    except Exception as e:
        logger.error(f"Startup error: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

async def _periodic_price_sync():
    """Background task: sync signal prices every 5 minutes during market hours."""
    from auto_trade_scheduler import MarketSessionManager, MarketSession
    while True:
        try:
            await asyncio.sleep(300)  # 5 minutes
            session = MarketSessionManager.get_session()
            if session in (MarketSession.PRE_MARKET, MarketSession.REGULAR, MarketSession.CLOSING):
                result = await price_integrity.sync_signal_prices(db)
                if result.get("updated", 0) > 0:
                    logger.info(f"Periodic price sync: {result}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Periodic price sync error: {e}")
            await asyncio.sleep(60)


async def _market_open_verifier_watcher():
    """Background task: auto-starts the re-eval verifier at market open, stops after 30 min."""
    from auto_trade_scheduler import MarketSessionManager, MarketSession, _now_et
    from reeval_verifier import VERIFICATION_WINDOW_SECONDS
    started_today = False
    last_date = None

    while True:
        try:
            await asyncio.sleep(30)
            now_et = _now_et()
            session = MarketSessionManager.get_session()
            today = now_et.date()

            # Reset daily flag
            if last_date != today:
                started_today = False
                last_date = today

            # Auto-start at regular market open (first time today)
            if session == MarketSession.REGULAR and not started_today and not reeval_verifier.is_active:
                engine_status = live_price_engine.get_status()
                reeval_verifier.start(engine_status)
                started_today = True
                logger.info("VERIFIER: Auto-started at market open")

                # Schedule auto-stop after verification window
                async def auto_stop():
                    await asyncio.sleep(VERIFICATION_WINDOW_SECONDS)
                    if reeval_verifier.is_active:
                        reeval_verifier.stop()
                        report = reeval_verifier.get_report()
                        logger.info(
                            f"VERIFIER: Auto-stopped after {VERIFICATION_WINDOW_SECONDS}s | "
                            f"Events: {report['summary']['total_events']} | "
                            f"Symbols: {report['summary']['unique_symbols']} | "
                            f"Setup changes: {report['summary']['setup_changes']} | "
                            f"Errors: {len(report.get('errors', []))}"
                        )
                        # Persist report to DB
                        await db.reeval_verification.insert_one({
                            "date": today.isoformat(),
                            "report": report,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                asyncio.create_task(auto_stop())

            # Feed engine status to verifier while active
            if reeval_verifier.is_active:
                reeval_verifier.update_engine_status(live_price_engine.get_status())

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Verifier watcher error: {e}")
            await asyncio.sleep(60)
