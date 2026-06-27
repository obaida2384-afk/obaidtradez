"""Top Plays tracking: snapshots each day's ranked short-term list, tracks entries/
exits with hysteresis, labels exit reasons, computes conviction + risk-discipline
fields, and reports forward performance. All data-driven; no randomness."""

from datetime import datetime, timezone
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
            doc = {
                "ticker": p["ticker"], "name": p.get("name"), "sector": p.get("sector"),
                "entryDate": p.get("entryDate"), "entryPrice": entry,
                "entryScore": p.get("entryScore"), "entryRank": p.get("entryRank"),
                "currentPrice": cur, "returnPct": ret,
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
                doc.update({
                    "exitDate": p.get("exitDate"), "exitPrice": p.get("exitPrice"),
                    "exitReturnPct": p.get("exitReturnPct"), "exitReason": p.get("exitReason"),
                })
            return doc

        active_list = [clean(p, True) for p in actives]
        recent_exited = [clean(p, False) for p in exited if _days_since(p.get("exitDate")) <= HISTORY_WINDOW_DAYS]

        return {
            "active": active_list,
            "exited": recent_exited,
            "stats": self._stats(exited),
            "sectorConcentration": self._sector_concentration(active_list),
            "generated_at": _iso(),
        }

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
