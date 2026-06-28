"""Top Plays tracking: snapshots each day's ranked short-term list, tracks entries/
exits with hysteresis, labels exit reasons, computes conviction + risk-discipline
fields, and reports forward performance. All data-driven; no randomness."""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

SECTOR_PE_ANCHOR = {
    "Technology": 28, "Communication Services": 22, "Consumer Cyclical": 24,
    "Healthcare": 22, "Financial Services": 14, "Industrials": 20,
    "Consumer Defensive": 20, "Energy": 12, "Utilities": 18,
    "Real Estate": 18, "Basic Materials": 15, "default": 20,
}

HYSTERESIS_DAYS = 2          # consecutive days absent before a pick is exited
HISTORY_WINDOW_DAYS = 90     # how far back exited picks are shown
TARGET_HIT_RETURN = 15.0     # % gain that counts as "target hit" if no analyst target
THESIS_BREAK_RETURN = -8.0   # % loss that flags a broken thesis
THESIS_BREAK_SCORE_DROP = 12 # score deterioration that flags a broken thesis


def _now():
    return datetime.now(timezone.utc)


def _iso():
    return _now().isoformat()


def _days_since(iso_str: Optional[str]) -> float:
    if not iso_str:
        return 0.0
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return round((_now() - dt).total_seconds() / 86400, 1)
    except Exception:
        return 0.0


class TopPlaysTracker:
    COLLECTION = "top_plays_picks"

    def __init__(self, db):
        self.db = db
        self.col = db[self.COLLECTION]

    # ---------- conviction (#4: momentum + value) ----------
    def _conviction(self, view: Dict) -> Dict:
        score = view.get("growthScore") or 0
        up = view.get("analystUpsidePct")
        fcf = view.get("fcfMargin")
        pe = (view.get("valuationMultiples") or {}).get("pe")
        anchor = SECTOR_PE_ANCHOR.get(view.get("sector") or "default", SECTOR_PE_ANCHOR["default"])
        cheap = (pe is None) or (pe and pe > 0 and pe <= anchor)
        value_ok = (up is not None and up > 10) and (fcf is None or fcf > 0)
        if score >= 70 and value_ok and cheap:
            label = "High"
        elif score >= 60 and (up is None or up > 0):
            label = "Medium"
        else:
            label = "Standard"
        reasons = []
        if score >= 70:
            reasons.append("strong momentum score")
        if up is not None and up > 10:
            reasons.append(f"{up:.0f}% analyst upside")
        if cheap and pe:
            reasons.append(f"P/E {pe:g} at/below sector norm ({anchor})")
        if fcf is not None and fcf > 0:
            reasons.append("positive free cash flow")
        return {"conviction": label, "convictionReasons": reasons}

    # ---------- risk discipline (#5) ----------
    def _risk_plan(self, view: Dict) -> Dict:
        risk = view.get("riskScore") or 50
        beta = view.get("beta") or 1.0
        # Higher risk/beta -> wider stop, smaller position.
        stop_pct = round(min(25, max(8, 8 + (risk / 100) * 10 + (beta - 1) * 4)), 1)
        weight_pct = round(min(10, max(2, 10 * (1 - risk / 160))), 1)
        target = view.get("analystConsensusTarget") or (view.get("bullCase") or {}).get("price")
        price = view.get("price")
        rr = None
        if price and target and target > price:
            reward = (target - price) / price * 100
            rr = round(reward / stop_pct, 2) if stop_pct else None
        return {
            "suggestedStopPct": stop_pct,
            "suggestedWeightPct": weight_pct,
            "rewardRiskRatio": rr,
        }

    def _enrich(self, view: Dict) -> Dict:
        out = {}
        out.update(self._conviction(view))
        out.update(self._risk_plan(view))
        return out

    # ---------- exit reason (#2) ----------
    def _exit_reason(self, pick: Dict, ret_pct: Optional[float]) -> str:
        entry_target = pick.get("entryTarget")
        last_price = pick.get("lastPrice")
        entry_score = pick.get("entryScore") or 0
        last_score = pick.get("lastScore") or 0
        if ret_pct is not None:
            if (entry_target and last_price and last_price >= entry_target) or ret_pct >= TARGET_HIT_RETURN:
                return "Target Hit"
            if ret_pct <= THESIS_BREAK_RETURN:
                return "Thesis Broke"
        if (entry_score - last_score) >= THESIS_BREAK_SCORE_DROP:
            return "Thesis Broke"
        return "Out-ranked"

    # ---------- daily reconcile (#1 + #3 hysteresis) ----------
    async def reconcile(self, companies: List[Dict]) -> Dict:
        now = _iso()
        current = {c.get("ticker"): (i, c) for i, c in enumerate(companies) if c.get("ticker")}
        actives = await self.col.find({"status": "active"}).to_list(length=2000)
        active_tickers = {p["ticker"] for p in actives}

        entered, exited, updated = 0, 0, 0

        # Update / exit existing active picks
        for p in actives:
            tk = p["ticker"]
            if tk in current:
                rank, view = current[tk]
                price = view.get("price")
                peak = max(p.get("peakPrice") or 0, price or 0)
                enrich = self._enrich(view)
                await self.col.update_one({"_id": p["_id"]}, {"$set": {
                    "lastPrice": price, "lastScore": view.get("growthScore"),
                    "lastRank": rank + 1, "lastSeen": now, "missedDays": 0,
                    "peakPrice": peak, "name": view.get("name"), "sector": view.get("sector"),
                    "analystTarget": view.get("analystConsensusTarget"),
                    "riskScore": view.get("riskScore"), "beta": view.get("beta"),
                    **enrich,
                }})
                updated += 1
            else:
                absent_days = _days_since(p.get("lastSeen"))
                if absent_days >= HYSTERESIS_DAYS:
                    exit_price = p.get("lastPrice") or p.get("entryPrice")
                    entry_price = p.get("entryPrice")
                    ret = round((exit_price - entry_price) / entry_price * 100, 1) if (exit_price and entry_price) else None
                    await self.col.update_one({"_id": p["_id"]}, {"$set": {
                        "status": "exited", "exitDate": now, "exitPrice": exit_price,
                        "exitReturnPct": ret, "holdDays": _days_since(p.get("entryDate")),
                        "exitReason": self._exit_reason(p, ret),
                    }})
                    exited += 1

        # New entrants
        for tk, (rank, view) in current.items():
            if tk in active_tickers:
                continue
            enrich = self._enrich(view)
            await self.col.insert_one({
                "ticker": tk, "name": view.get("name"), "sector": view.get("sector"),
                "status": "active", "entryDate": now, "entryPrice": view.get("price"),
                "entryScore": view.get("growthScore"), "entryRank": rank + 1,
                "entryTarget": view.get("analystConsensusTarget"),
                "lastPrice": view.get("price"), "lastScore": view.get("growthScore"),
                "lastRank": rank + 1, "lastSeen": now, "missedDays": 0,
                "peakPrice": view.get("price"), "analystTarget": view.get("analystConsensusTarget"),
                "riskScore": view.get("riskScore"), "beta": view.get("beta"),
                **enrich,
            })
            entered += 1

        return {"entered": entered, "exited": exited, "updated": updated, "reconciled_at": now}

    # ---------- read API ----------
    async def get_tracked(self, live_prices: Optional[Dict[str, float]] = None) -> Dict:
        live_prices = live_prices or {}
        actives = await self.col.find({"status": "active"}).sort("lastRank", 1).to_list(length=2000)
        exited = await self.col.find({"status": "exited"}).sort("exitDate", -1).to_list(length=500)

        def clean(p, is_active):
            entry = p.get("entryPrice")
            cur = live_prices.get(p["ticker"]) or p.get("lastPrice") or entry
            ret = round((cur - entry) / entry * 100, 1) if (cur and entry) else None
            # Peak return = best gain achievable from the suggestion date (best-case exit timing).
            peak_seen = max(p.get("peakPrice") or 0, cur or 0, entry or 0)
            peak_ret = round((peak_seen - entry) / entry * 100, 1) if (peak_seen and entry) else None
            doc = {
                "ticker": p["ticker"], "name": p.get("name"), "sector": p.get("sector"),
                "entryDate": p.get("entryDate"), "entryPrice": entry,
                "entryScore": p.get("entryScore"), "entryRank": p.get("entryRank"),
                "currentPrice": cur, "returnPct": ret, "nowReturnPct": ret,
                "peakPrice": round(peak_seen, 2) if peak_seen else None, "peakReturnPct": peak_ret,
                "holdDays": _days_since(p.get("entryDate")),
                "lastScore": p.get("lastScore"), "lastRank": p.get("lastRank"),
                "analystTarget": p.get("analystTarget"),
                "conviction": p.get("conviction", "Standard"),
                "convictionReasons": p.get("convictionReasons", []),
                "suggestedStopPct": p.get("suggestedStopPct"),
                "suggestedWeightPct": p.get("suggestedWeightPct"),
                "rewardRiskRatio": p.get("rewardRiskRatio"),
                "riskScore": p.get("riskScore"), "beta": p.get("beta"),
            }
            if not is_active:
                exit_price = p.get("exitPrice")
                since_exit = round((cur - exit_price) / exit_price * 100, 1) if (cur and exit_price) else None
                doc.update({
                    "exitDate": p.get("exitDate"), "exitPrice": exit_price,
                    "exitReturnPct": p.get("exitReturnPct"), "exitReason": p.get("exitReason"),
                    "sinceExitPct": since_exit, "daysSinceExit": _days_since(p.get("exitDate")),
                })
            return doc

        active_list = [clean(p, True) for p in actives]
        recent_exited = [clean(p, False) for p in exited if _days_since(p.get("exitDate")) <= HISTORY_WINDOW_DAYS]

        return {
            "active": active_list,
            "exited": recent_exited,
            "stats": self._stats(exited),
            "bestPerformers": self._best_performers(active_list, recent_exited),
            "exitedForwardSummary": self._exited_forward_summary(recent_exited),
            "sectorConcentration": self._sector_concentration(active_list),
            "generated_at": _iso(),
        }

    # ---------- best performers leaderboard (ROI since suggestion) ----------
    def _best_performers(self, active: List[Dict], exited: List[Dict], limit: int = 20) -> List[Dict]:
        rows = []
        for p in active:
            rows.append({
                "ticker": p["ticker"], "name": p.get("name"), "sector": p.get("sector"),
                "status": "active", "entryDate": p.get("entryDate"), "entryPrice": p.get("entryPrice"),
                "peakReturnPct": p.get("peakReturnPct"), "nowReturnPct": p.get("nowReturnPct"),
                "realizedReturnPct": None, "holdDays": p.get("holdDays"),
            })
        for p in exited:
            rows.append({
                "ticker": p["ticker"], "name": p.get("name"), "sector": p.get("sector"),
                "status": "exited", "entryDate": p.get("entryDate"), "entryPrice": p.get("entryPrice"),
                "peakReturnPct": p.get("peakReturnPct"), "nowReturnPct": p.get("nowReturnPct"),
                "realizedReturnPct": p.get("exitReturnPct"), "holdDays": p.get("holdDays"),
            })
        rows = [r for r in rows if r.get("peakReturnPct") is not None]
        rows.sort(key=lambda r: r["peakReturnPct"], reverse=True)
        return rows[:limit]

    # ---------- forward performance of names that left the list ----------
    def _exited_forward_summary(self, exited: List[Dict]) -> Dict:
        vals = [(p.get("sinceExitPct"), p.get("daysSinceExit")) for p in exited if p.get("sinceExitPct") is not None]
        if not vals:
            return {"count": 0}
        rets = [v for v, _ in vals]
        days = [d for _, d in vals if d is not None]
        up = [r for r in rets if r > 0]
        return {
            "count": len(rets),
            "pctStillUp": round(len(up) / len(rets) * 100, 1),
            "avgSinceExit": round(sum(rets) / len(rets), 1),
            "avgDaysSinceExit": round(sum(days) / len(days), 1) if days else None,
        }

    # ---------- backfill entries from real historical prices ----------
    async def backfill_entries(self, fetch_history, lookback_days: int = 30) -> Dict:
        """Set each active pick's entry to a real market price ~lookback_days ago and
        peak to the real high over that window, so returns are meaningful immediately.
        fetch_history(ticker) -> list of EOD bars [{date, close, high, ...}] (any order)."""
        cutoff = _now() - timedelta(days=lookback_days)
        actives = await self.col.find({"status": "active"}).to_list(length=2000)
        updated, skipped = 0, 0
        for p in actives:
            try:
                bars = await fetch_history(p["ticker"])
            except Exception:
                bars = None
            parsed = []
            for b in (bars or []):
                ds = b.get("date")
                close = b.get("close")
                if not ds or close is None:
                    continue
                high = b.get("high") if b.get("high") is not None else close
                try:
                    d = datetime.fromisoformat(str(ds).split(" ")[0]).replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                parsed.append((d, float(close), float(high)))
            if not parsed:
                skipped += 1
                continue
            parsed.sort(key=lambda x: x[0])
            entry_bar = next((x for x in parsed if x[0] >= cutoff), parsed[0])
            window = [x for x in parsed if x[0] >= entry_bar[0]]
            entry_price = entry_bar[1]
            last_price = window[-1][1]
            peak_price = max(h for _, _, h in window)
            await self.col.update_one({"_id": p["_id"]}, {"$set": {
                "entryDate": entry_bar[0].isoformat(),
                "entryPrice": round(entry_price, 4),
                "lastPrice": round(last_price, 4),
                "peakPrice": round(peak_price, 4),
                "backfilled": True,
            }})
            updated += 1
        return {"updated": updated, "skipped": skipped, "lookbackDays": lookback_days, "at": _iso()}

    # ---------- all-time best pick (Hall of Fame) ----------
    async def hall_of_fame(self, live_prices: Optional[Dict[str, float]] = None) -> Dict:
        live_prices = live_prices or {}
        docs = await self.col.find({}).to_list(length=5000)
        best = None
        total = 0
        for p in docs:
            entry = p.get("entryPrice")
            if not entry:
                continue
            total += 1
            cur = live_prices.get(p.get("ticker")) or p.get("lastPrice") or entry
            peak = max(p.get("peakPrice") or 0, cur or 0, entry)
            ret = round((peak - entry) / entry * 100, 1)
            if best is None or ret > best["peakReturnPct"]:
                best = {
                    "ticker": p.get("ticker"), "name": p.get("name"), "sector": p.get("sector"),
                    "entryDate": p.get("entryDate"), "entryPrice": entry,
                    "peakPrice": round(peak, 2), "peakReturnPct": ret,
                    "status": p.get("status"), "holdDays": _days_since(p.get("entryDate")),
                }
        return {"best": best, "trackedCount": total, "generated_at": _iso()}

    def _stats(self, exited: List[Dict]) -> Dict:
        rets = [p.get("exitReturnPct") for p in exited if p.get("exitReturnPct") is not None]
        if not rets:
            return {"closedCount": 0, "hitRate": None, "avgReturn": None,
                    "avgWinner": None, "avgLoser": None, "avgHoldDays": None, "reasonBreakdown": {}}
        wins = [r for r in rets if r > 0]
        losses = [r for r in rets if r <= 0]
        holds = [p.get("holdDays") for p in exited if p.get("holdDays") is not None]
        reasons: Dict[str, int] = {}
        for p in exited:
            r = p.get("exitReason")
            if r:
                reasons[r] = reasons.get(r, 0) + 1
        return {
            "closedCount": len(rets),
            "hitRate": round(len(wins) / len(rets) * 100, 1),
            "avgReturn": round(sum(rets) / len(rets), 1),
            "avgWinner": round(sum(wins) / len(wins), 1) if wins else None,
            "avgLoser": round(sum(losses) / len(losses), 1) if losses else None,
            "avgHoldDays": round(sum(holds) / len(holds), 1) if holds else None,
            "reasonBreakdown": reasons,
        }

    def _sector_concentration(self, active: List[Dict]) -> List[Dict]:
        total = len(active) or 1
        counts: Dict[str, int] = {}
        for p in active:
            s = p.get("sector") or "Unknown"
            counts[s] = counts.get(s, 0) + 1
        out = [{"sector": s, "count": n, "pct": round(n / total * 100, 1),
                "concentrated": (n / total) > 0.30} for s, n in counts.items()]
        return sorted(out, key=lambda x: x["count"], reverse=True)
