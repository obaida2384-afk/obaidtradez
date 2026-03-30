"""
ObaidTradez Technical Analysis Engine
Professional-grade day trading system using Polygon OHLCV data.
All indicators computed internally. Technical structure is the PRIMARY driver.
"""

import asyncio
import logging
import os
import math
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

POLYGON_KEY = os.environ.get("POLYGON_API_KEY", "")


# ===================== TA CACHE =====================

class TACache:
    """In-memory cache with TTL to avoid redundant Polygon API calls within a cycle"""
    _cache: Dict[str, Dict] = {}
    _ttl: int = 300  # 5 minutes

    @classmethod
    def get(cls, symbol: str) -> Optional[Dict]:
        entry = cls._cache.get(symbol)
        if entry and (time.time() - entry["ts"]) < cls._ttl:
            return entry["data"]
        return None

    @classmethod
    def set(cls, symbol: str, data: Dict):
        cls._cache[symbol] = {"data": data, "ts": time.time()}

    @classmethod
    def clear(cls):
        cls._cache.clear()

    @classmethod
    def stats(cls) -> Dict:
        now = time.time()
        valid = sum(1 for e in cls._cache.values() if (now - e["ts"]) < cls._ttl)
        return {"total": len(cls._cache), "valid": valid}


# ===================== POLYGON DATA FETCHER =====================

class PolygonDataFetcher:
    """Fetch OHLCV bars from Polygon for technical analysis"""

    BASE = "https://api.polygon.io"

    @staticmethod
    async def _get(url: str, params: dict, timeout: int = 12) -> Optional[dict]:
        for attempt in range(3):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, params=params, timeout=timeout)
                    if resp.status_code == 200:
                        return resp.json()
                    if resp.status_code == 429:
                        wait = (attempt + 1) * 15
                        logger.warning(f"Polygon 429 rate limit, retrying in {wait}s (attempt {attempt+1}/3)")
                        await asyncio.sleep(wait)
                        continue
                    if resp.status_code == 403:
                        logger.debug(f"Polygon 403 (endpoint requires paid plan): {url.split('?')[0]}")
                        return None
                    logger.warning(f"Polygon {resp.status_code}: {url.split('?')[0]}")
            except Exception as e:
                logger.warning(f"Polygon fetch error: {e}")
                if attempt < 2:
                    await asyncio.sleep(2)
        return None

    @staticmethod
    async def get_bars(symbol: str, timespan: str = "minute",
                       multiplier: int = 5, limit: int = 100) -> List[Dict]:
        """Fetch OHLCV bars. timespan: minute, hour, day. multiplier: 1,5,15"""
        now = datetime.now(timezone.utc)
        # For intraday, use today; for daily, use last 6 months
        if timespan == "day":
            from_date = (now - timedelta(days=180)).strftime("%Y-%m-%d")
            to_date = now.strftime("%Y-%m-%d")
        else:
            from_date = (now - timedelta(days=5)).strftime("%Y-%m-%d")
            to_date = now.strftime("%Y-%m-%d")

        data = await PolygonDataFetcher._get(
            f"{PolygonDataFetcher.BASE}/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_date}/{to_date}",
            {"apiKey": POLYGON_KEY, "limit": limit, "sort": "asc", "adjusted": "true"}
        )
        if not data or data.get("resultsCount", 0) == 0:
            return []
        results = data.get("results", [])
        bars = []
        for r in results:
            bars.append({
                "o": r.get("o", 0), "h": r.get("h", 0),
                "l": r.get("l", 0), "c": r.get("c", 0),
                "v": r.get("v", 0), "t": r.get("t", 0),
                "vw": r.get("vw", 0),
            })
        return bars

    @staticmethod
    async def get_snapshot(symbol: str) -> Optional[Dict]:
        """Get real-time snapshot (last price, bid/ask, volume)"""
        data = await PolygonDataFetcher._get(
            f"{PolygonDataFetcher.BASE}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}",
            {"apiKey": POLYGON_KEY}
        )
        if data and data.get("ticker"):
            t = data["ticker"]
            return {
                "price": t.get("lastTrade", {}).get("p", 0) or t.get("day", {}).get("c", 0),
                "bid": t.get("lastQuote", {}).get("p", 0),
                "ask": t.get("lastQuote", {}).get("P", 0),
                "volume": t.get("day", {}).get("v", 0),
                "prev_close": t.get("prevDay", {}).get("c", 0),
                "today_open": t.get("day", {}).get("o", 0),
                "today_high": t.get("day", {}).get("h", 0),
                "today_low": t.get("day", {}).get("l", 0),
                "prev_volume": t.get("prevDay", {}).get("v", 0),
                "change_pct": t.get("todaysChangePerc", 0),
            }
        return None

    @staticmethod
    async def get_multi_timeframe(symbol: str) -> Dict:
        """Fetch bars concurrently, build snapshot from bar data (no snapshot API needed)"""
        results = await asyncio.gather(
            PolygonDataFetcher.get_bars(symbol, "minute", 1, 100),
            PolygonDataFetcher.get_bars(symbol, "minute", 5, 100),
            PolygonDataFetcher.get_bars(symbol, "minute", 15, 60),
            PolygonDataFetcher.get_bars(symbol, "day", 1, 60),
            return_exceptions=True
        )
        bars_1m = results[0] if isinstance(results[0], list) else []
        bars_5m = results[1] if isinstance(results[1], list) else []
        bars_15m = results[2] if isinstance(results[2], list) else []
        bars_daily = results[3] if isinstance(results[3], list) else []

        # Build snapshot substitute from bar data
        ref_bars = bars_5m or bars_1m or bars_15m
        snapshot = {}
        if ref_bars:
            last_bar = ref_bars[-1]
            prev_close = bars_daily[-2]["c"] if len(bars_daily) >= 2 else (ref_bars[0]["o"] if ref_bars else 0)
            price = last_bar["c"]
            snapshot = {
                "price": price,
                "volume": sum(b["v"] for b in ref_bars),
                "prev_close": prev_close,
                "today_open": ref_bars[0]["o"],
                "today_high": max(b["h"] for b in ref_bars),
                "today_low": min(b["l"] for b in ref_bars),
                "change_pct": round(((price / prev_close) - 1) * 100, 2) if prev_close > 0 else 0,
                "bid": 0,
                "ask": 0,
                "prev_volume": sum(b["v"] for b in bars_daily[-2:-1]) if len(bars_daily) >= 2 else 0,
            }

        return {
            "bars_1m": bars_1m,
            "bars_5m": bars_5m,
            "bars_15m": bars_15m,
            "bars_daily": bars_daily,
            "snapshot": snapshot,
        }


# ===================== TECHNICAL CALCULATOR =====================

class TechnicalCalculator:
    """Compute all technical indicators from raw OHLCV data"""

    @staticmethod
    def ema(values: List[float], period: int) -> List[float]:
        if not values or len(values) < period:
            return []
        k = 2 / (period + 1)
        result = [sum(values[:period]) / period]
        for i in range(period, len(values)):
            result.append(values[i] * k + result[-1] * (1 - k))
        return result

    @staticmethod
    def rsi(closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        gains = []
        losses = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(0, diff))
            losses.append(max(0, -diff))
        if len(gains) < period:
            return 50.0
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 1)

    @staticmethod
    def macd(closes: List[float]) -> Dict:
        if len(closes) < 26:
            return {"macd": 0, "signal": 0, "histogram": 0, "crossover": "none"}
        ema12 = TechnicalCalculator.ema(closes, 12)
        ema26 = TechnicalCalculator.ema(closes, 26)
        if not ema12 or not ema26:
            return {"macd": 0, "signal": 0, "histogram": 0, "crossover": "none"}
        # Align lengths
        offset = len(ema12) - len(ema26)
        macd_line = [ema12[i + offset] - ema26[i] for i in range(len(ema26))]
        signal_line = TechnicalCalculator.ema(macd_line, 9)
        if not signal_line:
            return {"macd": macd_line[-1] if macd_line else 0, "signal": 0, "histogram": 0, "crossover": "none"}
        macd_val = macd_line[-1]
        sig_val = signal_line[-1]
        hist = macd_val - sig_val
        crossover = "none"
        if len(signal_line) >= 2 and len(macd_line) >= 2:
            prev_hist = macd_line[-2] - signal_line[-2]
            if prev_hist <= 0 and hist > 0:
                crossover = "bullish"
            elif prev_hist >= 0 and hist < 0:
                crossover = "bearish"
        return {"macd": round(macd_val, 3), "signal": round(sig_val, 3),
                "histogram": round(hist, 3), "crossover": crossover}

    @staticmethod
    def vwap(bars: List[Dict]) -> float:
        if not bars:
            return 0
        cum_pv = 0
        cum_v = 0
        for b in bars:
            typical = (b["h"] + b["l"] + b["c"]) / 3
            cum_pv += typical * b["v"]
            cum_v += b["v"]
        return round(cum_pv / cum_v, 2) if cum_v > 0 else 0

    @staticmethod
    def relative_volume(bars: List[Dict], period: int = 20) -> float:
        if not bars or len(bars) < 2:
            return 0
        current_vol = bars[-1]["v"]
        avg_vol = sum(b["v"] for b in bars[-period - 1:-1]) / min(period, len(bars) - 1)
        return round(current_vol / avg_vol, 2) if avg_vol > 0 else 0

    @staticmethod
    def avg_range(bars: List[Dict], period: int = 20) -> float:
        if not bars:
            return 0
        recent = bars[-period:] if len(bars) >= period else bars
        ranges = [b["h"] - b["l"] for b in recent]
        return round(sum(ranges) / len(ranges), 4) if ranges else 0

    @staticmethod
    def spread_pct(snapshot: Dict, bars: List[Dict] = None) -> float:
        bid = snapshot.get("bid", 0)
        ask = snapshot.get("ask", 0)
        if bid > 0 and ask > 0:
            mid = (bid + ask) / 2
            return round(abs(ask - bid) / mid * 100, 3) if mid > 0 else 0
        # Fallback: estimate spread from last bar's range vs price
        if bars and len(bars) >= 1:
            last = bars[-1]
            price = last.get("c", 0)
            if price > 0:
                bar_range = last["h"] - last["l"]
                # Typical spread is ~5-10% of the last bar's range for liquid stocks
                return round(min(bar_range * 0.08 / price * 100, 1.0), 3)
        return 0.1  # Default: assume reasonably tight spread

    @staticmethod
    def compute_all(bars_5m: List[Dict], bars_15m: List[Dict],
                    bars_1m: List[Dict], snapshot: Dict) -> Dict:
        """Compute all indicators from bar data"""
        closes_5m = [b["c"] for b in bars_5m] if bars_5m else []
        closes_15m = [b["c"] for b in bars_15m] if bars_15m else []
        closes_1m = [b["c"] for b in bars_1m] if bars_1m else []

        # EMAs on 5-min
        ema9 = TechnicalCalculator.ema(closes_5m, 9)
        ema20 = TechnicalCalculator.ema(closes_5m, 20)
        ema50 = TechnicalCalculator.ema(closes_5m, 50)

        # RSI on 5-min
        rsi_val = TechnicalCalculator.rsi(closes_5m, 14)

        # MACD on 5-min
        macd_data = TechnicalCalculator.macd(closes_5m)

        # VWAP from 1-min bars (intraday)
        vwap_val = TechnicalCalculator.vwap(bars_1m) if bars_1m else (TechnicalCalculator.vwap(bars_5m) if bars_5m else 0)

        # RelVol from 5-min
        rel_vol = TechnicalCalculator.relative_volume(bars_5m, 20)

        # Avg range from 5-min
        avg_rng = TechnicalCalculator.avg_range(bars_5m, 20)

        # Spread (use bars as fallback for bid/ask estimation)
        spread = TechnicalCalculator.spread_pct(snapshot, bars_5m)

        price = snapshot.get("price", 0) or (closes_5m[-1] if closes_5m else 0)

        # VWAP distance
        vwap_dist_pct = round(((price - vwap_val) / vwap_val) * 100, 2) if vwap_val > 0 else 0

        # EMA alignment
        ema_bullish = False
        ema_bearish = False
        if ema9 and ema20 and ema50:
            ema_bullish = ema9[-1] > ema20[-1] > ema50[-1]
            ema_bearish = ema9[-1] < ema20[-1] < ema50[-1]

        return {
            "price": price,
            "ema9": round(ema9[-1], 2) if ema9 else 0,
            "ema20": round(ema20[-1], 2) if ema20 else 0,
            "ema50": round(ema50[-1], 2) if ema50 else 0,
            "ema_bullish": ema_bullish,
            "ema_bearish": ema_bearish,
            "rsi": rsi_val,
            "macd": macd_data,
            "vwap": vwap_val,
            "vwap_distance_pct": vwap_dist_pct,
            "above_vwap": price > vwap_val if vwap_val > 0 else None,
            "rel_vol": rel_vol,
            "avg_range": avg_rng,
            "spread_pct": spread,
            "volume": snapshot.get("volume", 0),
            "prev_close": snapshot.get("prev_close", 0),
            "change_pct": snapshot.get("change_pct", 0),
        }


# ===================== MARKET STRUCTURE ANALYZER =====================

class MarketStructureAnalyzer:
    """Pivot-based HH/HL/LH/LL structure, S/R, structure breaks"""

    @staticmethod
    def find_pivots(bars: List[Dict], lookback: int = 3) -> Dict:
        if len(bars) < lookback * 2 + 1:
            return {"pivot_highs": [], "pivot_lows": [], "structure": "unknown"}

        pivot_highs = []
        pivot_lows = []

        for i in range(lookback, len(bars) - lookback):
            is_high = all(bars[i]["h"] >= bars[i + j]["h"] for j in range(-lookback, lookback + 1) if j != 0)
            is_low = all(bars[i]["l"] <= bars[i + j]["l"] for j in range(-lookback, lookback + 1) if j != 0)
            if is_high:
                pivot_highs.append({"price": bars[i]["h"], "index": i})
            if is_low:
                pivot_lows.append({"price": bars[i]["l"], "index": i})

        return {"pivot_highs": pivot_highs, "pivot_lows": pivot_lows}

    @staticmethod
    def analyze_structure(bars: List[Dict]) -> Dict:
        pivots = MarketStructureAnalyzer.find_pivots(bars, lookback=2)
        ph = pivots["pivot_highs"]
        pl = pivots["pivot_lows"]

        structure = "ranging"
        hh = hl = lh = ll = False

        if len(ph) >= 2:
            hh = ph[-1]["price"] > ph[-2]["price"]
            lh = ph[-1]["price"] < ph[-2]["price"]
        if len(pl) >= 2:
            hl = pl[-1]["price"] > pl[-2]["price"]
            ll = pl[-1]["price"] < pl[-2]["price"]

        if hh and hl:
            structure = "bullish"
        elif lh and ll:
            structure = "bearish"
        elif hh and ll:
            structure = "ranging"
        elif lh and hl:
            structure = "ranging"

        # Support / Resistance from last 20 bars
        recent = bars[-20:] if len(bars) >= 20 else bars
        resistance = max(b["h"] for b in recent) if recent else 0
        support = min(b["l"] for b in recent) if recent else 0

        # Structure break detection
        current_price = bars[-1]["c"] if bars else 0
        structure_break = None
        if structure == "bullish" and len(pl) >= 1 and current_price < pl[-1]["price"]:
            structure_break = "bullish_breakdown"
        elif structure == "bearish" and len(ph) >= 1 and current_price > ph[-1]["price"]:
            structure_break = "bearish_breakout"

        return {
            "structure": structure,
            "hh": hh, "hl": hl, "lh": lh, "ll": ll,
            "resistance": round(resistance, 2),
            "support": round(support, 2),
            "last_pivot_high": round(ph[-1]["price"], 2) if ph else 0,
            "last_pivot_low": round(pl[-1]["price"], 2) if pl else 0,
            "structure_break": structure_break,
        }


# ===================== SETUP DETECTOR =====================

class SetupDetector:
    """Detect breakout, breakdown, liquidity traps, FVG, VWAP reclaim"""

    @staticmethod
    def detect_all(bars: List[Dict], indicators: Dict, structure: Dict) -> List[Dict]:
        setups = []
        if not bars or len(bars) < 5:
            return setups

        price = indicators.get("price", 0)
        vwap = indicators.get("vwap", 0)
        above_vwap = indicators.get("above_vwap", False)
        rel_vol = indicators.get("rel_vol", 0)
        resistance = structure.get("resistance", 0)
        support = structure.get("support", 0)
        struct_type = structure.get("structure", "ranging")

        last_bar = bars[-1]
        prev_bar = bars[-2] if len(bars) >= 2 else last_bar

        # --- BREAKOUT LONG ---
        if (price > resistance * 0.998 and rel_vol >= 1.3
                and above_vwap and struct_type in ("bullish", "ranging")):
            setups.append({
                "type": "breakout_long",
                "direction": "LONG",
                "confidence_boost": 15,
                "reason": f"Close ${price:.2f} > resistance ${resistance:.2f}, RelVol {rel_vol:.1f}x, above VWAP"
            })

        # --- BREAKDOWN SHORT ---
        if (price < support * 1.002 and rel_vol >= 1.3
                and not above_vwap and struct_type in ("bearish", "ranging")):
            setups.append({
                "type": "breakdown_short",
                "direction": "SHORT",
                "confidence_boost": 15,
                "reason": f"Close ${price:.2f} < support ${support:.2f}, RelVol {rel_vol:.1f}x, below VWAP"
            })

        # --- VWAP RECLAIM ---
        if (prev_bar["c"] < vwap and last_bar["c"] > vwap and rel_vol >= 1.2
                and struct_type != "bearish"):
            setups.append({
                "type": "vwap_reclaim",
                "direction": "LONG",
                "confidence_boost": 12,
                "reason": f"VWAP reclaim at ${vwap:.2f} with volume confirmation"
            })

        # --- VWAP LOSS ---
        if (prev_bar["c"] > vwap and last_bar["c"] < vwap and rel_vol >= 1.2
                and struct_type != "bullish"):
            setups.append({
                "type": "vwap_loss",
                "direction": "SHORT",
                "confidence_boost": 12,
                "reason": f"VWAP lost at ${vwap:.2f} with volume confirmation"
            })

        # --- LIQUIDITY SWEEP LONG ---
        prev_low = min(b["l"] for b in bars[-10:-1]) if len(bars) >= 10 else support
        if (last_bar["l"] < prev_low and last_bar["c"] > prev_low
                and rel_vol >= 1.3):
            setups.append({
                "type": "liquidity_sweep_long",
                "direction": "LONG",
                "confidence_boost": 18,
                "reason": f"Swept below ${prev_low:.2f}, closed back above with volume"
            })

        # --- LIQUIDITY SWEEP SHORT ---
        prev_high = max(b["h"] for b in bars[-10:-1]) if len(bars) >= 10 else resistance
        if (last_bar["h"] > prev_high and last_bar["c"] < prev_high
                and rel_vol >= 1.3):
            setups.append({
                "type": "liquidity_sweep_short",
                "direction": "SHORT",
                "confidence_boost": 18,
                "reason": f"Swept above ${prev_high:.2f}, closed back below with volume"
            })

        # --- FAIR VALUE GAP ---
        if len(bars) >= 3:
            # Bullish FVG: bars[-1].l > bars[-3].h (gap up)
            if bars[-1]["l"] > bars[-3]["h"]:
                setups.append({
                    "type": "fvg_bullish",
                    "direction": "LONG",
                    "confidence_boost": 8,
                    "reason": f"Bullish FVG: gap between ${bars[-3]['h']:.2f} and ${bars[-1]['l']:.2f}"
                })
            # Bearish FVG: bars[-1].h < bars[-3].l (gap down)
            if bars[-1]["h"] < bars[-3]["l"]:
                setups.append({
                    "type": "fvg_bearish",
                    "direction": "SHORT",
                    "confidence_boost": 8,
                    "reason": f"Bearish FVG: gap between ${bars[-3]['l']:.2f} and ${bars[-1]['h']:.2f}"
                })

        # --- EMA CROSSOVER ---
        ema9 = indicators.get("ema9", 0)
        ema20 = indicators.get("ema20", 0)
        if ema9 > 0 and ema20 > 0:
            if indicators.get("ema_bullish") and price > ema9:
                setups.append({
                    "type": "ema_alignment_long",
                    "direction": "LONG",
                    "confidence_boost": 8,
                    "reason": f"EMA alignment bullish (9>{ema9:.0f} > 20>{ema20:.0f})"
                })
            elif indicators.get("ema_bearish") and price < ema9:
                setups.append({
                    "type": "ema_alignment_short",
                    "direction": "SHORT",
                    "confidence_boost": 8,
                    "reason": f"EMA alignment bearish (9<{ema9:.0f} < 20<{ema20:.0f})"
                })

        return setups

    @staticmethod
    def detect_fake_breakout(bars: List[Dict], structure: Dict) -> Optional[Dict]:
        if len(bars) < 3:
            return None
        last = bars[-1]
        resistance = structure.get("resistance", 0)
        support = structure.get("support", 0)

        # Bull trap: high > resistance, close < resistance, bearish candle
        if resistance > 0 and last["h"] > resistance and last["c"] < resistance:
            if last["c"] < last["o"]:
                return {"type": "bull_trap", "level": resistance,
                        "reason": f"Bull trap: swept ${resistance:.2f} but closed ${last['c']:.2f} below"}

        # Bear trap: low < support, close > support, bullish candle
        if support > 0 and last["l"] < support and last["c"] > support:
            if last["c"] > last["o"]:
                return {"type": "bear_trap", "level": support,
                        "reason": f"Bear trap: swept ${support:.2f} but closed ${last['c']:.2f} above"}
        return None


# ===================== OVEREXTENSION FILTER =====================

class OverextensionFilter:
    """Reject trades if price too far from VWAP or candle too large"""

    @staticmethod
    def check(indicators: Dict, bars: List[Dict]) -> Tuple[bool, str]:
        vwap_dist = abs(indicators.get("vwap_distance_pct", 0))
        if vwap_dist > 2.5:
            return True, f"Overextended: {vwap_dist:.1f}% from VWAP (max 2.5%)"

        if bars and len(bars) >= 2:
            last_range = bars[-1]["h"] - bars[-1]["l"]
            avg_rng = indicators.get("avg_range", 0)
            if avg_rng > 0 and last_range > avg_rng * 3:
                return True, f"Candle too large: ${last_range:.2f} vs avg ${avg_rng:.2f}"

        return False, ""


# ===================== MULTI-TIMEFRAME CONFIRMER =====================

class MultiTimeframeConfirmer:
    """Confirm trade direction across 1m (entry), 5m (structure), 15m (trend)"""

    @staticmethod
    def confirm(bars_1m: List[Dict], bars_5m: List[Dict],
                bars_15m: List[Dict], direction: str) -> Dict:
        score = 0
        details = []

        # 15-min trend
        if bars_15m and len(bars_15m) >= 5:
            struct_15 = MarketStructureAnalyzer.analyze_structure(bars_15m)
            if direction == "LONG" and struct_15["structure"] == "bullish":
                score += 2
                details.append("15m trend: bullish")
            elif direction == "SHORT" and struct_15["structure"] == "bearish":
                score += 2
                details.append("15m trend: bearish")
            elif struct_15["structure"] == "ranging":
                score += 1
                details.append("15m trend: ranging (neutral)")
            else:
                details.append(f"15m trend: {struct_15['structure']} (opposing)")

        # 5-min structure
        if bars_5m and len(bars_5m) >= 5:
            struct_5 = MarketStructureAnalyzer.analyze_structure(bars_5m)
            if direction == "LONG" and struct_5["structure"] in ("bullish", "ranging"):
                score += 1
                details.append(f"5m structure: {struct_5['structure']}")
            elif direction == "SHORT" and struct_5["structure"] in ("bearish", "ranging"):
                score += 1
                details.append(f"5m structure: {struct_5['structure']}")
            else:
                details.append(f"5m structure: {struct_5['structure']} (opposing)")

        # 1-min entry timing
        if bars_1m and len(bars_1m) >= 3:
            last_3 = bars_1m[-3:]
            if direction == "LONG":
                if last_3[-1]["c"] > last_3[-1]["o"]:
                    score += 1
                    details.append("1m: bullish candle")
            else:
                if last_3[-1]["c"] < last_3[-1]["o"]:
                    score += 1
                    details.append("1m: bearish candle")

        aligned = score >= 3
        return {"aligned": aligned, "score": score, "max": 4, "details": details}


# ===================== FULL TECHNICAL SIGNAL GENERATOR =====================

class TechnicalSignalGenerator:
    """Generate complete technical analysis signal for a stock"""

    @staticmethod
    async def analyze(symbol: str) -> Optional[Dict]:
        """Full technical analysis pipeline for a single stock"""
        try:
            cached = TACache.get(symbol)
            if cached:
                return cached

            data = await PolygonDataFetcher.get_multi_timeframe(symbol)
            bars_1m = data["bars_1m"]
            bars_5m = data["bars_5m"]
            bars_15m = data["bars_15m"]
            snapshot = data["snapshot"]

            if not bars_5m or len(bars_5m) < 10:
                return None

            # 1. Compute all indicators
            indicators = TechnicalCalculator.compute_all(bars_5m, bars_15m, bars_1m, snapshot)
            price = indicators["price"]
            if price <= 0:
                return None

            # 2. Market structure (5-min primary)
            structure = MarketStructureAnalyzer.analyze_structure(bars_5m)

            # 3. Detect setups
            setups = SetupDetector.detect_all(bars_5m, indicators, structure)

            # 4. Fake breakout filter
            fake = SetupDetector.detect_fake_breakout(bars_5m, structure)

            # 5. Overextension filter
            overextended, ext_reason = OverextensionFilter.check(indicators, bars_5m)

            # 6. Determine best direction
            long_setups = [s for s in setups if s["direction"] == "LONG"]
            short_setups = [s for s in setups if s["direction"] == "SHORT"]

            best_setup = None
            direction = "NONE"
            if long_setups:
                best_setup = max(long_setups, key=lambda x: x["confidence_boost"])
                direction = "LONG"
            if short_setups:
                best_short = max(short_setups, key=lambda x: x["confidence_boost"])
                if not best_setup or best_short["confidence_boost"] > best_setup["confidence_boost"]:
                    best_setup = best_short
                    direction = "SHORT"

            # 7. Multi-timeframe confirmation
            mtf = MultiTimeframeConfirmer.confirm(bars_1m, bars_5m, bars_15m, direction)

            # 8. Compute base confidence
            base_confidence = 45
            if best_setup:
                base_confidence += best_setup["confidence_boost"]
            if mtf["aligned"]:
                base_confidence += 10
            elif mtf["score"] >= 2:
                base_confidence += 5
            if indicators["rel_vol"] >= 2.0:
                base_confidence += 8
            elif indicators["rel_vol"] >= 1.3:
                base_confidence += 4
            rsi = indicators["rsi"]
            if direction == "LONG" and 40 < rsi < 70:
                base_confidence += 3
            elif direction == "SHORT" and 30 < rsi < 60:
                base_confidence += 3
            macd_data = indicators["macd"]
            if direction == "LONG" and macd_data["crossover"] == "bullish":
                base_confidence += 5
            elif direction == "SHORT" and macd_data["crossover"] == "bearish":
                base_confidence += 5
            if structure["structure"] == "bullish" and direction == "LONG":
                base_confidence += 5
            elif structure["structure"] == "bearish" and direction == "SHORT":
                base_confidence += 5

            # Penalties
            if fake:
                base_confidence -= 20
            if overextended:
                base_confidence -= 15
            if indicators["spread_pct"] > 0.5:
                base_confidence -= 10
            elif indicators["spread_pct"] > 0.3:
                base_confidence -= 5

            base_confidence = max(0, min(100, base_confidence))

            # Momentum mode: strong volume + breakout + structure → bypass soft filters
            momentum_mode = (indicators["rel_vol"] >= 2.0
                             and best_setup is not None
                             and structure["structure"] in ("bullish", "bearish")
                             and not fake and not overextended)

            # 9. Stop and target
            stop_loss = 0
            take_profit = 0
            if direction == "LONG":
                stop_loss = structure["last_pivot_low"] if structure["last_pivot_low"] > 0 else structure["support"]
                if stop_loss <= 0:
                    stop_loss = price * 0.985
                risk = price - stop_loss
                take_profit = price + risk * 2
            elif direction == "SHORT":
                stop_loss = structure["last_pivot_high"] if structure["last_pivot_high"] > 0 else structure["resistance"]
                if stop_loss <= 0:
                    stop_loss = price * 1.015
                risk = stop_loss - price
                take_profit = price - risk * 2

            rr_ratio = 0
            if direction == "LONG" and stop_loss > 0 and price > stop_loss:
                rr_ratio = round((take_profit - price) / (price - stop_loss), 1)
            elif direction == "SHORT" and stop_loss > 0 and stop_loss > price:
                rr_ratio = round((price - take_profit) / (stop_loss - price), 1)

            result = {
                "symbol": symbol,
                "price": round(price, 2),
                "direction": direction,
                "confidence": base_confidence,
                "momentum_mode": momentum_mode,
                "best_setup": best_setup,
                "all_setups": setups,
                "structure": structure,
                "indicators": indicators,
                "mtf_confirmation": mtf,
                "fake_breakout": fake,
                "overextended": overextended,
                "overextension_reason": ext_reason,
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "rr_ratio": rr_ratio,
                "entry_reasons": [s["reason"] for s in setups],
                "reject_reasons": (
                    ([fake["reason"]] if fake else []) +
                    ([ext_reason] if overextended else []) +
                    ([f"Wide spread: {indicators['spread_pct']:.2f}%"] if indicators["spread_pct"] > 0.5 else [])
                ),
            }
            TACache.set(symbol, result)
            return result
        except Exception as e:
            logger.error(f"Technical analysis error for {symbol}: {e}")
            return None

    @staticmethod
    async def batch_analyze(symbols: List[str], max_concurrent: int = 3) -> List[Dict]:
        """Analyze multiple symbols with controlled concurrency and rate limiting"""
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _analyze_one(sym):
            async with semaphore:
                r = await TechnicalSignalGenerator.analyze(sym)
                if r:
                    results.append(r)
                await asyncio.sleep(0.5)  # Rate limit courtesy

        tasks = [_analyze_one(s) for s in symbols]
        await asyncio.gather(*tasks, return_exceptions=True)
        results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return results


    @staticmethod
    async def analyze_fast(symbol: str) -> Optional[Dict]:
        """Lightweight TA using only 5-min bars (1 API call). Best for rate-limited environments."""
        try:
            cached = TACache.get(symbol)
            if cached:
                return cached

            bars_5m = await PolygonDataFetcher.get_bars(symbol, "minute", 5, 100)
            if not bars_5m or len(bars_5m) < 10:
                return None

            # Build a minimal snapshot from bar data
            last_bar = bars_5m[-1]
            price = last_bar["c"]
            if price <= 0:
                return None

            snapshot = {
                "price": price,
                "volume": sum(b["v"] for b in bars_5m),
                "prev_close": bars_5m[0]["o"],
                "today_open": bars_5m[0]["o"],
                "today_high": max(b["h"] for b in bars_5m),
                "today_low": min(b["l"] for b in bars_5m),
                "change_pct": round(((price / bars_5m[0]["o"]) - 1) * 100, 2) if bars_5m[0]["o"] > 0 else 0,
                "bid": 0,
                "ask": 0,
                "prev_volume": 0,
            }

            indicators = TechnicalCalculator.compute_all(bars_5m, [], [], snapshot)
            structure = MarketStructureAnalyzer.analyze_structure(bars_5m)
            setups = SetupDetector.detect_all(bars_5m, indicators, structure)
            fake = SetupDetector.detect_fake_breakout(bars_5m, structure)
            overextended, ext_reason = OverextensionFilter.check(indicators, bars_5m)

            # Direction + setup selection (same logic as full analyze)
            best_setup = None
            direction = "NONE"
            if setups:
                setups.sort(key=lambda s: s.get("confidence_boost", 0), reverse=True)
                best_setup = setups[0]
                direction = best_setup.get("direction", "LONG")

            if not best_setup:
                if indicators.get("ema_bullish") and indicators.get("rsi", 50) > 50:
                    direction = "LONG"
                elif indicators.get("ema_bearish") and indicators.get("rsi", 50) < 50:
                    direction = "SHORT"

            # Confidence scoring
            base_confidence = 45
            if best_setup:
                base_confidence += min(best_setup.get("confidence_boost", 0), 18)
            rel_vol = indicators.get("rel_vol", 0)
            if rel_vol >= 2.0:
                base_confidence += 8
            elif rel_vol >= 1.3:
                base_confidence += 4
            rsi = indicators.get("rsi", 50)
            if 40 <= rsi <= 60:
                base_confidence += 3
            elif 30 <= rsi <= 70:
                base_confidence += 1
            macd = indicators.get("macd", {})
            if macd.get("crossover") == "bullish" and direction == "LONG":
                base_confidence += 5
            elif macd.get("crossover") == "bearish" and direction == "SHORT":
                base_confidence += 5
            if fake:
                base_confidence -= 20
            if overextended:
                base_confidence -= 15
            if indicators.get("spread_pct", 0) > 0.5:
                base_confidence -= 5
            elif indicators.get("spread_pct", 0) > 0.3:
                base_confidence -= 2
            base_confidence = max(0, min(100, base_confidence))

            momentum_mode = rel_vol >= 2.0 and structure.get("structure") in ("bullish", "bearish")

            # Stop/target from setup or ATR
            avg_range = indicators.get("avg_range", price * 0.01)
            if best_setup and best_setup.get("stop"):
                stop_loss = best_setup["stop"]
            else:
                stop_loss = price - (avg_range * 1.5) if direction == "LONG" else price + (avg_range * 1.5)
            if best_setup and best_setup.get("target"):
                take_profit = best_setup["target"]
            else:
                take_profit = price + (avg_range * 2.5) if direction == "LONG" else price - (avg_range * 2.5)

            risk_dist = abs(price - stop_loss)
            reward_dist = abs(take_profit - price)
            rr_ratio = round(reward_dist / risk_dist, 2) if risk_dist > 0 else 0

            result = {
                "symbol": symbol,
                "price": round(price, 2),
                "direction": direction,
                "confidence": base_confidence,
                "momentum_mode": momentum_mode,
                "best_setup": best_setup,
                "all_setups": setups,
                "structure": structure,
                "indicators": indicators,
                "mtf_confirmation": {"aligned": False, "score": 0, "details": ["fast mode: single timeframe"]},
                "fake_breakout": fake,
                "overextended": overextended,
                "overextension_reason": ext_reason,
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "rr_ratio": rr_ratio,
                "entry_reasons": [s["reason"] for s in setups],
                "reject_reasons": (
                    ([fake["reason"]] if fake else []) +
                    ([ext_reason] if overextended else []) +
                    ([f"Wide spread: {indicators['spread_pct']:.2f}%"] if indicators["spread_pct"] > 0.5 else [])
                ),
                "analysis_mode": "fast",
            }
            TACache.set(symbol, result)
            return result
        except Exception as e:
            logger.error(f"Fast TA error for {symbol}: {e}")
            return None

    @staticmethod
    async def batch_analyze_fast(symbols: List[str], max_concurrent: int = 1) -> List[Dict]:
        """Analyze with 1 API call per stock. Strictly rate-limited (max ~4 calls/min for Polygon free)."""
        results = []

        for sym in symbols:
            r = await TechnicalSignalGenerator.analyze_fast(sym)
            if r:
                results.append(r)
            await asyncio.sleep(13)  # 60s / 5 calls = 12s min, use 13s for safety

        results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return results
