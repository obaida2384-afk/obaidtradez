"""
Price Integrity Service for ObaidTradez
Single source of truth for all price data.
Validates freshness, rejects stale data, normalizes tickers.
"""
import asyncio
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# Max age of a valid trade (in days). Beyond this, ticker is considered dead/stale
MAX_TRADE_AGE_DAYS = 5
# Max age of a valid snapshot for trading decisions (in seconds)
MAX_PRICE_AGE_SECONDS = 300  # 5 minutes during market hours


class PriceRecord:
    """Validated, timestamped price with source tracking."""
    __slots__ = (
        "symbol", "price", "bid", "ask", "mid", "spread", "spread_pct",
        "source", "trade_timestamp", "fetch_timestamp",
        "stale", "dead_ticker", "age_seconds", "volume",
    )

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.price: float = 0
        self.bid: float = 0
        self.ask: float = 0
        self.mid: float = 0
        self.spread: float = 0
        self.spread_pct: float = 0
        self.source: str = "none"
        self.trade_timestamp: Optional[str] = None
        self.fetch_timestamp: float = 0
        self.stale: bool = True
        self.dead_ticker: bool = False
        self.age_seconds: float = 0
        self.volume: int = 0

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "bid": self.bid,
            "ask": self.ask,
            "mid": self.mid,
            "spread": self.spread,
            "spread_pct": self.spread_pct,
            "source": self.source,
            "trade_timestamp": self.trade_timestamp,
            "fetch_timestamp": datetime.fromtimestamp(self.fetch_timestamp, tz=timezone.utc).isoformat() if self.fetch_timestamp > 0 else None,
            "stale": self.stale,
            "dead_ticker": self.dead_ticker,
            "age_seconds": round(self.age_seconds, 1),
        }


class PriceIntegrityService:
    """
    Centralized price validation and distribution.
    All price consumers (UI, trading logic, sync) MUST use this service.
    """

    def __init__(self):
        self._api_key = os.environ.get("ALPACA_API_KEY", "")
        self._secret_key = os.environ.get("ALPACA_SECRET_KEY", "")
        self._fmp_key = os.environ.get("FMP_API_KEY", "")
        self._alpaca_rest = "https://data.alpaca.markets/v2"
        self._fmp_rest = "https://financialmodelingprep.com/api/v3"
        self._cache: Dict[str, PriceRecord] = {}
        self._cache_ttl = 30  # seconds
        self._dead_tickers: set = set()
        self._ticker_map: Dict[str, str] = {}  # old_ticker -> new_ticker
        self._stats = {
            "fetches": 0,
            "cache_hits": 0,
            "stale_rejected": 0,
            "dead_rejected": 0,
            "fmp_fallbacks": 0,
        }

    def get_canonical_symbol(self, symbol: str) -> str:
        """Resolve ticker renames/mappings."""
        return self._ticker_map.get(symbol.upper(), symbol.upper())

    def is_dead_ticker(self, symbol: str) -> bool:
        return symbol.upper() in self._dead_tickers

    def mark_dead(self, symbol: str):
        self._dead_tickers.add(symbol.upper())

    def add_ticker_mapping(self, old: str, new: str):
        self._ticker_map[old.upper()] = new.upper()

    async def get_validated_price(self, symbol: str) -> PriceRecord:
        """
        Get a validated, timestamped price for a symbol.
        Priority: cache (if fresh) -> Alpaca snapshot (with freshness check) -> FMP quote
        """
        symbol = symbol.upper()
        canonical = self.get_canonical_symbol(symbol)

        # Check dead ticker
        if canonical in self._dead_tickers:
            rec = PriceRecord(symbol)
            rec.dead_ticker = True
            rec.source = "dead_ticker"
            self._stats["dead_rejected"] += 1
            return rec

        # Check cache
        cached = self._cache.get(canonical)
        if cached and (time.time() - cached.fetch_timestamp) < self._cache_ttl and not cached.stale:
            self._stats["cache_hits"] += 1
            return cached

        # Fetch from Alpaca
        rec = await self._fetch_alpaca_snapshot(canonical)
        self._stats["fetches"] += 1

        # If Alpaca returns stale data, try FMP
        if rec.dead_ticker or rec.stale:
            fmp_rec = await self._fetch_fmp_quote(canonical)
            if fmp_rec and fmp_rec.price > 0 and not fmp_rec.stale:
                self._stats["fmp_fallbacks"] += 1
                rec = fmp_rec
            elif rec.dead_ticker:
                self._dead_tickers.add(canonical)
                self._stats["dead_rejected"] += 1

        self._cache[canonical] = rec
        return rec

    async def get_batch_validated(self, symbols: List[str]) -> Dict[str, PriceRecord]:
        """Batch-fetch validated prices for multiple symbols."""
        results = {}
        to_fetch = []

        for sym in symbols:
            sym = sym.upper()
            canonical = self.get_canonical_symbol(sym)

            if canonical in self._dead_tickers:
                rec = PriceRecord(sym)
                rec.dead_ticker = True
                rec.source = "dead_ticker"
                results[sym] = rec
                continue

            cached = self._cache.get(canonical)
            if cached and (time.time() - cached.fetch_timestamp) < self._cache_ttl and not cached.stale:
                results[sym] = cached
                self._stats["cache_hits"] += 1
            else:
                to_fetch.append((sym, canonical))

        # Batch fetch from Alpaca
        if to_fetch:
            canonicals = list(set(c for _, c in to_fetch))
            alpaca_results = await self._batch_alpaca_snapshots(canonicals)

            # Map results back
            for orig_sym, canonical in to_fetch:
                rec = alpaca_results.get(canonical)
                if not rec:
                    rec = PriceRecord(orig_sym)
                    rec.stale = True
                    rec.source = "not_found"

                if rec.dead_ticker:
                    self._dead_tickers.add(canonical)

                self._cache[canonical] = rec
                results[orig_sym] = rec

        return results

    async def _fetch_alpaca_snapshot(self, symbol: str) -> PriceRecord:
        """Fetch single snapshot from Alpaca with freshness validation."""
        rec = PriceRecord(symbol)
        try:
            headers = {
                "APCA-API-KEY-ID": self._api_key,
                "APCA-API-SECRET-KEY": self._secret_key,
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._alpaca_rest}/stocks/snapshots",
                    params={"symbols": symbol},
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if symbol not in data:
                        rec.source = "not_found"
                        return rec
                    self._parse_alpaca_snapshot(rec, data[symbol])
        except Exception as e:
            logger.warning(f"Alpaca snapshot error for {symbol}: {e}")
            rec.source = "error"
        return rec

    async def _batch_alpaca_snapshots(self, symbols: List[str]) -> Dict[str, PriceRecord]:
        """Batch fetch from Alpaca with freshness validation."""
        results = {}
        headers = {
            "APCA-API-KEY-ID": self._api_key,
            "APCA-API-SECRET-KEY": self._secret_key,
        }

        batch_size = 50
        async with httpx.AsyncClient(timeout=15) as client:
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                try:
                    resp = await client.get(
                        f"{self._alpaca_rest}/stocks/snapshots",
                        params={"symbols": ",".join(batch)},
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for sym in batch:
                            rec = PriceRecord(sym)
                            if sym in data:
                                self._parse_alpaca_snapshot(rec, data[sym])
                            else:
                                rec.source = "not_found"
                                rec.dead_ticker = True
                            results[sym] = rec
                except Exception as e:
                    logger.warning(f"Batch snapshot error: {e}")
                    for sym in batch:
                        rec = PriceRecord(sym)
                        rec.source = "error"
                        results[sym] = rec
                if i + batch_size < len(symbols):
                    await asyncio.sleep(0.2)

        return results

    def _parse_alpaca_snapshot(self, rec: PriceRecord, snap: Dict):
        """Parse Alpaca snapshot and validate freshness."""
        trade = snap.get("latestTrade", {})
        quote = snap.get("latestQuote", {})

        trade_price = trade.get("p", 0)
        trade_time_str = trade.get("t", "")
        bid = quote.get("bp", 0)
        ask = quote.get("ap", 0)

        rec.price = trade_price
        rec.trade_timestamp = trade_time_str
        rec.fetch_timestamp = time.time()
        rec.source = "alpaca"

        # Validate trade freshness
        if trade_time_str:
            try:
                trade_time = datetime.fromisoformat(trade_time_str.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                age = now - trade_time
                rec.age_seconds = age.total_seconds()

                if age.days > MAX_TRADE_AGE_DAYS:
                    rec.stale = True
                    rec.dead_ticker = True
                    rec.source = f"dead_ticker(last_trade={trade_time.strftime('%Y-%m-%d')})"
                    logger.debug(f"{rec.symbol}: dead ticker, last trade {age.days} days ago")
                    return
                else:
                    rec.stale = False
            except (ValueError, TypeError):
                rec.stale = True
                return

        # Parse bid/ask
        if bid > 0 and ask > 0 and ask >= bid:
            spread = ask - bid
            if bid > 0 and (spread / bid) <= 0.10:
                rec.bid = bid
                rec.ask = ask
                rec.mid = round((bid + ask) / 2, 4)
                rec.spread = round(spread, 4)
                rec.spread_pct = round((spread / rec.mid) * 100, 4) if rec.mid > 0 else 0

    async def _fetch_fmp_quote(self, symbol: str) -> Optional[PriceRecord]:
        """Fallback: fetch from FMP for symbols Alpaca doesn't recognize."""
        if not self._fmp_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._fmp_rest}/quote/{symbol}",
                    params={"apikey": self._fmp_key},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data and len(data) > 0:
                        q = data[0]
                        rec = PriceRecord(symbol)
                        rec.price = q.get("price", 0)
                        rec.volume = q.get("volume", 0)
                        rec.fetch_timestamp = time.time()
                        rec.source = "fmp"

                        # FMP doesn't give trade timestamp directly,
                        # but if volume > 0 and price > 0, it's likely active
                        if rec.price > 0 and rec.volume > 0:
                            rec.stale = False
                        else:
                            rec.stale = True
                        return rec
        except Exception as e:
            logger.warning(f"FMP quote error for {symbol}: {e}")
        return None

    async def audit_universe(self, symbols: List[str]) -> Dict:
        """Full universe audit: identify dead, stale, and healthy tickers."""
        results = await self.get_batch_validated(symbols)

        dead = []
        stale = []
        healthy = []

        for sym, rec in results.items():
            entry = {
                "symbol": sym,
                "price": rec.price,
                "source": rec.source,
                "trade_timestamp": rec.trade_timestamp,
                "age_seconds": round(rec.age_seconds, 1),
                "stale": rec.stale,
                "dead_ticker": rec.dead_ticker,
                "bid": rec.bid,
                "ask": rec.ask,
            }
            if rec.dead_ticker:
                dead.append(entry)
            elif rec.stale:
                stale.append(entry)
            else:
                healthy.append(entry)

        return {
            "total": len(results),
            "healthy": len(healthy),
            "stale": len(stale),
            "dead": len(dead),
            "dead_tickers": sorted(dead, key=lambda x: x["symbol"]),
            "stale_tickers": sorted(stale, key=lambda x: x["symbol"]),
            "stats": self._stats,
        }

    async def sync_signal_prices(self, db) -> Dict:
        """
        Sync all cached signal prices with validated live data.
        Rejects stale/dead prices. Flags dead tickers in DB.
        """
        # Collect all symbols
        ts_cursor = db.trading_signals.find({}, {"_id": 0, "symbol": 1})
        is_cursor = db.investment_signals.find({}, {"_id": 0, "symbol": 1})
        ts_docs = await ts_cursor.to_list(length=2000)
        is_docs = await is_cursor.to_list(length=2000)
        all_symbols = list(set(
            [d["symbol"] for d in ts_docs if d.get("symbol")] +
            [d["symbol"] for d in is_docs if d.get("symbol")]
        ))

        if not all_symbols:
            return {"updated": 0, "dead_flagged": 0, "rejected": 0}

        # Batch validate
        validated = await self.get_batch_validated(all_symbols)

        updated = 0
        dead_flagged = 0
        stale_rejected = 0
        now_iso = datetime.now(timezone.utc).isoformat()

        for sym, rec in validated.items():
            if rec.dead_ticker:
                # Flag dead tickers in DB instead of syncing bad price
                await db.trading_signals.update_one(
                    {"symbol": sym},
                    {"$set": {
                        "dead_ticker": True,
                        "price_status": "dead",
                        "price_synced_at": now_iso,
                        "price_source": rec.source,
                    }}
                )
                await db.investment_signals.update_one(
                    {"symbol": sym},
                    {"$set": {
                        "dead_ticker": True,
                        "price_status": "dead",
                        "price_synced_at": now_iso,
                        "price_source": rec.source,
                    }}
                )
                dead_flagged += 1
                continue

            if rec.stale or rec.price <= 0:
                stale_rejected += 1
                self._stats["stale_rejected"] += 1
                continue

            # Valid price — update DB
            update_fields = {
                "price": rec.price,
                "price_synced_at": now_iso,
                "price_source": rec.source,
                "price_trade_ts": rec.trade_timestamp,
                "dead_ticker": False,
                "price_status": "live",
            }
            if rec.bid > 0:
                update_fields["live_bid"] = rec.bid
            if rec.ask > 0:
                update_fields["live_ask"] = rec.ask

            result = await db.trading_signals.update_one(
                {"symbol": sym},
                {"$set": update_fields}
            )
            if result.modified_count:
                updated += 1

            inv_fields = {**update_fields, "current_price": rec.price}
            await db.investment_signals.update_one(
                {"symbol": sym},
                {"$set": inv_fields}
            )

        logger.info(f"Price sync: {updated} updated, {dead_flagged} dead flagged, {stale_rejected} stale rejected (of {len(all_symbols)} total)")
        return {
            "updated": updated,
            "dead_flagged": dead_flagged,
            "rejected": stale_rejected,
            "total": len(all_symbols),
        }

    def get_stats(self) -> Dict:
        return {
            **self._stats,
            "dead_tickers_count": len(self._dead_tickers),
            "cached_prices": len(self._cache),
            "ticker_mappings": len(self._ticker_map),
        }
