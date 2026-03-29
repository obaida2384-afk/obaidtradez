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
    
    async def fmp_historical(self, symbol: str) -> Optional[List]:
        data = await self._request(
            f"{self.fmp_url}/historical-price-eod/full",
            headers={"apikey": config.FMP_API_KEY},
            params={"symbol": symbol}
        )
        return data if isinstance(data, list) else None
    
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

# ===================== UNIVERSE MANAGER =====================

class UniverseManager:
    """Manages the investment universe - fetching, storing, and updating stock lists"""
    
    # Comprehensive stock universe - covering major sectors and market caps
    CORE_UNIVERSE = [
        # Mega Cap Tech
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL",
        # Large Cap Tech
        "CRM", "ADBE", "AMD", "INTC", "CSCO", "TXN", "QCOM", "IBM", "NOW", "INTU",
        "AMAT", "ADI", "LRCX", "MU", "SNPS", "CDNS", "KLAC", "MRVL", "FTNT", "PANW",
        # Software & Cloud
        "SNOW", "DDOG", "ZS", "CRWD", "NET", "MDB", "OKTA", "PLTR", "PATH", "SHOP",
        "WDAY", "TTD", "HUBS", "VEEV", "ZM", "DOCU", "TEAM", "SPLK", "TWLO", "U",
        # Semiconductors
        "ASML", "TSM", "ARM", "ON", "MCHP", "SWKS", "NXPI", "GFS", "WOLF",
        # Financial Services
        "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "C",
        "AXP", "USB", "PNC", "TFC", "COF", "BK", "AIG", "PRU", "MET", "AFL",
        "CME", "ICE", "SPGI", "MCO", "MSCI", "FIS", "PYPL", "SQ", "FI", "COIN",
        # Healthcare
        "UNH", "JNJ", "LLY", "PFE", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY",
        "AMGN", "GILD", "VRTX", "REGN", "MRNA", "BIIB", "ILMN", "ISRG", "SYK", "BSX",
        "MDT", "ZBH", "EW", "BDX", "DXCM", "ALGN", "IDXX", "IQV", "A", "MTD",
        # Consumer Discretionary
        "HD", "NKE", "MCD", "SBUX", "LOW", "TJX", "TGT", "ROST", "CMG", "DHI",
        "LEN", "GM", "F", "ABNB", "BKNG", "MAR", "HLT", "ORLY", "AZO", "BBY",
        "DPZ", "YUM", "LULU", "RCL", "CCL", "WYNN", "LVS", "MGM", "DRI", "EBAY",
        # Consumer Staples
        "PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL", "MDLZ", "KMB",
        "GIS", "K", "HSY", "SJM", "CAG", "KHC", "STZ", "BF.B", "TAP", "EL",
        # Industrials
        "UNP", "HON", "UPS", "BA", "CAT", "GE", "RTX", "DE", "LMT", "NOC",
        "MMM", "ITW", "EMR", "ROK", "ETN", "PH", "GD", "WM", "RSG", "CTAS",
        "FDX", "CSX", "NSC", "PCAR", "CMI", "TT", "IR", "FAST", "ODFL", "J",
        # Energy
        "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "PXD",
        "HES", "DVN", "FANG", "HAL", "BKR", "KMI", "WMB", "OKE", "LNG", "TRGP",
        # Materials
        "LIN", "APD", "ECL", "SHW", "DD", "NEM", "FCX", "NUE", "VMC", "MLM",
        "DOW", "PPG", "ALB", "CTVA", "CF", "MOS", "IFF", "FMC", "CE", "EMN",
        # Utilities
        "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "PEG", "ED",
        "WEC", "ES", "AWK", "DTE", "ETR", "FE", "AEE", "CMS", "EVRG", "AES",
        # Real Estate
        "PLD", "AMT", "EQIX", "CCI", "PSA", "SPG", "O", "VICI", "WELL", "DLR",
        "AVB", "EQR", "ARE", "MAA", "ESS", "UDR", "VTR", "PEAK", "SUI", "HST",
        # Communication Services
        "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS", "CHTR", "WBD", "PARA", "FOX",
        "OMC", "IPG", "EA", "TTWO", "RBLX", "MTCH", "LYV", "SPOT", "PINS", "SNAP",
        # High Growth / Momentum
        "SMCI", "MSTR", "APP", "CELH", "DUOL", "DKNG", "DASH", "RKLB", "IONQ", "SOUN",
        "AI", "UPST", "SOFI", "HOOD", "AFRM", "RIVN", "LCID", "NIO", "XPEV", "LI",
        # Small/Mid Cap Value
        "SNA", "LKQ", "JBL", "TOL", "STLD", "CLF", "X", "AA", "RHI", "JBHT",
        "CHRW", "XPO", "SAIA", "LSTR", "WERN", "KNX", "ARCB", "HUBG", "HTLD", "MATX",
        # Financials - Regional Banks & Insurance
        "HBAN", "KEY", "CFG", "MTB", "RF", "FITB", "ZION", "CMA", "FCNCA", "SIVB",
        "CINF", "CB", "TRV", "ALL", "PGR", "HIG", "L", "WRB", "RE", "RNR",
        # Biotech
        "ALNY", "SGEN", "BMRN", "SRPT", "EXEL", "INCY", "HALO", "PCVX", "BNTX", "NVAX",
        "CRSP", "BEAM", "EDIT", "NTLA", "VERV", "FATE", "RCKT", "BLUE", "SGMO", "RARE",
        # Clean Energy & EV
        "ENPH", "SEDG", "FSLR", "RUN", "NOVA", "PLUG", "BE", "CHPT", "BLNK", "EVGO",
        "QS", "SLDP", "MVST", "MP", "LAC", "ALB", "LTHM", "SQM", "PLL", "LIVENT",
        # Cybersecurity
        "S", "CYBR", "TENB", "QLYS", "RPD", "VRNS", "SAIL", "SWI", "SCWX", "NTCT"
    ]
    
    # ETFs for sector exposure
    CORE_ETFS = [
        "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "VEA", "VWO", "EFA", "EEM",
        "XLF", "XLK", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE",
        "GLD", "SLV", "TLT", "HYG", "LQD", "VNQ", "ARKK", "ARKG", "ARKF", "ARKW",
        "SMH", "SOXX", "IBB", "XBI", "ICLN", "TAN", "LIT", "HACK", "SKYY", "CLOU"
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
            
            vol_ratio = volume / avg_volume if avg_volume > 0 else 1
            price_vs_50 = ((price / sma50) - 1) * 100 if sma50 > 0 else 0
            price_vs_200 = ((price / sma200) - 1) * 100 if sma200 > 0 else 0
            
            range_52 = high_52 - low_52 if high_52 > low_52 else 1
            position_52 = ((price - low_52) / range_52) * 100 if range_52 > 0 else 50
            
            momentum_score = 50
            volume_score = 50
            technical_score = 50
            trend_score = 50
            
            reasons = []
            
            if change_pct > 3:
                momentum_score += 25
                reasons.append(f"Strong momentum (+{change_pct:.1f}% today)")
            elif change_pct > 1:
                momentum_score += 15
            elif change_pct < -3:
                momentum_score -= 20
                reasons.append(f"Weak price action ({change_pct:.1f}%)")
            
            if vol_ratio > 2:
                volume_score += 30
                reasons.append(f"High volume ({vol_ratio:.1f}x average)")
            elif vol_ratio > 1.5:
                volume_score += 15
            elif vol_ratio < 0.5:
                volume_score -= 15
            
            if price > sma50 > sma200:
                technical_score += 25
                trend_score += 20
                reasons.append("Bullish MA alignment")
            elif price > sma50:
                technical_score += 10
            elif price < sma50 < sma200:
                technical_score -= 20
                reasons.append("Bearish trend")
            
            if position_52 > 90 and vol_ratio > 1.5:
                technical_score += 20
                reasons.append("Near 52-week high with volume (breakout)")
            elif position_52 < 20:
                technical_score -= 10
            
            overall = (momentum_score * 0.30 + volume_score * 0.25 + 
                      technical_score * 0.25 + trend_score * 0.20)
            
            if overall >= 70 and len(reasons) >= 2:
                signal = "Buy"
                category = "Hot" if overall >= 80 else "Breakout"
            elif overall >= 55:
                signal = "Watch"
                category = "Medium"
            else:
                signal = "Avoid"
                category = "Avoid"
            
            entry_zone = f"${price * 0.98:.2f} - ${price:.2f}"
            stop_loss = round(price * 0.95, 2)
            take_profit = round(price * 1.10, 2)
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
    limit: int = Query(default=300, ge=50, le=1000),
    auth: bool = Depends(verify_access)
):
    """Trigger investment signals refresh using enhanced engine"""
    
    async def refresh_with_enhanced_engine(limit: int):
        """Background task to refresh signals using enhanced engine"""
        symbols = universe_manager.CORE_UNIVERSE[:limit]
        logger.info(f"Enhanced refresh: analyzing {len(symbols)} stocks...")
        
        signals = await enhanced_investment_engine.batch_analyze(symbols, batch_size=10)
        
        # Store in MongoDB
        for signal in signals:
            await db.investment_signals.update_one(
                {"symbol": signal.symbol},
                {"$set": convert_to_legacy_format(signal)},
                upsert=True
            )
        
        logger.info(f"Stored {len(signals)} enhanced investment signals")
        return len(signals)
    
    background_tasks.add_task(refresh_with_enhanced_engine, limit)
    return {"message": f"Refreshing signals for up to {limit} stocks with enhanced engine", "status": "processing"}

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

# Investments (Enhanced)
@api_router.get("/investments/scan")
async def scan_investments(auth: bool = Depends(verify_access)):
    """Scan market for investment opportunities with dynamic thresholds"""
    # Check if we have cached signals
    total = await db.investment_signals.count_documents({})
    
    if total > 50:
        # Use cached data
        cursor = db.investment_signals.find({}, {"_id": 0}).sort("overall_score", -1).limit(300)
        all_signals = await cursor.to_list(length=300)
        
        # Apply dynamic percentile-based categorization
        for i, s in enumerate(all_signals):
            percentile = ((len(all_signals) - i) / len(all_signals)) * 100
            score = s.get("overall_score", 0)
            
            # Dynamic categorization
            if percentile >= 90 and score >= 60:
                s["category"] = "Hot"
                s["signal"] = "Buy"
            elif percentile >= 75 and score >= 55:
                s["category"] = "Bullish"
                s["signal"] = "Buy"
            # Keep existing category for others
        
        signals = all_signals
    else:
        # Analyze on demand
        universe = universe_manager.CORE_UNIVERSE[:100]
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
    
    # Categorize results
    hot = [s for s in signals if s.get("category") == "Hot"]
    bullish = [s for s in signals if s.get("category") == "Bullish"]
    undervalued = [s for s in signals if s.get("category") == "Undervalued"]
    bearish = [s for s in signals if s.get("category") == "Bearish"]
    overpriced = [s for s in signals if s.get("category") == "Overpriced"]
    watch = [s for s in signals if s.get("category") == "Watch"]
    
    return {
        "hot": sorted(hot, key=lambda x: x.get("overall_score", 0), reverse=True)[:15],
        "bullish": sorted(bullish, key=lambda x: x.get("overall_score", 0), reverse=True)[:15],
        "undervalued": sorted(undervalued, key=lambda x: x.get("overall_score", 0), reverse=True)[:15],
        "watch": sorted(watch, key=lambda x: x.get("overall_score", 0), reverse=True)[:15],
        "bearish": bearish[:15],
        "overpriced": overpriced[:15],
        "avoid": [s for s in signals if s.get("signal") == "Sell"][:15],
        "all": sorted(signals, key=lambda x: x.get("overall_score", 0), reverse=True),
        "total_analyzed": len(signals)
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
    return {"name": "ObaidTradez API", "version": "2.0.0", "status": "running"}

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
    """Initialize the investment universe on startup"""
    try:
        # Check if we have any cached signals
        count = await db.investment_signals.count_documents({})
        if count == 0:
            logger.info("No cached signals found, starting initial load...")
            # Start with a quick initial load of top stocks
            asyncio.create_task(investment_engine.refresh_universe_signals(200))
    except Exception as e:
        logger.error(f"Startup error: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
