"""Intraday trade candidate engine: news + technicals + analyst flow, with a full trade plan per pick."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
ET = ZoneInfo("America/New_York")

EXCLUDE_NAME_HINTS = (
    "etf", "fund", "trust", " etn", "3x", "2x", "1.5x", "bull", "bear",
    "leveraged", "direxion", "proshares", "graniteshares", "ultra ", "inverse",
)


def _f(x) -> Optional[float]:
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


def _rsi(closes: List[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    avg_g, avg_l = gains / period, losses / period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        avg_g = (avg_g * (period - 1) + max(d, 0)) / period
        avg_l = (avg_l * (period - 1) + max(-d, 0)) / period
    if avg_l == 0:
        return 100.0
    return round(100 - 100 / (1 + avg_g / avg_l), 1)


def _ema(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = v * k + e * (1 - k)
    return round(e, 2)


class DayTradesEngine:
    PICKS = "day_trades_log"
    CACHE = "day_trades_cache"
    CACHE_TTL_SEC = 15 * 60

    def __init__(self, db, api_client, fmp_key_getter, news_service):
        self.db = db
        self.api = api_client
        self._key = fmp_key_getter
        self.news = news_service

    async def _fmp(self, endpoint: str, params: Optional[Dict] = None, timeout: float = 20.0):
        return await self.api._request(
            f"{self.api.fmp_url}/{endpoint}",
            headers={"apikey": self._key()},
            params=dict(params or {}),
            timeout=timeout,
        )

    # ---------- session context ----------
    @staticmethod
    def _session_note() -> Dict:
        now = datetime.now(ET)
        hm = now.hour * 60 + now.minute
        if now.weekday() >= 5:
            phase, note = "Closed", "Market closed (weekend). Candidates reflect the last session — use them to prepare Monday's watchlist."
        elif hm < 4 * 60:
            phase, note = "Closed", "Market closed. Candidates reflect the last session."
        elif hm < 9 * 60 + 30:
            phase, note = "Pre-market", "Pre-market. Build your watchlist now; confirm catalysts and pre-market volume before the open."
        elif hm < 9 * 60 + 45:
            phase, note = "Opening range", "First 15 minutes: let the opening range form. Do not chase — wait for your entry trigger."
        elif hm < 11 * 60 + 30:
            phase, note = "Morning drive", "Prime window. Momentum and volume are strongest — execute planned entries only."
        elif hm < 14 * 60:
            phase, note = "Midday chop", "Lunch chop: volume dries up, ranges tighten. Manage open positions; avoid fresh entries."
        elif hm < 15 * 60 + 30:
            phase, note = "Afternoon", "Volume returns. Watch for VWAP reclaims and afternoon breakouts."
        elif hm < 16 * 60:
            phase, note = "Power hour", "Final stretch. Close remaining day trades before 15:45 ET — no overnight holds."
        else:
            phase, note = "Closed", "Market closed. Review today's trades and prepare tomorrow's plan."
        return {"phase": phase, "note": note, "etTime": now.strftime("%H:%M ET")}

    # ---------- candidate sourcing ----------
    async def _candidates(self) -> List[Dict]:
        gainers, actives = await asyncio.gather(
            self._fmp("biggest-gainers"), self._fmp("most-actives"),
            return_exceptions=True,
        )
        rows, seen = [], set()

        def add(lst, source):
            for r in (lst if isinstance(lst, list) else []):
                sym = r.get("symbol")
                name = (r.get("name") or "").lower()
                price = _f(r.get("price")) or 0
                chg = _f(r.get("changesPercentage"))
                if not sym or sym in seen or "." in sym:
                    continue
                if any(h in name for h in EXCLUDE_NAME_HINTS):
                    continue
                if price < 2 or price > 1500:
                    continue
                if source == "gainer" and (chg is None or chg < 3 or chg > 75):
                    continue
                if source == "active" and (chg is None or abs(chg) < 1.5):
                    continue
                seen.add(sym)
                rows.append({"ticker": sym, "name": r.get("name"), "changePct": chg, "sourceList": source})

        add(gainers, "gainer")
        add(actives, "active")
        return rows[:16]

    # ---------- enrichment ----------
    async def _enrich(self, cand: Dict) -> Optional[Dict]:
        sym = cand["ticker"]
        quote, bars, ptc, cons, grades, news, eod = await asyncio.gather(
            self.api.fmp_quote(sym),
            self._fmp("historical-chart/5min", {"symbol": sym}),
            self._fmp("price-target-consensus", {"symbol": sym}),
            self._fmp("grades-consensus", {"symbol": sym}),
            self._fmp("grades", {"symbol": sym}),
            self.news.company_news(sym, items=4),
            self._fmp("historical-price-eod/full", {"symbol": sym}),
            return_exceptions=True,
        )

        def ok(x):
            return x if not isinstance(x, Exception) else None

        quote, bars, ptc, cons, grades, news, eod = ok(quote), ok(bars), ok(ptc), ok(cons), ok(grades), ok(news), ok(eod)
        if not quote or not _f(quote.get("price")):
            return None

        avg_volume = None
        if isinstance(eod, list) and len(eod) > 1:
            vols = [_f(b.get("volume")) for b in eod[1:21] if _f(b.get("volume"))]
            if vols:
                avg_volume = sum(vols) / len(vols)

        price = _f(quote.get("price"))
        tech = self._technicals(bars, quote, price, avg_volume)
        analyst = self._analyst(ptc, cons, grades, price)
        catalyst = self._catalyst(news)
        score, signals, risks = self._score(cand, price, tech, analyst, catalyst)
        plan = self._trade_plan(sym, price, tech)

        return {
            "ticker": sym,
            "name": quote.get("name") or cand.get("name"),
            "price": round(price, 2),
            "changePct": _f(quote.get("changePercentage")) or cand.get("changePct"),
            "sourceList": cand.get("sourceList"),
            "dayHigh": _f(quote.get("dayHigh")),
            "dayLow": _f(quote.get("dayLow")),
            "open": _f(quote.get("open")),
            "prevClose": _f(quote.get("previousClose")),
            "volume": _f(quote.get("volume")),
            "avgVolume": _f(quote.get("avgVolume")),
            "marketCap": _f(quote.get("marketCap")),
            "technicals": tech,
            "analyst": analyst,
            "catalyst": catalyst,
            "score": score,
            "signals": signals,
            "risks": risks,
            "plan": plan,
        }

    @staticmethod
    def _technicals(bars, quote, price, avg_volume=None) -> Dict:
        out = {"vwap": None, "rsi14": None, "ema9": None, "relVolume": None,
               "openingRangeHigh": None, "openingRangeLow": None, "sessionDate": None,
               "aboveVwap": None, "distFromVwapPct": None}
        vol = _f(quote.get("volume"))
        if vol and avg_volume:
            out["relVolume"] = round(vol / avg_volume, 2)
        if not isinstance(bars, list) or not bars:
            return out
        session = bars[0].get("date", "")[:10]
        day = [b for b in bars if (b.get("date") or "").startswith(session)]
        day.reverse()  # chronological
        if not day:
            return out
        out["sessionDate"] = session
        closes = [_f(b.get("close")) for b in day if _f(b.get("close")) is not None]
        pv = sv = 0.0
        for b in day:
            h, l, c, v = _f(b.get("high")), _f(b.get("low")), _f(b.get("close")), _f(b.get("volume")) or 0
            if None in (h, l, c):
                continue
            pv += (h + l + c) / 3 * v
            sv += v
        if sv > 0:
            out["vwap"] = round(pv / sv, 2)
        out["rsi14"] = _rsi(closes)
        out["ema9"] = _ema(closes, 9)
        orb = day[:3]
        if orb:
            out["openingRangeHigh"] = round(max(_f(b.get("high")) or 0 for b in orb), 2)
            out["openingRangeLow"] = round(min(_f(b.get("low")) or 1e12 for b in orb), 2)
        if out["vwap"] and price:
            out["aboveVwap"] = price > out["vwap"]
            out["distFromVwapPct"] = round((price - out["vwap"]) / out["vwap"] * 100, 2)
        return out

    @staticmethod
    def _analyst(ptc, cons, grades, price) -> Dict:
        ptc0 = ptc[0] if isinstance(ptc, list) and ptc else (ptc if isinstance(ptc, dict) else {})
        cons0 = cons[0] if isinstance(cons, list) and cons else (cons if isinstance(cons, dict) else {})
        target = _f(ptc0.get("targetConsensus") or ptc0.get("targetMedian"))
        upside = round((target - price) / price * 100, 1) if (target and price) else None
        recent = []
        cutoff = datetime.now(timezone.utc).timestamp() - 7 * 86400
        for g in (grades if isinstance(grades, list) else [])[:20]:
            try:
                d = datetime.strptime(g.get("date", ""), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if d.timestamp() >= cutoff:
                recent.append({
                    "date": g.get("date"), "firm": g.get("gradingCompany"),
                    "action": g.get("action"), "grade": g.get("newGrade"),
                    "previousGrade": g.get("previousGrade"),
                })
        bullish_actions = sum(1 for r in recent if (r.get("action") or "").lower() in ("upgrade", "initiate") or
                              ("buy" in (r.get("grade") or "").lower() and (r.get("action") or "").lower() == "maintain"))
        return {
            "consensus": cons0.get("consensus"),
            "priceTarget": target,
            "upsidePct": upside,
            "recentActions": recent[:5],
            "recentBullishActions": bullish_actions,
        }

    @staticmethod
    def _catalyst(news) -> Dict:
        articles = (news or {}).get("articles") or []
        today = datetime.now(ET).strftime("%m/%d/%Y")
        fresh = [a for a in articles if today in (a.get("date") or "")] or articles[:1]
        top = fresh[0] if fresh else None
        return {
            "headline": top.get("title") if top else None,
            "url": top.get("url") if top else None,
            "source": top.get("source") if top else None,
            "date": top.get("date") if top else None,
            "sentiment": top.get("sentiment") if top else None,
            "isToday": bool(top and today in (top.get("date") or "")),
            "tone": (news or {}).get("sentiment", {}).get("tone"),
        }

    @staticmethod
    def _score(cand, price, tech, analyst, catalyst):
        score, signals, risks = 0.0, [], []
        chg = _f(cand.get("changePct")) or 0
        score += min(max(chg, 0), 30) / 30 * 20
        if chg >= 5:
            signals.append(f"Strong momentum: +{chg:.1f}% today")
        rv = tech.get("relVolume")
        if rv:
            score += min(rv, 5) / 5 * 20
            if rv >= 2:
                signals.append(f"Relative volume {rv}x — institutional participation")
            elif rv < 1:
                risks.append("Below-average volume: moves may not sustain")
        if tech.get("aboveVwap"):
            score += 10
            signals.append("Trading above VWAP — buyers in control")
        elif tech.get("aboveVwap") is False:
            risks.append("Below VWAP — sellers in control, wait for reclaim")
        rsi = tech.get("rsi14")
        if rsi is not None:
            if 50 <= rsi <= 75:
                score += 15
                signals.append(f"RSI {rsi}: healthy momentum, not overheated")
            elif 40 <= rsi < 50 or 75 < rsi <= 80:
                score += 5
            if rsi > 80:
                risks.append(f"RSI {rsi}: overextended — only enter on a pullback")
        if catalyst.get("isToday"):
            score += 15 if catalyst.get("sentiment") == "Positive" else 8
            signals.append("Fresh news catalyst today")
        if analyst.get("recentBullishActions"):
            score += 10
            signals.append(f"{analyst['recentBullishActions']} bullish analyst action(s) this week")
        if "Buy" in str(analyst.get("consensus") or ""):
            score += 10
            signals.append(f"Analyst consensus: {analyst['consensus']}")
        if price < 5:
            risks.append("Sub-$5 stock: expect violent swings, size down")
        if not catalyst.get("headline"):
            risks.append("No identifiable news catalyst — purely technical move")
        return round(min(score, 100), 1), signals, risks

    @staticmethod
    def _trade_plan(sym, price, tech) -> Dict:
        vwap = tech.get("vwap")
        orh = tech.get("openingRangeHigh")
        entry = price
        entry_low = round(max(vwap, price * 0.985), 2) if vwap and vwap < price else round(price * 0.99, 2)
        target1 = round(entry * 1.02, 2)
        target2 = round(entry * 1.03, 2)
        stop = entry * 0.985
        if vwap and vwap < entry:
            stop = min(max(entry * 0.985, vwap * 0.995), entry * 0.9925)
        stop = round(stop, 2)
        stop_pct = round((stop - entry) / entry * 100, 1)
        rr = round((target1 - entry) / (entry - stop), 1) if entry > stop else None
        vtxt = f"${vwap}" if vwap else "VWAP"
        steps = [
            f"PRE-TRADE — Confirm the catalyst is still live and {sym} holds above {vtxt} (VWAP). If price is below VWAP, stand aside until it reclaims it.",
            f"ENTRY — Two valid triggers: (a) a pullback into the ${entry_low}–${round(entry, 2)} zone that holds VWAP with green 5-min candles, or (b) a break above the opening-range high {'$' + str(orh) if orh else ''} on rising volume. Never market-buy a vertical candle.",
            f"STOP — Hard stop at ${stop} ({stop_pct}%). It sits below VWAP/support. Enter the stop order immediately after filling. Never widen it.",
            f"TARGET 1 — ${target1} (+2%): sell 50–75% of the position and move your stop to breakeven (${round(entry, 2)}). The trade is now risk-free.",
            f"TARGET 2 — ${target2} (+3%): sell the remainder, or trail the last part with the 9-EMA on the 5-min chart{' (currently $' + str(tech.get('ema9')) + ')' if tech.get('ema9') else ''} — exit on a 5-min close below it.",
            "TIME EXIT — If neither target nor stop is hit by 15:45 ET, close the position. Day trades do not become overnight holds.",
        ]
        return {
            "entryZoneLow": entry_low, "entryRef": round(entry, 2),
            "target1": target1, "target2": target2,
            "stop": stop, "stopPct": stop_pct, "rewardRisk": rr,
            "steps": steps,
        }

    # ---------- public API ----------
    async def generate(self, force: bool = False) -> Dict:
        today = datetime.now(ET).strftime("%Y-%m-%d")
        cache = await self.db[self.CACHE].find_one({"_id": today})
        if cache and not force:
            age = datetime.now(timezone.utc).timestamp() - cache.get("ts", 0)
            if age < self.CACHE_TTL_SEC:
                payload = cache["payload"]
                payload["cached"] = True
                payload["session"] = self._session_note()
                return payload

        cands = await self._candidates()
        enriched = []
        for i in range(0, len(cands), 4):
            batch = await asyncio.gather(*(self._enrich(c) for c in cands[i:i + 4]), return_exceptions=True)
            enriched.extend(e for e in batch if isinstance(e, dict))
        enriched.sort(key=lambda x: x["score"], reverse=True)
        picks = enriched[:8]

        for p in picks:
            await self.db[self.PICKS].update_one(
                {"date": today, "ticker": p["ticker"]},
                {"$setOnInsert": {
                    "date": today, "ticker": p["ticker"], "name": p.get("name"),
                    "entryRef": p["plan"]["entryRef"], "target1": p["plan"]["target1"],
                    "target2": p["plan"]["target2"], "stop": p["plan"]["stop"],
                    "score": p["score"], "pickedAt": datetime.now(timezone.utc).isoformat(),
                    "outcome": None,
                }},
                upsert=True,
            )

        payload = {
            "date": today,
            "session": self._session_note(),
            "candidates": picks,
            "scanned": len(cands),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "cached": False,
        }
        await self.db[self.CACHE].replace_one(
            {"_id": today},
            {"_id": today, "ts": datetime.now(timezone.utc).timestamp(), "payload": payload},
            upsert=True,
        )
        return payload

    async def _evaluate_pick(self, pick: Dict):
        data = await self._fmp("historical-price-eod/full", {
            "symbol": pick["ticker"], "from": pick["date"], "to": pick["date"],
        })
        bar = data[0] if isinstance(data, list) and data else None
        if not bar:
            return
        high, low, close = _f(bar.get("high")), _f(bar.get("low")), _f(bar.get("close"))
        entry, t1, t2, stop = pick["entryRef"], pick["target1"], pick["target2"], pick["stop"]
        if high is None or low is None:
            return
        if low <= stop and high >= t1:
            outcome, realized = "ambiguous_stopped", round((stop - entry) / entry * 100, 1)
        elif high >= t2:
            outcome, realized = "target2_hit", round((t2 - entry) / entry * 100, 1)
        elif high >= t1:
            outcome, realized = "target1_hit", round((t1 - entry) / entry * 100, 1)
        elif low <= stop:
            outcome, realized = "stopped", round((stop - entry) / entry * 100, 1)
        else:
            outcome = "closed_flat"
            realized = round((close - entry) / entry * 100, 1) if close else None
        await self.db[self.PICKS].update_one(
            {"_id": pick["_id"]},
            {"$set": {"outcome": outcome, "realizedPct": realized, "dayHigh": high, "dayLow": low, "dayClose": close}},
        )

    async def scoreboard(self) -> Dict:
        today = datetime.now(ET).strftime("%Y-%m-%d")
        pending = await self.db[self.PICKS].find({"date": {"$lt": today}, "outcome": None}).to_list(length=100)
        for p in pending:
            try:
                await self._evaluate_pick(p)
            except Exception as e:
                logger.warning(f"[day-trades] evaluate {p.get('ticker')}: {e}")

        done = await self.db[self.PICKS].find({"outcome": {"$ne": None}}).sort("date", -1).to_list(length=300)
        wins = [p for p in done if p["outcome"] in ("target1_hit", "target2_hit")]
        losses = [p for p in done if p["outcome"] in ("stopped", "ambiguous_stopped")]
        realized = [p.get("realizedPct") for p in done if p.get("realizedPct") is not None]
        rows = [{
            "date": p["date"], "ticker": p["ticker"], "name": p.get("name"),
            "entryRef": p.get("entryRef"), "target1": p.get("target1"), "stop": p.get("stop"),
            "outcome": p["outcome"], "realizedPct": p.get("realizedPct"), "score": p.get("score"),
        } for p in done[:60]]
        return {
            "evaluated": len(done),
            "targetHits": len(wins),
            "stops": len(losses),
            "flat": len(done) - len(wins) - len(losses),
            "winRatePct": round(len(wins) / len(done) * 100, 1) if done else None,
            "avgRealizedPct": round(sum(realized) / len(realized), 2) if realized else None,
            "history": rows,
        }
