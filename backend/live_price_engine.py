"""
Live Price Engine for ObaidTradez
Uses Alpaca WebSocket for real-time trades + quotes, with REST snapshot fallback.
Provides separated price types: display_price, last_trade, mid_price, bid, ask, spread.
Includes stale-data detection, graceful WS fallback, and signal re-evaluation triggers.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable

import httpx
import websockets

logger = logging.getLogger(__name__)

# Stale threshold in seconds — if no update for this long, mark stale
STALE_THRESHOLD_SECONDS = 60
# Minimum price change % to trigger re-evaluation
PRICE_CHANGE_THRESHOLD_PCT = 0.05
# Max consecutive WS auth/connection failures before switching to REST-only
MAX_WS_FAILURES = 3
# REST polling interval in seconds when in fallback mode
REST_POLL_INTERVAL = 10


class SymbolPriceState:
    """Holds all price data for a single symbol."""
    __slots__ = (
        "symbol", "last_trade_price", "last_trade_size", "last_trade_time",
        "bid", "bid_size", "ask", "ask_size", "quote_time",
        "display_price", "mid_price", "spread", "spread_pct",
        "buy_estimate", "sell_estimate",
        "last_update_ts", "source", "stale",
        "prev_display_price",
    )

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.last_trade_price: float = 0
        self.last_trade_size: int = 0
        self.last_trade_time: str = ""
        self.bid: float = 0
        self.bid_size: int = 0
        self.ask: float = 0
        self.ask_size: int = 0
        self.quote_time: str = ""
        self.display_price: float = 0
        self.mid_price: float = 0
        self.spread: float = 0
        self.spread_pct: float = 0
        self.buy_estimate: float = 0
        self.sell_estimate: float = 0
        self.last_update_ts: float = 0
        self.source: str = "none"
        self.stale: bool = True
        self.prev_display_price: float = 0

    def update_trade(self, price: float, size: int, timestamp: str):
        if price <= 0:
            return
        self.prev_display_price = self.display_price
        self.last_trade_price = price
        self.last_trade_size = size
        self.last_trade_time = timestamp
        self.display_price = price
        self.last_update_ts = time.time()
        self.source = "live"
        self.stale = False
        self._recalc()

    def update_quote(self, bid: float, bid_size: int, ask: float, ask_size: int, timestamp: str):
        if bid <= 0 or ask <= 0 or ask < bid:
            return
        if bid > 0 and ((ask - bid) / bid) > 0.10:
            return
        self.bid = bid
        self.bid_size = bid_size
        self.ask = ask
        self.ask_size = ask_size
        self.quote_time = timestamp
        self.mid_price = round((bid + ask) / 2, 4)
        self.spread = round(ask - bid, 4)
        self.spread_pct = round((self.spread / self.mid_price) * 100, 4) if self.mid_price > 0 else 0
        self.buy_estimate = ask
        self.sell_estimate = bid
        if self.display_price == 0:
            self.prev_display_price = self.display_price
            self.display_price = self.mid_price
        self.last_update_ts = time.time()
        self.source = "live"
        self.stale = False

    def update_from_snapshot(self, trade_price: float, bid: float, ask: float, timestamp: str = ""):
        if trade_price > 0:
            self.prev_display_price = self.display_price
            self.last_trade_price = trade_price
            self.display_price = trade_price
        if bid > 0 and ask > 0 and ask >= bid:
            if bid > 0 and ((ask - bid) / bid) <= 0.10:
                self.bid = bid
                self.ask = ask
                self.mid_price = round((bid + ask) / 2, 4)
                self.spread = round(ask - bid, 4)
                self.spread_pct = round((self.spread / self.mid_price) * 100, 4) if self.mid_price > 0 else 0
                self.buy_estimate = ask
                self.sell_estimate = bid
        self.last_update_ts = time.time()
        self.source = "snapshot"
        self.stale = False

    def check_stale(self):
        if self.last_update_ts > 0 and (time.time() - self.last_update_ts) > STALE_THRESHOLD_SECONDS:
            self.stale = True
            self.source = "stale"

    def price_changed_significantly(self) -> bool:
        if self.prev_display_price <= 0:
            return False
        change_pct = abs((self.display_price - self.prev_display_price) / self.prev_display_price) * 100
        return change_pct >= PRICE_CHANGE_THRESHOLD_PCT

    def _recalc(self):
        if self.bid > 0 and self.ask > 0:
            self.mid_price = round((self.bid + self.ask) / 2, 4)
            self.spread = round(self.ask - self.bid, 4)
            self.spread_pct = round((self.spread / self.mid_price) * 100, 4) if self.mid_price > 0 else 0
            self.buy_estimate = self.ask
            self.sell_estimate = self.bid

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "display_price": self.display_price,
            "last_trade_price": self.last_trade_price,
            "last_trade_size": self.last_trade_size,
            "last_trade_time": self.last_trade_time,
            "bid": self.bid,
            "bid_size": self.bid_size,
            "ask": self.ask,
            "ask_size": self.ask_size,
            "mid_price": self.mid_price,
            "spread": self.spread,
            "spread_pct": self.spread_pct,
            "buy_estimate": self.buy_estimate,
            "sell_estimate": self.sell_estimate,
            "last_update": datetime.fromtimestamp(self.last_update_ts, tz=timezone.utc).isoformat() if self.last_update_ts > 0 else None,
            "source": self.source,
            "stale": self.stale,
        }


class LivePriceEngine:
    """Manages WebSocket + REST fallback for live price streaming."""

    def __init__(self):
        self._api_key = os.environ.get("ALPACA_API_KEY", "")
        self._secret_key = os.environ.get("ALPACA_SECRET_KEY", "")
        self._ws_url = "wss://stream.data.alpaca.markets/v2/iex"
        self._rest_base = "https://data.alpaca.markets/v2"
        self._prices: Dict[str, SymbolPriceState] = {}
        self._tracked_symbols: set = set()
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._connected = False
        self._reconnect_count = 0
        self._ws_auth_failures = 0
        self._mode = "stopped"  # "websocket", "rest_fallback", "stopped"
        self._on_price_change: Optional[Callable] = None
        self._stale_check_task = None
        self._ws_task = None
        self._rest_poll_task = None
        self._stats = {
            "trades_received": 0,
            "quotes_received": 0,
            "reconnects": 0,
            "snapshots_fetched": 0,
            "reevals_triggered": 0,
            "ws_auth_failures": 0,
            "rest_polls": 0,
        }

    def set_reeval_callback(self, callback: Callable):
        self._on_price_change = callback

    def get_price(self, symbol: str) -> Optional[SymbolPriceState]:
        return self._prices.get(symbol)

    def get_all_prices(self) -> Dict[str, Dict]:
        return {s: p.to_dict() for s, p in self._prices.items()}

    def get_execution_price_data(self, symbol: str) -> Dict:
        p = self._prices.get(symbol)
        if not p:
            return {"source": "none", "stale": True}
        return {
            "live_price": p.display_price,
            "bid": p.bid,
            "ask": p.ask,
            "spread": p.spread,
            "spread_pct": p.spread_pct,
            "mid_price": p.mid_price,
            "buy_estimate": p.buy_estimate,
            "sell_estimate": p.sell_estimate,
            "source": p.source,
            "stale": p.stale,
            "last_update": datetime.fromtimestamp(p.last_update_ts, tz=timezone.utc).isoformat() if p.last_update_ts > 0 else None,
        }

    def is_stale(self, symbol: str) -> bool:
        p = self._prices.get(symbol)
        if not p:
            return True
        p.check_stale()
        return p.stale

    async def start(self, symbols: List[str]):
        """Start the live price engine with initial symbols."""
        # If already running, just update symbols
        if self._running:
            await self.update_symbols(symbols)
            return

        self._tracked_symbols = set(s.upper() for s in symbols)
        for s in self._tracked_symbols:
            if s not in self._prices:
                self._prices[s] = SymbolPriceState(s)

        self._running = True
        self._ws_auth_failures = 0

        # Fetch initial snapshots via REST
        await self._fetch_snapshots(list(self._tracked_symbols))

        # Start WebSocket — will auto-fallback to REST if connection limited
        self._ws_task = asyncio.create_task(self._ws_loop())
        self._stale_check_task = asyncio.create_task(self._stale_check_loop())
        self._mode = "websocket"
        logger.info(f"LivePriceEngine started: tracking {len(self._tracked_symbols)} symbols")

    async def stop(self):
        self._running = False
        self._mode = "stopped"
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        for task in [self._ws_task, self._stale_check_task, self._rest_poll_task]:
            if task:
                task.cancel()
        self._ws_task = None
        self._stale_check_task = None
        self._rest_poll_task = None
        self._connected = False
        logger.info("LivePriceEngine stopped")

    async def update_symbols(self, symbols: List[str]):
        new_symbols = set(s.upper() for s in symbols)
        added = new_symbols - self._tracked_symbols
        removed = self._tracked_symbols - new_symbols

        for s in added:
            if s not in self._prices:
                self._prices[s] = SymbolPriceState(s)

        self._tracked_symbols = new_symbols

        if self._ws and self._connected and (added or removed):
            try:
                if removed:
                    unsub = {"action": "unsubscribe", "trades": list(removed), "quotes": list(removed)}
                    await self._ws.send(json.dumps(unsub))
                if added:
                    sub = {"action": "subscribe", "trades": list(added), "quotes": list(added)}
                    await self._ws.send(json.dumps(sub))
                    await self._fetch_snapshots(list(added))
            except Exception as e:
                logger.error(f"Error updating WS subscriptions: {e}")

        # If in REST fallback mode, fetch snapshots for new symbols immediately
        if self._mode == "rest_fallback" and added:
            await self._fetch_snapshots(list(added))

    def _switch_to_rest_fallback(self):
        """Switch from WebSocket to REST-only polling mode."""
        if self._mode == "rest_fallback":
            return
        self._mode = "rest_fallback"
        self._connected = False
        logger.warning(f"Switching to REST-only fallback mode after {self._ws_auth_failures} WS auth failures")
        # Cancel WS task if running
        if self._ws_task:
            self._ws_task.cancel()
            self._ws_task = None
        # Start REST polling
        if not self._rest_poll_task or self._rest_poll_task.done():
            self._rest_poll_task = asyncio.create_task(self._rest_poll_loop())

    async def _ws_loop(self):
        """Main WebSocket connection loop with auto-reconnect and graceful fallback."""
        while self._running and self._mode == "websocket":
            try:
                async with websockets.connect(self._ws_url, ping_interval=20, ping_timeout=10, close_timeout=5) as ws:
                    self._ws = ws

                    # Wait for connected message
                    msg = await asyncio.wait_for(ws.recv(), 10)
                    data = json.loads(msg)
                    if not any(m.get("msg") == "connected" for m in data):
                        logger.error(f"WS unexpected connect msg: {msg}")
                        continue

                    # Authenticate
                    auth = {"action": "auth", "key": self._api_key, "secret": self._secret_key}
                    await ws.send(json.dumps(auth))
                    msg = await asyncio.wait_for(ws.recv(), 10)
                    data = json.loads(msg)

                    # Check for auth failure
                    auth_ok = any(m.get("msg") == "authenticated" for m in data)
                    if not auth_ok:
                        # Check if connection limit exceeded (code 406)
                        is_conn_limit = any(m.get("code") == 406 for m in data)
                        self._ws_auth_failures += 1
                        self._stats["ws_auth_failures"] = self._ws_auth_failures
                        logger.warning(f"WS auth failed (attempt {self._ws_auth_failures}/{MAX_WS_FAILURES}): {msg}")

                        if self._ws_auth_failures >= MAX_WS_FAILURES or is_conn_limit:
                            self._switch_to_rest_fallback()
                            return  # Exit WS loop
                        await asyncio.sleep(30)
                        continue

                    # Auth succeeded — reset failure counter
                    self._ws_auth_failures = 0
                    self._stats["ws_auth_failures"] = 0

                    # Subscribe
                    if self._tracked_symbols:
                        syms = list(self._tracked_symbols)
                        sub = {"action": "subscribe", "trades": syms, "quotes": syms}
                        await ws.send(json.dumps(sub))
                        await asyncio.wait_for(ws.recv(), 10)

                    self._connected = True
                    self._reconnect_count = 0
                    logger.info(f"WS connected and subscribed to {len(self._tracked_symbols)} symbols")

                    async for msg in ws:
                        if not self._running:
                            break
                        try:
                            events = json.loads(msg)
                            for event in events:
                                await self._handle_event(event)
                        except json.JSONDecodeError:
                            pass

            except (websockets.exceptions.ConnectionClosed, ConnectionError, asyncio.TimeoutError) as e:
                self._connected = False
                self._reconnect_count += 1
                self._stats["reconnects"] += 1

                if self._reconnect_count >= MAX_WS_FAILURES:
                    logger.warning(f"WS failed {self._reconnect_count} times, switching to REST fallback")
                    self._switch_to_rest_fallback()
                    return

                wait = min(30, 2 ** min(self._reconnect_count, 5))
                logger.warning(f"WS disconnected ({e}), reconnecting in {wait}s (attempt {self._reconnect_count})")
                await asyncio.sleep(wait)
                if self._tracked_symbols:
                    await self._fetch_snapshots(list(self._tracked_symbols))
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._connected = False
                logger.error(f"WS unexpected error: {e}")
                self._reconnect_count += 1
                if self._reconnect_count >= MAX_WS_FAILURES:
                    self._switch_to_rest_fallback()
                    return
                await asyncio.sleep(10)

    async def _rest_poll_loop(self):
        """Periodic REST snapshot polling as fallback when WebSocket is unavailable."""
        logger.info(f"REST poll loop started (interval={REST_POLL_INTERVAL}s)")
        while self._running and self._mode == "rest_fallback":
            try:
                if self._tracked_symbols:
                    await self._fetch_snapshots(list(self._tracked_symbols))
                    self._stats["rest_polls"] += 1

                    # Trigger re-evaluation for symbols with significant changes
                    if self._on_price_change:
                        for sym, state in self._prices.items():
                            if state.price_changed_significantly():
                                self._stats["reevals_triggered"] += 1
                                try:
                                    asyncio.create_task(self._on_price_change(sym, state))
                                except Exception as e:
                                    logger.error(f"Re-eval callback error for {sym}: {e}")

                await asyncio.sleep(REST_POLL_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"REST poll error: {e}")
                await asyncio.sleep(REST_POLL_INTERVAL)

    async def _handle_event(self, event: Dict):
        event_type = event.get("T")
        symbol = event.get("S", "")

        if symbol not in self._prices:
            return

        state = self._prices[symbol]

        if event_type == "t":  # Trade
            state.update_trade(
                price=event.get("p", 0),
                size=event.get("s", 0),
                timestamp=event.get("t", ""),
            )
            self._stats["trades_received"] += 1

            if state.price_changed_significantly() and self._on_price_change:
                self._stats["reevals_triggered"] += 1
                try:
                    asyncio.create_task(self._on_price_change(symbol, state))
                except Exception as e:
                    logger.error(f"Re-eval callback error for {symbol}: {e}")

        elif event_type == "q":  # Quote
            state.update_quote(
                bid=event.get("bp", 0),
                bid_size=event.get("bs", 0),
                ask=event.get("ap", 0),
                ask_size=event.get("as", 0),
                timestamp=event.get("t", ""),
            )
            self._stats["quotes_received"] += 1

    async def _fetch_snapshots(self, symbols: List[str]):
        if not symbols:
            return
        headers = {
            "APCA-API-KEY-ID": self._api_key,
            "APCA-API-SECRET-KEY": self._secret_key,
        }
        batch_size = 50
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        f"{self._rest_base}/stocks/snapshots",
                        params={"symbols": ",".join(batch)},
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for sym, snap in data.items():
                            if sym in self._prices:
                                trade = snap.get("latestTrade", {})
                                quote = snap.get("latestQuote", {})
                                self._prices[sym].update_from_snapshot(
                                    trade_price=trade.get("p", 0),
                                    bid=quote.get("bp", 0),
                                    ask=quote.get("ap", 0),
                                    timestamp=trade.get("t", ""),
                                )
                        self._stats["snapshots_fetched"] += 1
                    else:
                        logger.warning(f"Snapshot fetch failed: {resp.status_code}")
            except Exception as e:
                logger.error(f"Snapshot fetch error: {e}")

    async def _stale_check_loop(self):
        while self._running:
            try:
                await asyncio.sleep(15)
                for state in self._prices.values():
                    state.check_stale()
            except asyncio.CancelledError:
                break

    def get_status(self) -> Dict:
        stale_count = sum(1 for p in self._prices.values() if p.stale)
        live_count = sum(1 for p in self._prices.values() if p.source == "live")
        snapshot_count = sum(1 for p in self._prices.values() if p.source == "snapshot")
        return {
            "running": self._running,
            "mode": self._mode,
            "ws_connected": self._connected,
            "tracked_symbols": len(self._tracked_symbols),
            "live_count": live_count,
            "snapshot_count": snapshot_count,
            "stale_count": stale_count,
            "reconnect_count": self._reconnect_count,
            "stats": self._stats,
        }
