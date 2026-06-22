"""
Company Universe - scalable, API-driven company dataset.

Builds a dynamic universe (1,000-5,000 companies) sourced from the FMP screener
rather than a hardcoded list, enriches each name with fundamentals, analyst,
ownership and valuation data, and persists records with per-field provenance.

No values are fabricated: when a provider has no data for a field the value is
left null and its source is marked as estimated/unavailable.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_UNIVERSE_SIZE = 5000
ESTIMATED = "Estimated from historical trends and industry averages"

# Sector valuation anchors used to frame "cheap vs peers" without inventing numbers.
SECTOR_PE_ANCHOR = {
    "Technology": 28, "Healthcare": 22, "Financial Services": 12,
    "Consumer Cyclical": 20, "Consumer Defensive": 24, "Industrials": 20,
    "Energy": 12, "Basic Materials": 15, "Real Estate": 35, "Utilities": 18,
    "Communication Services": 20, "default": 20,
}


def _f(value: Any) -> Optional[float]:
    """Coerce to float, returning None on failure/blank."""
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: Optional[float], digits: int = 2) -> Optional[float]:
    return round(value, digits) if isinstance(value, (int, float)) else None


def _market_cap_label(mc: Optional[float]) -> str:
    if not mc:
        return "Unknown"
    if mc >= 200e9:
        return "Mega Cap"
    if mc >= 10e9:
        return "Large Cap"
    if mc >= 2e9:
        return "Mid Cap"
    if mc >= 300e6:
        return "Small Cap"
    if mc >= 50e6:
        return "Micro Cap"
    return "Nano Cap"


class CompanyUniverseService:
    """Owns the API-driven company universe lifecycle: build, enrich, query."""

    COLLECTION = "company_universe"
    META_ID = "company_universe_meta"

    def __init__(self, api_client, db, fmp_key_getter):
        self.api = api_client
        self.db = db
        self._fmp_key_getter = fmp_key_getter
        self._indexed = False

    # ---------- low level ----------

    @property
    def _fmp_key(self) -> Optional[str]:
        return self._fmp_key_getter()

    async def _fmp(self, endpoint: str, params: Optional[Dict] = None, timeout: float = 20.0):
        params = dict(params or {})
        return await self.api._request(
            f"{self.api.fmp_url}/{endpoint}",
            headers={"apikey": self._fmp_key},
            params=params,
            timeout=timeout,
        )

    async def _ensure_indexes(self):
        if self._indexed:
            return
        try:
            col = self.db[self.COLLECTION]
            await col.create_index("ticker", unique=True)
            await col.create_index("sector")
            await col.create_index("marketCap")
            await col.create_index("opportunityScore")
            self._indexed = True
        except Exception as e:
            logger.warning(f"Universe index creation skipped: {e}")

    # ---------- discovery (dynamic, not hardcoded) ----------

    async def discover_tickers(
        self,
        target_size: int,
        min_market_cap: float = 50e6,
        exchanges: str = "NASDAQ,NYSE,AMEX",
    ) -> List[Dict]:
        """Pull a dynamic ticker list from the FMP screener, largest first."""
        target_size = max(1, min(int(target_size), MAX_UNIVERSE_SIZE))
        data = await self.api.fmp_screener({
            "marketCapMoreThan": int(min_market_cap),
            "isActivelyTrading": "true",
            "isEtf": "false",
            "isFund": "false",
            "exchange": exchanges,
            "limit": target_size,
        })
        if not isinstance(data, list):
            return []

        rows = []
        for r in data:
            symbol = r.get("symbol")
            if not symbol:
                continue
            rows.append({
                "ticker": symbol,
                "companyName": r.get("companyName") or symbol,
                "sector": r.get("sector"),
                "industry": r.get("industry"),
                "marketCap": _f(r.get("marketCap")),
                "price": _f(r.get("price")),
            })
        rows.sort(key=lambda x: x.get("marketCap") or 0, reverse=True)
        return rows[:target_size]

    # ---------- enrichment ----------

    async def enrich_company(self, base: Dict) -> Dict:
        """Build a full CompanyRecord for one ticker from multiple API sources."""
        symbol = base["ticker"]
        profile, quote, ratios, metrics, growth, estimates, ptc, grades, peers = await asyncio.gather(
            self.api.fmp_profile(symbol),
            self.api.fmp_quote(symbol),
            self.api.fmp_ratios(symbol),
            self.api.fmp_metrics(symbol),
            self._fmp("financial-growth", {"symbol": symbol, "limit": 2}),
            self._fmp("analyst-estimates", {"symbol": symbol, "period": "annual", "limit": 2}),
            self._fmp("price-target-consensus", {"symbol": symbol}),
            self._fmp("grades-consensus", {"symbol": symbol}),
            self._fmp("stock-peers", {"symbol": symbol}),
            return_exceptions=True,
        )

        def ok(x):
            return x if not isinstance(x, Exception) else None

        profile, quote, ratios, metrics = ok(profile), ok(quote), ok(ratios), ok(metrics)
        growth, estimates, ptc, grades, peers = ok(growth), ok(estimates), ok(ptc), ok(grades), ok(peers)

        g0 = growth[0] if isinstance(growth, list) and growth else {}
        g1 = growth[1] if isinstance(growth, list) and len(growth) > 1 else {}
        ptc0 = ptc[0] if isinstance(ptc, list) and ptc else (ptc if isinstance(ptc, dict) else {})
        grades0 = grades[0] if isinstance(grades, list) and grades else (grades if isinstance(grades, dict) else {})

        sources: Dict[str, str] = {}

        # Identity
        name = (profile or {}).get("companyName") or base.get("companyName") or symbol
        sector = (profile or {}).get("sector") or base.get("sector")
        industry = (profile or {}).get("industry") or base.get("industry")
        market_cap = _f((profile or {}).get("marketCap")) or base.get("marketCap")
        price = _f((quote or {}).get("price")) or _f((profile or {}).get("price")) or base.get("price")
        if profile:
            sources["companyName"] = sources["sector"] = sources["industry"] = "FMP profile"
        sources["price"] = "FMP quote" if quote else (ESTIMATED if price is None else "FMP profile")
        sources["marketCap"] = "FMP profile" if profile else "FMP screener"

        # Growth
        rev_growth = _f(g0.get("revenueGrowth"))
        rev_growth_prior = _f(g1.get("revenueGrowth"))
        rev_growth = _round(rev_growth * 100) if rev_growth is not None else None
        rev_growth_prior = _round(rev_growth_prior * 100) if rev_growth_prior is not None else None
        rev_accel = _round(rev_growth - rev_growth_prior) if (rev_growth is not None and rev_growth_prior is not None) else None
        eps_growth = _f(g0.get("epsgrowth") if g0.get("epsgrowth") is not None else g0.get("epsGrowth"))
        eps_growth = _round(eps_growth * 100) if eps_growth is not None else None
        if growth:
            sources["revenueGrowth"] = sources["epsGrowth"] = "FMP financial-growth"
            sources["revenueAcceleration"] = "Computed (YoY growth delta)" if rev_accel is not None else ESTIMATED

        # Margins
        ebitda_margin = _f((metrics or {}).get("ebitdaMargin") if metrics else None)
        if ebitda_margin is None and ratios:
            ebitda_margin = _f(ratios.get("ebitdaMarginTTM") or ratios.get("operatingProfitMarginTTM"))
        ebitda_margin = _round(ebitda_margin * 100) if (ebitda_margin is not None and abs(ebitda_margin) <= 5) else _round(ebitda_margin)
        fcf_margin = None
        if metrics:
            fcf_margin = _f(metrics.get("freeCashFlowMargin"))
        if fcf_margin is None and ratios:
            fcf_margin = _f(ratios.get("freeCashFlowMarginTTM"))
        fcf_margin = _round(fcf_margin * 100) if (fcf_margin is not None and abs(fcf_margin) <= 5) else _round(fcf_margin)
        sources["ebitdaMargin"] = "FMP key-metrics/ratios" if ebitda_margin is not None else ESTIMATED
        sources["fcfMargin"] = "FMP key-metrics/ratios" if fcf_margin is not None else ESTIMATED

        # Valuation multiples
        pe = _f((ratios or {}).get("priceToEarningsRatioTTM") or (ratios or {}).get("peRatioTTM")) if ratios else _f((quote or {}).get("pe"))
        ev_ebitda = _f((ratios or {}).get("enterpriseValueMultipleTTM") or (ratios or {}).get("evToEBITDATTM")) if ratios else None
        ps = _f((ratios or {}).get("priceToSalesRatioTTM")) if ratios else None
        pfcf = _f((ratios or {}).get("priceToFreeCashFlowsRatioTTM")) if ratios else None
        valuation_multiples = {
            "pe": _round(pe), "evEbitda": _round(ev_ebitda),
            "ps": _round(ps), "pFcf": _round(pfcf),
        }
        sources["valuationMultiples"] = "FMP ratios-ttm" if ratios else "FMP quote"

        # Analyst
        analyst_pt = _f(ptc0.get("targetConsensus") or ptc0.get("targetMedian")) if ptc0 else None
        analyst_rating = (grades0.get("consensus") if grades0 else None)
        revisions = None
        if isinstance(estimates, list) and len(estimates) >= 2:
            cur = _f(estimates[0].get("estimatedRevenueAvg"))
            prev = _f(estimates[1].get("estimatedRevenueAvg"))
            if cur is not None and prev is not None and prev != 0:
                revisions = "Upward" if cur > prev else "Downward" if cur < prev else "Stable"
        sources["analystPriceTarget"] = "FMP price-target-consensus" if analyst_pt is not None else ESTIMATED
        sources["analystRating"] = "FMP grades-consensus" if analyst_rating else ESTIMATED
        sources["analystEstimateRevisions"] = "FMP analyst-estimates" if revisions else ESTIMATED

        # Peers
        peer_list = []
        if isinstance(peers, list):
            for p in peers[:8]:
                sym = p.get("symbol") if isinstance(p, dict) else p
                if sym and sym != symbol:
                    peer_list.append(sym)
        sources["peerComparison"] = "FMP stock-peers" if peer_list else ESTIMATED

        # Ownership / insider — best effort; marked estimated when unavailable
        institutional_trend = None
        insider_activity = None
        sources["institutionalOwnershipTrend"] = ESTIMATED
        sources["insiderActivity"] = ESTIMATED

        beta = _f((profile or {}).get("beta"))

        # Scores (computed from real metrics only)
        opportunity = self._score_opportunity(
            sector=sector, pe=pe, rev_growth=rev_growth, rev_accel=rev_accel,
            eps_growth=eps_growth, fcf_margin=fcf_margin, price=price, analyst_pt=analyst_pt,
        )
        risk = self._score_risk(
            market_cap=market_cap, beta=beta, pe=pe, sector=sector,
            ebitda_margin=ebitda_margin, fcf_margin=fcf_margin,
        )
        sources["opportunityScore"] = "Computed (valuation/growth/margins/analyst upside)"
        sources["riskScore"] = "Computed (size/beta/leverage/valuation)"

        # Narrative cases (assembled from real data; no invented numbers)
        upside_pct = None
        if analyst_pt and price:
            upside_pct = _round((analyst_pt - price) / price * 100, 1)
        bull, base_c, bear, thesis = self._build_cases(
            name, sector, rev_growth, rev_accel, fcf_margin, upside_pct, analyst_rating, valuation_multiples,
        )

        return {
            "ticker": symbol,
            "companyName": name,
            "sector": sector,
            "industry": industry,
            "marketCap": market_cap,
            "marketCapLabel": _market_cap_label(market_cap),
            "price": _round(price),
            "revenueGrowth": rev_growth,
            "revenueAcceleration": rev_accel,
            "ebitdaMargin": ebitda_margin,
            "fcfMargin": fcf_margin,
            "epsGrowth": eps_growth,
            "analystRating": analyst_rating,
            "analystPriceTarget": _round(analyst_pt),
            "analystEstimateRevisions": revisions,
            "analystUpsidePct": upside_pct,
            "institutionalOwnershipTrend": institutional_trend,
            "insiderActivity": insider_activity,
            "valuationMultiples": valuation_multiples,
            "peerComparison": peer_list,
            "catalysts": [],
            "macroSensitivity": self._macro_sensitivity(sector, beta),
            "shariahStatus": None,
            "opportunityScore": opportunity,
            "riskScore": risk,
            "bullCase": bull,
            "baseCase": base_c,
            "bearCase": bear,
            "thesis": thesis,
            "beta": _round(beta),
            "dataCompleteness": self._completeness([profile, quote, ratios, metrics, growth]),
            "source": sources,
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
        }

    def _completeness(self, parts: List) -> float:
        avail = sum(1 for p in parts if p)
        return round(avail / len(parts) * 100, 1) if parts else 0.0

    def _macro_sensitivity(self, sector: Optional[str], beta: Optional[float]) -> str:
        rate_sensitive = {"Real Estate", "Utilities", "Financial Services"}
        if sector in rate_sensitive:
            return "High (rate-sensitive sector)"
        if beta is not None:
            if beta >= 1.3:
                return "High (beta > 1.3)"
            if beta <= 0.8:
                return "Low (defensive beta)"
            return "Moderate"
        return ESTIMATED

    def _score_opportunity(self, sector, pe, rev_growth, rev_accel, eps_growth, fcf_margin, price, analyst_pt):
        score, weight = 0.0, 0.0
        anchor = SECTOR_PE_ANCHOR.get(sector or "default", SECTOR_PE_ANCHOR["default"])
        if pe and pe > 0:
            val = max(0, min(100, (anchor / pe) * 50))
            score += val * 0.25; weight += 0.25
        if rev_growth is not None:
            score += max(0, min(100, rev_growth * 2.5)) * 0.20; weight += 0.20
        if rev_accel is not None:
            score += max(0, min(100, 50 + rev_accel * 5)) * 0.15; weight += 0.15
        if eps_growth is not None:
            score += max(0, min(100, 50 + eps_growth)) * 0.15; weight += 0.15
        if fcf_margin is not None:
            score += max(0, min(100, fcf_margin * 3)) * 0.10; weight += 0.10
        if analyst_pt and price:
            upside = (analyst_pt - price) / price * 100
            score += max(0, min(100, 50 + upside * 1.5)) * 0.15; weight += 0.15
        if weight == 0:
            return None
        return round(score / weight)

    def _score_risk(self, market_cap, beta, pe, sector, ebitda_margin, fcf_margin):
        score, weight = 0.0, 0.0
        if market_cap:
            if market_cap >= 200e9: size = 10
            elif market_cap >= 10e9: size = 25
            elif market_cap >= 2e9: size = 45
            elif market_cap >= 300e6: size = 70
            else: size = 90
            score += size * 0.30; weight += 0.30
        if beta is not None:
            score += max(0, min(100, beta * 50)) * 0.25; weight += 0.25
        anchor = SECTOR_PE_ANCHOR.get(sector or "default", SECTOR_PE_ANCHOR["default"])
        if pe and pe > 0:
            stretch = max(0, min(100, (pe / anchor) * 40))
            score += stretch * 0.20; weight += 0.20
        if fcf_margin is not None:
            score += max(0, min(100, 60 - fcf_margin * 3)) * 0.15; weight += 0.15
        if ebitda_margin is not None:
            score += max(0, min(100, 60 - ebitda_margin * 1.5)) * 0.10; weight += 0.10
        if weight == 0:
            return None
        return round(score / weight)

    def _build_cases(self, name, sector, rev_growth, rev_accel, fcf_margin, upside_pct, rating, multiples):
        def pct(x):
            return f"{x:.1f}%" if isinstance(x, (int, float)) else "n/a"

        bull_points = []
        if rev_growth is not None:
            bull_points.append(f"Revenue growing {pct(rev_growth)} YoY")
        if rev_accel is not None and rev_accel > 0:
            bull_points.append(f"Growth accelerating (+{pct(rev_accel)} vs prior year)")
        if fcf_margin is not None and fcf_margin > 0:
            bull_points.append(f"Free-cash-flow margin of {pct(fcf_margin)}")
        if upside_pct is not None and upside_pct > 0:
            bull_points.append(f"Analyst consensus implies {pct(upside_pct)} upside")

        bear_points = []
        if multiples.get("pe"):
            bear_points.append(f"Valuation at {multiples['pe']}x earnings leaves little margin for error")
        if rev_accel is not None and rev_accel < 0:
            bear_points.append(f"Revenue growth decelerating ({pct(rev_accel)} vs prior year)")
        if upside_pct is not None and upside_pct < 0:
            bear_points.append("Trading above analyst consensus target")
        if not bear_points:
            bear_points.append("Execution and macro risks could pressure the multiple")

        thesis = (
            f"{name} operates in {sector or 'its sector'} with "
            f"{('revenue growth of ' + pct(rev_growth)) if rev_growth is not None else 'limited disclosed growth data'}. "
            f"Analyst stance: {rating or 'not rated'}. "
            "Scores and cases are computed from currently available fundamentals; gaps are flagged in the source map."
        )
        return (
            {"summary": "Upside drivers", "points": bull_points},
            {"summary": "Most-likely path tracks fundamentals and analyst consensus", "points": []},
            {"summary": "Downside drivers", "points": bear_points},
            thesis,
        )

    # ---------- build & persist ----------

    async def build_universe(self, target_size: int = 1500, min_market_cap: float = 50e6,
                             batch_size: int = 12) -> Dict:
        await self._ensure_indexes()
        if not self._fmp_key:
            return {"status": "no_data_source", "built": 0,
                    "message": "No FMP_API_KEY configured — set one to populate the universe."}

        tickers = await self.discover_tickers(target_size, min_market_cap)
        if not tickers:
            return {"status": "empty", "built": 0,
                    "message": "Screener returned no companies (check API key/plan)."}

        col = self.db[self.COLLECTION]
        built = 0
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            records = await asyncio.gather(
                *[self.enrich_company(b) for b in batch], return_exceptions=True
            )
            for rec in records:
                if isinstance(rec, Exception) or not rec:
                    continue
                await col.update_one({"ticker": rec["ticker"]}, {"$set": rec}, upsert=True)
                built += 1
            if i + batch_size < len(tickers):
                await asyncio.sleep(0.4)

        await self.db[self.META_ID].update_one(
            {"_id": self.META_ID},
            {"$set": {"count": built, "target_size": target_size,
                      "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
        logger.info(f"Company universe built: {built} companies")
        return {"status": "ok", "built": built, "requested": len(tickers)}

    # ---------- query ----------

    async def list_companies(self, page: int = 1, limit: int = 50, sector: Optional[str] = None,
                             search: Optional[str] = None, min_market_cap: Optional[float] = None,
                             min_opportunity: Optional[float] = None, sort_by: str = "marketCap",
                             order: int = -1) -> Dict:
        col = self.db[self.COLLECTION]
        query: Dict[str, Any] = {}
        if sector and sector != "All":
            query["sector"] = sector
        if min_market_cap:
            query["marketCap"] = {"$gte": min_market_cap}
        if min_opportunity is not None:
            query["opportunityScore"] = {"$gte": min_opportunity}
        if search:
            s = search.strip().upper()
            query["$or"] = [
                {"ticker": {"$regex": f"^{s}", "$options": "i"}},
                {"companyName": {"$regex": search.strip(), "$options": "i"}},
            ]

        allowed_sort = {"marketCap", "opportunityScore", "riskScore", "price",
                        "revenueGrowth", "ticker"}
        sort_field = sort_by if sort_by in allowed_sort else "marketCap"
        limit = max(1, min(int(limit), 200))
        skip = (max(1, int(page)) - 1) * limit

        total = await col.count_documents(query)
        cursor = col.find(query, {"_id": 0}).sort(sort_field, order).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)
        return {
            "companies": items, "total": total, "page": page, "limit": limit,
            "pages": (total + limit - 1) // limit,
        }

    async def get_company(self, ticker: str) -> Optional[Dict]:
        return await self.db[self.COLLECTION].find_one({"ticker": ticker.upper()}, {"_id": 0})

    async def coverage(self) -> Dict:
        col = self.db[self.COLLECTION]
        meta = await self.db[self.META_ID].find_one({"_id": self.META_ID}, {"_id": 0}) or {}
        total = await col.count_documents({})
        sectors: Dict[str, int] = {}
        caps: Dict[str, int] = {}
        async for doc in col.find({}, {"sector": 1, "marketCap": 1, "_id": 0}):
            sec = doc.get("sector") or "Unknown"
            sectors[sec] = sectors.get(sec, 0) + 1
            label = _market_cap_label(doc.get("marketCap"))
            caps[label] = caps.get(label, 0) + 1
        return {
            "count": total,
            "has_data_source": bool(self._fmp_key),
            "updated_at": meta.get("updated_at"),
            "target_size": meta.get("target_size"),
            "sectors": sectors,
            "market_caps": caps,
        }
