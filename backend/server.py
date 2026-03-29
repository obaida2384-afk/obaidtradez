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
    # Store base URL without /v2, add it in API calls
    _raw_base_url = os.environ.get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets/v2')
    ALPACA_BASE_URL = _raw_base_url.rstrip('/').replace('/v2', '')

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
        "TILE", "BECN", "PGTI", "GMS", "PATK", "JELD", "UFPI", "LGIH", "CVCO", "SKY"
    ]
    
    # ETFs for sector exposure
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
        "SKYY", "CLOU", "WCLD", "IGV", "CIBR", "HACK", "FINX", "IPAY", "BOTZ", "ROBO"
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
                category=category
            )
            
            analysis["included"] = True
            analysis["signal"] = signal
            return analysis
            
        except Exception as e:
            logger.error(f"Trading analysis error for {symbol}: {e}")
            analysis["exclusion_reason"] = f"Analysis error: {str(e)}"
            return analysis
    
    async def scan_trading_opportunities(self) -> Dict:
        """
        Scan market for HIGH-QUALITY trading opportunities.
        Returns only top 5-15 signals with full diagnostics.
        """
        # Expanded universe for better selection
        universe = [
            # Mega caps
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
            # High-beta tech
            "AMD", "NFLX", "CRM", "SHOP", "SQ", "COIN", "PLTR", "SNOW",
            # Volatile movers
            "ROKU", "SNAP", "UBER", "ABNB", "RIVN", "LCID", "NIO",
            # Momentum names
            "MARA", "RIOT", "HOOD", "SOFI", "AFRM", "UPST",
            # Sector leaders
            "XOM", "CVX", "JPM", "GS", "BA", "CAT", "DE"
        ]
        
        # Analyze all stocks
        analyses = await asyncio.gather(*[self.analyze_for_trading(s) for s in universe])
        
        # Separate included vs excluded
        included = []
        excluded = []
        
        for analysis in analyses:
            if analysis and analysis.get("included") and analysis.get("signal"):
                included.append(analysis["signal"])
            elif analysis:
                excluded.append({
                    "symbol": analysis.get("symbol"),
                    "reason": analysis.get("exclusion_reason", "Unknown")
                })
        
        # Sort by quality (confidence * has structure bonus)
        def quality_score(s):
            base = s.confidence
            if s.indicators.get("structure_type"):
                base += 0.1
            if s.indicators.get("volume_ratio", 0) >= 1.5:
                base += 0.05
            return base
        
        included.sort(key=quality_score, reverse=True)
        
        # Limit to top 15 signals max
        all_signals = included[:15]
        
        # Categorize
        hot = [s for s in all_signals if s.category == "Hot"][:5]
        breakout = [s for s in all_signals if s.category == "Breakout"][:5]
        momentum = [s for s in all_signals if s.category == "Momentum"][:5]
        high_volume = [s for s in all_signals if s.category == "High Volume"][:5]
        watch = [s for s in all_signals if s.category == "Watch"][:5]
        
        # Top Trades Today: Best 3-5 regardless of category
        top_trades = sorted(all_signals, key=quality_score, reverse=True)[:5]
        
        return {
            "top_trades": top_trades,
            "hot": hot,
            "breakout": breakout,
            "momentum": momentum,
            "high_volume": high_volume,
            "watch": watch,
            "all": all_signals,
            "diagnostics": {
                "stocks_scanned": len(universe),
                "signals_generated": len(all_signals),
                "excluded_count": len(excluded),
                "excluded_reasons": excluded[:10],  # Show first 10 exclusions
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
    """Simple backtesting engine using historical data"""
    
    PERIOD_DAYS = {
        "3m": 90,
        "6m": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825
    }
    
    async def get_historical_data(self, symbol: str, days: int) -> List[Dict]:
        """Get historical price data"""
        cache_key = f"historical_{symbol}_{days}"
        cached = get_cached(cache_key, 3600)  # 1 hour cache
        if cached:
            return cached
        
        try:
            # Try FMP first
            data = await api_client.fmp_historical(symbol)
            if data and len(data) > 0:
                # Limit to requested days
                data = data[:days] if len(data) > days else data
                data = list(reversed(data))  # Oldest first
                set_cached(cache_key, data)
                return data
        except Exception as e:
            logger.error(f"Historical data error for {symbol}: {e}")
        
        return []
    
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
        
        return {
            "symbol": request.symbol.upper(),
            "strategy": request.strategy,
            "period": request.period,
            "initial_capital": request.initial_capital,
            "final_value": round(final_value, 2),
            "total_return": round(total_return, 2),
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe, 2),
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "wins": wins,
            "losses": losses,
            "best_trade": round(best_trade, 2),
            "worst_trade": round(worst_trade, 2),
            "trades": trades[-10:],  # Last 10 trades
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

# Health check (no auth required)
@api_router.get("/")
async def root():
    return {"name": "ObaidTradez API", "version": "2.5.0", "status": "running"}

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
