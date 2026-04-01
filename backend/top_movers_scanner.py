"""
Top Movers Scanner — Fetches daily top gainers/losers from FMP API.
Pre-populates the trading universe with actively moving stocks.
Refreshes every 15-30 min during regular market hours.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
import httpx

logger = logging.getLogger(__name__)

# Dead tickers / risky names to always exclude
EXCLUDED_SYMBOLS = set()
try:
    from server import PaperExecutionEngine
    EXCLUDED_SYMBOLS = EXCLUDED_SYMBOLS | PaperExecutionEngine.RISKY_STOCKS
except (ImportError, AttributeError):
    pass


class TopMoversScanner:
    """Scans FMP for top gainers/losers and pre-filters for the momentum engine."""

    # Limits
    MAX_GAINERS = 30
    MAX_LOSERS = 30
    MAX_ACTIVES = 20
    REFRESH_INTERVAL_MINUTES = 20  # Refresh every 20 min during market hours
    CACHE_TTL_SECONDS = 1200  # 20 minutes

    # Quality filters
    MIN_PRICE = 5.0
    MAX_PRICE = 50.0
    MIN_VOLUME = 500_000
    MIN_CHANGE_PCT = 2.0  # Must have moved at least 2% to be interesting
    MAX_SPREAD_PCT = 0.5
    MIN_MARKET_CAP = 100_000_000  # $100M minimum to avoid low-float trash

    def __init__(self, db, fmp_api_key: str):
        self.db = db
        self.fmp_api_key = fmp_api_key
        self.fmp_base = "https://financialmodelingprep.com/api/v3"
        self.fmp_stable = "https://financialmodelingprep.com/stable"
        self._cache: Dict = {}
        self._cache_time: Optional[datetime] = None
        self._scan_history: List[Dict] = []
        self._last_refresh: Optional[datetime] = None

    async def _fmp_request(self, url: str, params: Dict = None) -> Optional[List]:
        """Make FMP API request with apikey as query param."""
        try:
            full_params = {"apikey": self.fmp_api_key}
            if params:
                full_params.update(params)
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=full_params)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        return data
                    return []
                logger.warning(f"FMP top movers API error {resp.status_code}: {url}")
        except Exception as e:
            logger.error(f"FMP top movers request error: {e}")
        return []

    async def _fmp_request_stable(self, endpoint: str, params: Dict = None) -> Optional[List]:
        """Use stable API with apikey as header (matches existing codebase pattern)."""
        try:
            headers = {"apikey": self.fmp_api_key}
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.fmp_stable}/{endpoint}",
                    headers=headers,
                    params=params or {}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data if isinstance(data, list) else []
                # Fallback to v3 if stable doesn't support this endpoint
                logger.info(f"Stable API {resp.status_code} for {endpoint}, trying v3")
        except Exception as e:
            logger.info(f"Stable API error for {endpoint}: {e}, trying v3")
        return None  # Signal to try v3

    async def fetch_top_gainers(self) -> List[Dict]:
        """Fetch top gaining stocks. Uses FMP if available, falls back to DB signals."""
        # Try FMP first
        data = await self._fmp_request_stable("stock_market/gainers")
        if data and len(data) > 0:
            return data
        data = await self._fmp_request(f"{self.fmp_base}/stock_market/gainers")
        if data and len(data) > 0:
            return data
        # Fallback: compute from existing trading signals in DB
        return await self._compute_movers_from_db("gainers")

    async def fetch_top_losers(self) -> List[Dict]:
        """Fetch top losing stocks."""
        data = await self._fmp_request_stable("stock_market/losers")
        if data and len(data) > 0:
            return data
        data = await self._fmp_request(f"{self.fmp_base}/stock_market/losers")
        if data and len(data) > 0:
            return data
        return await self._compute_movers_from_db("losers")

    async def fetch_most_active(self) -> List[Dict]:
        """Fetch most actively traded stocks."""
        data = await self._fmp_request_stable("stock_market/actives")
        if data and len(data) > 0:
            return data
        data = await self._fmp_request(f"{self.fmp_base}/stock_market/actives")
        if data and len(data) > 0:
            return data
        return await self._compute_movers_from_db("actives")

    async def _compute_movers_from_db(self, mode: str) -> List[Dict]:
        """Compute top movers from existing trading signals in MongoDB.
        Uses Alpaca-synced price data that's already in the DB."""
        try:
            signals = await self.db.trading_signals.find(
                {"dead_ticker": {"$ne": True}, "price": {"$gt": 0}},
                {"_id": 0, "symbol": 1, "price": 1, "name": 1, "company_name": 1,
                 "indicators": 1, "change_pct": 1, "changesPercentage": 1,
                 "daily_change_pct": 1, "volume": 1, "marketCap": 1, "market_cap": 1}
            ).to_list(2000)

            enriched = []
            for sig in signals:
                symbol = sig.get("symbol", "")
                price = sig.get("price", 0) or 0
                indicators = sig.get("indicators", {})

                # Get change percentage from multiple possible fields
                change_pct = (
                    sig.get("daily_change_pct") or
                    sig.get("changesPercentage") or
                    sig.get("change_pct") or
                    indicators.get("daily_change_pct") or
                    indicators.get("change_pct", 0)
                )
                if change_pct is None:
                    change_pct = 0
                change_pct = float(change_pct)

                volume = indicators.get("volume", 0) or sig.get("volume", 0) or 0
                market_cap = sig.get("marketCap", sig.get("market_cap", 0)) or 0

                if price <= 0 or not symbol:
                    continue

                enriched.append({
                    "symbol": symbol,
                    "price": price,
                    "changesPercentage": change_pct,
                    "volume": volume,
                    "marketCap": market_cap,
                    "name": sig.get("name", sig.get("company_name", "")),
                })

            if mode == "gainers":
                enriched.sort(key=lambda x: x["changesPercentage"], reverse=True)
                return [s for s in enriched if s["changesPercentage"] > 0][:50]
            elif mode == "losers":
                enriched.sort(key=lambda x: x["changesPercentage"])
                return [s for s in enriched if s["changesPercentage"] < 0][:50]
            else:  # actives
                enriched.sort(key=lambda x: x["volume"], reverse=True)
                return enriched[:50]

        except Exception as e:
            logger.error(f"Failed to compute movers from DB: {e}")
            return []

    def _apply_quality_filters(self, stock: Dict) -> Tuple[bool, List[str]]:
        """Apply quality filters to a single mover. Returns (passed, reject_reasons)."""
        symbol = stock.get("symbol", "")
        price = stock.get("price", 0) or 0
        volume = stock.get("volume", 0) or 0
        change_pct = abs(stock.get("changesPercentage", stock.get("changePercent", 0)) or 0)
        market_cap = stock.get("marketCap", 0) or 0

        reject_reasons = []

        # Symbol exclusions
        if symbol in EXCLUDED_SYMBOLS:
            reject_reasons.append("Excluded: dead/risky ticker")
            return False, reject_reasons

        # No warrants, units, preferred shares
        if any(c in symbol for c in ['.', '-', 'W', 'U']) and len(symbol) > 4:
            reject_reasons.append(f"Non-common equity: {symbol}")
            return False, reject_reasons

        # Price filter: $5-$50
        if price < self.MIN_PRICE:
            reject_reasons.append(f"Price ${price:.2f} < ${self.MIN_PRICE}")
            return False, reject_reasons
        if price > self.MAX_PRICE:
            reject_reasons.append(f"Price ${price:.2f} > ${self.MAX_PRICE}")
            return False, reject_reasons

        # Volume filter
        if volume > 0 and volume < self.MIN_VOLUME:
            reject_reasons.append(f"Volume {volume:,} < {self.MIN_VOLUME:,}")
            return False, reject_reasons

        # Minimum move %
        if change_pct < self.MIN_CHANGE_PCT:
            reject_reasons.append(f"Change {change_pct:.1f}% < {self.MIN_CHANGE_PCT}% minimum")
            return False, reject_reasons

        # Market cap (avoid extreme low-float names)
        if market_cap > 0 and market_cap < self.MIN_MARKET_CAP:
            reject_reasons.append(f"Market cap ${market_cap/1e6:.0f}M < ${self.MIN_MARKET_CAP/1e6:.0f}M minimum")
            return False, reject_reasons

        return True, []

    async def scan(self, force: bool = False) -> Dict:
        """Full scan: fetch movers, filter, and return enriched universe.
        Returns a dict with accepted symbols, rejection pipeline, and metadata."""

        # Check cache
        if not force and self._cache_time:
            age = (datetime.now(timezone.utc) - self._cache_time).total_seconds()
            if age < self.CACHE_TTL_SECONDS and self._cache:
                return self._cache

        scan_start = datetime.now(timezone.utc)
        logger.info("Top Movers Scanner: Starting scan...")

        # Fetch all three lists in parallel
        gainers_raw, losers_raw, actives_raw = await asyncio.gather(
            self.fetch_top_gainers(),
            self.fetch_top_losers(),
            self.fetch_most_active(),
        )

        # Track pipeline stats
        pipeline = {
            "raw_gainers": len(gainers_raw),
            "raw_losers": len(losers_raw),
            "raw_actives": len(actives_raw),
            "filtered_gainers": 0,
            "filtered_losers": 0,
            "filtered_actives": 0,
            "total_accepted": 0,
            "total_rejected": 0,
            "rejections_by_reason": {},
        }

        accepted = {}  # symbol -> enriched data
        rejected = []  # list of rejected with reasons

        def process_list(stocks: List[Dict], source: str, cap: int):
            count = 0
            for stock in stocks:
                if count >= cap:
                    break
                symbol = stock.get("symbol", "")
                if not symbol or symbol in accepted:
                    continue

                passed, reasons = self._apply_quality_filters(stock)
                if passed:
                    accepted[symbol] = {
                        "symbol": symbol,
                        "source": source,
                        "price": stock.get("price", 0),
                        "change_pct": stock.get("changesPercentage", stock.get("changePercent", 0)),
                        "volume": stock.get("volume", 0),
                        "market_cap": stock.get("marketCap", 0),
                        "name": stock.get("name", stock.get("companyName", "")),
                    }
                    count += 1
                else:
                    rejected.append({
                        "symbol": symbol,
                        "source": source,
                        "price": stock.get("price", 0),
                        "change_pct": stock.get("changesPercentage", stock.get("changePercent", 0)),
                        "volume": stock.get("volume", 0),
                        "reject_reasons": reasons,
                    })
                    for r in reasons:
                        # Group by reason category, not specific value
                        if "Price" in r and ">" in r:
                            key = f"Price > ${self.MAX_PRICE}"
                        elif "Price" in r and "<" in r:
                            key = f"Price < ${self.MIN_PRICE}"
                        elif "Volume" in r:
                            key = "Volume too low"
                        elif "Change" in r:
                            key = f"Change < {self.MIN_CHANGE_PCT}%"
                        elif "Market cap" in r:
                            key = f"Market cap < ${self.MIN_MARKET_CAP/1e6:.0f}M"
                        elif "Excluded" in r:
                            key = "Excluded (risky/dead)"
                        elif "Non-common" in r:
                            key = "Non-common equity"
                        else:
                            key = r.split(":")[0].strip()
                        pipeline["rejections_by_reason"][key] = pipeline["rejections_by_reason"].get(key, 0) + 1

        # Process gainers first, then losers, then actives (deduplicated)
        process_list(gainers_raw, "top_gainer", self.MAX_GAINERS)
        pipeline["filtered_gainers"] = len([v for v in accepted.values() if v["source"] == "top_gainer"])

        process_list(losers_raw, "top_loser", self.MAX_LOSERS)
        pipeline["filtered_losers"] = len([v for v in accepted.values() if v["source"] == "top_loser"])

        process_list(actives_raw, "most_active", self.MAX_ACTIVES)
        pipeline["filtered_actives"] = len([v for v in accepted.values() if v["source"] == "most_active"])

        pipeline["total_accepted"] = len(accepted)
        pipeline["total_rejected"] = len(rejected)

        scan_duration = (datetime.now(timezone.utc) - scan_start).total_seconds()

        result = {
            "timestamp": scan_start.isoformat(),
            "duration_seconds": round(scan_duration, 2),
            "accepted": list(accepted.values()),
            "accepted_symbols": list(accepted.keys()),
            "rejected": rejected[:30],  # Cap rejected list for UI
            "pipeline": pipeline,
            "config": {
                "max_gainers": self.MAX_GAINERS,
                "max_losers": self.MAX_LOSERS,
                "max_actives": self.MAX_ACTIVES,
                "price_range": f"${self.MIN_PRICE}-${self.MAX_PRICE}",
                "min_volume": f"{self.MIN_VOLUME:,}",
                "min_change_pct": f"{self.MIN_CHANGE_PCT}%",
                "min_market_cap": f"${self.MIN_MARKET_CAP/1e6:.0f}M",
                "refresh_interval_minutes": self.REFRESH_INTERVAL_MINUTES,
            },
        }

        # Cache
        self._cache = result
        self._cache_time = scan_start
        self._last_refresh = scan_start

        # Store in MongoDB for analysis
        scan_record = {
            "timestamp": scan_start.isoformat(),
            "pipeline": pipeline,
            "accepted_count": len(accepted),
            "accepted_symbols": list(accepted.keys()),
            "rejected_count": len(rejected),
            "duration_seconds": round(scan_duration, 2),
        }
        self._scan_history.append(scan_record)
        try:
            await self.db.top_movers_scans.insert_one({
                **scan_record,
                "accepted": list(accepted.values()),
                "rejected": rejected[:50],
                "_id": f"scan_{scan_start.strftime('%Y%m%d_%H%M%S')}",
            })
        except Exception as e:
            logger.warning(f"Failed to persist top movers scan: {e}")

        logger.info(
            f"Top Movers Scanner: {pipeline['total_accepted']} accepted "
            f"({pipeline['filtered_gainers']}G + {pipeline['filtered_losers']}L + {pipeline['filtered_actives']}A) "
            f"| {pipeline['total_rejected']} rejected | {scan_duration:.1f}s"
        )

        return result

    def get_accepted_symbols(self) -> List[str]:
        """Return just the accepted symbols from the last scan (for universe injection)."""
        if self._cache:
            return self._cache.get("accepted_symbols", [])
        return []

    def get_symbol_source(self, symbol: str) -> Optional[str]:
        """Return the source tag for a symbol (top_gainer, top_loser, most_active)."""
        if not self._cache:
            return None
        for item in self._cache.get("accepted", []):
            if item["symbol"] == symbol:
                return item["source"]
        return None

    def should_refresh(self) -> bool:
        """Check if the scanner needs a refresh."""
        if not self._last_refresh:
            return True
        age_min = (datetime.now(timezone.utc) - self._last_refresh).total_seconds() / 60
        return age_min >= self.REFRESH_INTERVAL_MINUTES

    def get_scan_history(self, limit: int = 10) -> List[Dict]:
        """Return recent scan history for analytics."""
        return self._scan_history[-limit:]

    async def get_performance_summary(self) -> Dict:
        """Get performance summary from MongoDB for the current day."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        scans = await self.db.top_movers_scans.find(
            {"timestamp": {"$regex": f"^{today}"}},
            {"_id": 0}
        ).sort("timestamp", -1).to_list(50)

        if not scans:
            return {"date": today, "total_scans": 0, "message": "No scans today"}

        all_accepted = set()
        all_rejected_symbols = set()
        total_rejections_by_reason = {}
        
        for scan in scans:
            all_accepted.update(scan.get("accepted_symbols", []))
            for rej in scan.get("rejected", []):
                all_rejected_symbols.add(rej.get("symbol", ""))
                for r in rej.get("reject_reasons", []):
                    key = r.split(":")[0].strip()
                    total_rejections_by_reason[key] = total_rejections_by_reason.get(key, 0) + 1

        return {
            "date": today,
            "total_scans": len(scans),
            "unique_accepted_symbols": len(all_accepted),
            "accepted_symbols_list": sorted(all_accepted),
            "unique_rejected_symbols": len(all_rejected_symbols),
            "top_rejection_reasons": dict(sorted(
                total_rejections_by_reason.items(),
                key=lambda x: x[1], reverse=True
            )[:10]),
            "last_scan": scans[0] if scans else None,
        }
