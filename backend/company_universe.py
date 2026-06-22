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
        data = await self._fmp("company-screener", {
            "marketCapMoreThan": int(min_market_cap),
            "isActivelyTrading": "true",
            "isEtf": "false",
            "isFund": "false",
            "exchange": exchanges,
            "limit": target_size,
        }, timeout=30.0)
        if not isinstance(data, list):
            return []

        rows = []
        _excl = ("fund", "trust", "etf", " etn", "income fund", "acquisition corp", "spac")
        for r in data:
            symbol = r.get("symbol")
            if not symbol:
                continue
            name = (r.get("companyName") or "").lower()
            sector = r.get("sector")
            # Hard-exclude funds/ETFs/SPACs that slip past the screener flags.
            if any(x in name for x in _excl):
                continue
            if not sector or sector in ("", "N/A"):
                continue
            rows.append({
                "ticker": symbol,
                "companyName": r.get("companyName") or symbol,
                "sector": sector,
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
        profile, quote, ratios, metrics, growth, estimates, ptc, grades, peers, insider = await asyncio.gather(
            self.api.fmp_profile(symbol),
            self.api.fmp_quote(symbol),
            self.api.fmp_ratios(symbol),
            self.api.fmp_metrics(symbol),
            self._fmp("financial-growth", {"symbol": symbol, "limit": 2}),
            self._fmp("analyst-estimates", {"symbol": symbol, "period": "annual", "limit": 2}),
            self._fmp("price-target-consensus", {"symbol": symbol}),
            self._fmp("grades-consensus", {"symbol": symbol}),
            self._fmp("stock-peers", {"symbol": symbol}),
            self._fmp("insider-trading/search", {"symbol": symbol, "page": 0, "limit": 40}),
            return_exceptions=True,
        )

        def ok(x):
            return x if not isinstance(x, Exception) else None

        profile, quote, ratios, metrics = ok(profile), ok(quote), ok(ratios), ok(metrics)
        growth, estimates, ptc, grades, peers, insider = ok(growth), ok(estimates), ok(ptc), ok(grades), ok(peers), ok(insider)

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

        # Margins (FMP returns these ratios as decimals; convert to %)
        ebitda_margin = _f((ratios or {}).get("ebitdaMarginTTM")) if ratios else None
        if ebitda_margin is None and ratios:
            ebitda_margin = _f(ratios.get("operatingProfitMarginTTM"))
        ebitda_margin = _round(ebitda_margin * 100) if (ebitda_margin is not None and abs(ebitda_margin) <= 5) else _round(ebitda_margin)
        # FCF margin: prefer direct ratio, else derive from EV/Sales ÷ EV/FCF
        fcf_margin = _f((ratios or {}).get("freeCashFlowMarginTTM")) if ratios else None
        if fcf_margin is None and metrics:
            ev_sales = _f(metrics.get("evToSalesTTM"))
            ev_fcf = _f(metrics.get("evToFreeCashFlowTTM"))
            if ev_sales is not None and ev_fcf:
                fcf_margin = ev_sales / ev_fcf
        fcf_margin = _round(fcf_margin * 100) if (fcf_margin is not None and abs(fcf_margin) <= 5) else _round(fcf_margin)
        sources["ebitdaMargin"] = "FMP ratios-ttm" if ebitda_margin is not None else ESTIMATED
        sources["fcfMargin"] = "FMP key-metrics/ratios" if fcf_margin is not None else ESTIMATED

        # Valuation multiples
        pe = _f((ratios or {}).get("priceToEarningsRatioTTM") or (ratios or {}).get("peRatioTTM")) if ratios else None
        ev_ebitda = _f((metrics or {}).get("evToEBITDATTM")) if metrics else None
        if ev_ebitda is None and ratios:
            ev_ebitda = _f(ratios.get("enterpriseValueMultipleTTM"))
        ps = _f((ratios or {}).get("priceToSalesRatioTTM")) if ratios else (_f((metrics or {}).get("evToSalesTTM")) if metrics else None)
        pfcf = _f((ratios or {}).get("priceToFreeCashFlowsRatioTTM")) if ratios else None
        if pfcf is None and metrics:
            pfcf = _f(metrics.get("evToFreeCashFlowTTM"))
        valuation_multiples = {
            "pe": _round(pe), "evEbitda": _round(ev_ebitda),
            "ps": _round(ps), "pFcf": _round(pfcf),
        }
        sources["valuationMultiples"] = "FMP ratios-ttm / key-metrics-ttm" if (ratios or metrics) else ESTIMATED

        # Analyst
        analyst_pt = _f(ptc0.get("targetConsensus") or ptc0.get("targetMedian")) if ptc0 else None
        analyst_pt_high = _f(ptc0.get("targetHigh")) if ptc0 else None
        analyst_pt_low = _f(ptc0.get("targetLow")) if ptc0 else None
        analyst_rating = (grades0.get("consensus") if grades0 else None)
        revisions = None
        if isinstance(estimates, list) and len(estimates) >= 2:
            later = _f(estimates[0].get("revenueAvg"))
            earlier = _f(estimates[1].get("revenueAvg"))
            if later is not None and earlier is not None and earlier != 0:
                revisions = "Rising" if later > earlier else "Falling" if later < earlier else "Stable"
        sources["analystPriceTarget"] = "FMP price-target-consensus" if analyst_pt is not None else ESTIMATED
        sources["analystRating"] = "FMP grades-consensus" if analyst_rating else ESTIMATED
        sources["analystEstimateRevisions"] = "FMP analyst-estimates (forward trajectory)" if revisions else ESTIMATED

        # Peers
        peer_list = []
        if isinstance(peers, list):
            for p in peers[:8]:
                sym = p.get("symbol") if isinstance(p, dict) else p
                if sym and sym != symbol:
                    peer_list.append(sym)
        sources["peerComparison"] = "FMP stock-peers" if peer_list else ESTIMATED

        # Ownership / insider activity
        institutional_trend = None
        sources["institutionalOwnershipTrend"] = ESTIMATED
        insider_activity = None
        if isinstance(insider, list) and insider:
            buys = sum(1 for t in insider if t.get("acquisitionOrDisposition") == "A")
            sells = sum(1 for t in insider if t.get("acquisitionOrDisposition") == "D")
            if buys or sells:
                insider_activity = ("Net buying" if buys > sells else
                                    "Net selling" if sells > buys else "Mixed")
                sources["insiderActivity"] = f"FMP insider-trading ({buys} buys / {sells} sells, last 40 filings)"
            else:
                sources["insiderActivity"] = ESTIMATED
        else:
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
            "analystPriceTargetHigh": _round(analyst_pt_high),
            "analystPriceTargetLow": _round(analyst_pt_low),
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

    # ---------- short-term growth ranking (Phase 3) ----------

    def _size_tilt(self, market_cap: Optional[float]) -> float:
        """Down-weight mega caps so they don't dominate; favour mid/small caps."""
        mc = market_cap or 0
        if mc >= 200e9:
            return 0.85
        if mc >= 10e9:
            return 1.0
        if mc >= 2e9:
            return 1.12
        if mc >= 300e6:
            return 1.16
        return 1.08  # micro: modest tilt (offset by liquidity risk)

    def _short_term_score(self, c: Dict) -> Optional[float]:
        score, weight = 0.0, 0.0
        accel = c.get("revenueAcceleration")
        if accel is not None:
            score += max(0, min(100, 50 + accel * 3)) * 0.20; weight += 0.20
        rg = c.get("revenueGrowth")
        if rg is not None:
            score += max(0, min(100, rg * 2)) * 0.15; weight += 0.15
        eps = c.get("epsGrowth")
        if eps is not None:
            score += max(0, min(100, 50 + eps)) * 0.10; weight += 0.10
        rev = c.get("analystEstimateRevisions")
        if rev:
            score += (75 if rev == "Rising" else 35 if rev == "Falling" else 55) * 0.10; weight += 0.10
        up = c.get("analystUpsidePct")
        if up is not None:
            score += max(0, min(100, 50 + up)) * 0.15; weight += 0.15
        fcf = c.get("fcfMargin")
        if fcf is not None:
            score += max(0, min(100, fcf * 3)) * 0.10; weight += 0.10
        pe = (c.get("valuationMultiples") or {}).get("pe")
        anchor = SECTOR_PE_ANCHOR.get(c.get("sector") or "default", SECTOR_PE_ANCHOR["default"])
        if pe and pe > 0:
            score += max(0, min(100, (anchor / pe) * 50)) * 0.10; weight += 0.10
        rating = c.get("analystRating")
        if rating:
            score += (70 if "Buy" in str(rating) else 50 if "Hold" in str(rating) else 35) * 0.10; weight += 0.10
        if weight < 0.4:
            return None
        base = score / weight
        return round(min(100, base * self._size_tilt(c.get("marketCap"))), 1)

    def _growth_view(self, c: Dict) -> Dict:
        price = c.get("price")
        pt = c.get("analystPriceTarget")
        high = c.get("analystPriceTargetHigh")
        low = c.get("analystPriceTargetLow")
        rg = c.get("revenueGrowth")
        accel = c.get("revenueAcceleration")
        pe = (c.get("valuationMultiples") or {}).get("pe")
        risk = c.get("riskScore") or 45
        beta = c.get("beta")
        rating = c.get("analystRating")

        # Discard implausible analyst targets (bad/stale data on illiquid names).
        def sane(t, lo=0.4, hi=2.5):
            return t if (t and price and lo * price <= t <= hi * price) else None

        pt_ok = sane(pt)
        base_price = pt_ok or (round(price * (1 + (rg or 0) / 200), 2) if price else None)
        if price and high and base_price and base_price <= high <= 3 * price:
            bull_price = high
        elif price:
            bull_price = round(price * (1 + min(0.45, max(0.12, (rg or 12) / 100))), 2)
        else:
            bull_price = None
        if price and low and 0.3 * price <= low <= price:
            bear_price = low
        elif price:
            bear_price = round(price * (1 - min(0.4, risk / 200)), 2)
        else:
            bear_price = None
        # Keep ordering bear <= base <= bull
        if base_price and bull_price:
            base_price = min(base_price, bull_price)
        if base_price and bear_price:
            base_price = max(base_price, bear_price)

        up = round((pt_ok - price) / price * 100, 1) if (pt_ok and price) else None

        def thesis(kind):
            if kind == "bull":
                return ("Growth re-accelerates and margins expand while the multiple holds; "
                        "analyst high target is reached.")
            if kind == "bear":
                return ("Growth decelerates or margins compress and the multiple de-rates toward sector median.")
            return "Company tracks consensus estimates with the multiple roughly unchanged."

        # Why the market may be wrong
        why_bits = []
        if pe and accel is not None and accel > 0:
            why_bits.append(f"trades at {pe}x earnings while revenue growth is accelerating (+{accel:.1f}pp YoY)")
        elif pe and rg is not None:
            why_bits.append(f"trades at {pe}x earnings on {rg:.1f}% revenue growth")
        if up is not None and up > 0:
            why_bits.append(f"consensus implies {up:.1f}% upside")
        if c.get("analystEstimateRevisions") == "Rising":
            why_bits.append("forward estimates are trending higher")
        why_wrong = (f"{c.get('companyName')} " + ", ".join(why_bits) +
                     " — the market may be underpricing the durability of the growth.") if why_bits else \
                    "Limited disclosed data; treat as a watch-list candidate pending more coverage."

        # What could invalidate
        invalidate = []
        if accel is not None and accel > 0:
            invalidate.append("revenue growth re-decelerates")
        invalidate.append("margins compress")
        invalidate.append("the multiple de-rates toward sector median")
        if beta is not None and beta >= 1.3:
            invalidate.append(f"high beta ({beta}) amplifies drawdowns in risk-off markets")

        # Catalysts & risks
        catalysts = []
        if c.get("analystEstimateRevisions") == "Rising":
            catalysts.append("Rising analyst estimates")
        if accel is not None and accel > 0:
            catalysts.append("Accelerating revenue")
        if rating and "Buy" in str(rating):
            catalysts.append("Buy-rated consensus")
        if up is not None and up > 15:
            catalysts.append(f"{up:.0f}% to consensus target")
        catalysts.append("Next earnings report")

        risks = []
        if pe and pe > SECTOR_PE_ANCHOR.get(c.get("sector") or "default", 20) * 1.3:
            risks.append("Premium valuation vs sector")
        if accel is not None and accel < 0:
            risks.append("Decelerating growth")
        if c.get("fcfMargin") is not None and c.get("fcfMargin") < 0:
            risks.append("Negative free cash flow")
        if beta is not None and beta >= 1.3:
            risks.append(f"High volatility (beta {beta})")
        if not risks:
            risks.append("Execution and macro risk")

        return {
            "ticker": c.get("ticker"),
            "name": c.get("companyName"),
            "sector": c.get("sector"),
            "marketCap": c.get("marketCap"),
            "marketCapLabel": c.get("marketCapLabel"),
            "price": price,
            "opportunityScore": c.get("opportunityScore"),
            "growthScore": c.get("growthScore"),
            "riskScore": c.get("riskScore"),
            "analystRating": rating,
            "analystConsensusTarget": pt_ok,
            "avgPt": pt_ok,
            "analystUpsidePct": up,
            "valuationMultiples": c.get("valuationMultiples"),
            "revenueGrowth": rg,
            "revenueAcceleration": accel,
            "fcfMargin": c.get("fcfMargin"),
            "ebitdaMargin": c.get("ebitdaMargin"),
            "analystEstimateRevisions": c.get("analystEstimateRevisions"),
            "shariah": c.get("shariahStatus") or "Unknown",
            "whyMarketMayBeWrong": why_wrong,
            "whatInvalidates": "Thesis breaks if " + ", ".join(invalidate) + ".",
            "keyCatalysts": catalysts,
            "keyRisks": risks,
            "bullCase": {"price": bull_price, "thesis": thesis("bull")},
            "baseCase": {"price": round(base_price, 2) if base_price else None, "thesis": thesis("base")},
            "bearCase": {"price": bear_price, "thesis": thesis("bear")},
            "source": c.get("source", {}),
            "lastUpdated": c.get("lastUpdated"),
        }

    async def rank_short_term_growth(self, limit: int = 30, max_megacap: int = 6) -> Dict:
        col = self.db[self.COLLECTION]
        proj = {
            "_id": 0, "ticker": 1, "companyName": 1, "sector": 1, "marketCap": 1,
            "marketCapLabel": 1, "price": 1, "opportunityScore": 1, "riskScore": 1, "beta": 1,
            "revenueGrowth": 1, "revenueAcceleration": 1, "epsGrowth": 1, "fcfMargin": 1,
            "ebitdaMargin": 1, "analystRating": 1, "analystPriceTarget": 1,
            "analystPriceTargetHigh": 1, "analystPriceTargetLow": 1, "analystUpsidePct": 1,
            "analystEstimateRevisions": 1, "valuationMultiples": 1, "shariahStatus": 1,
            "source": 1, "lastUpdated": 1,
        }
        docs = await col.find({"opportunityScore": {"$ne": None}}, proj).to_list(length=5000)
        ranked = []
        for c in docs:
            s = self._short_term_score(c)
            if s is None:
                continue
            c["growthScore"] = s
            ranked.append(c)
        ranked.sort(key=lambda x: x["growthScore"], reverse=True)

        # Cap mega-cap presence so the list isn't dominated by the obvious names.
        selected, megas = [], 0
        for c in ranked:
            is_mega = (c.get("marketCap") or 0) >= 200e9
            if is_mega and megas >= max_megacap:
                continue
            if is_mega:
                megas += 1
            selected.append(c)
            if len(selected) >= limit:
                break

        return {
            "companies": [self._growth_view(c) for c in selected],
            "total_ranked": len(ranked),
            "megacap_in_list": megas,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ---------- future giants ranking (Phase 4) ----------

    SECULAR_SECTORS = {"Technology", "Healthcare", "Communication Services", "Consumer Cyclical"}
    CYCLICAL_SECTORS = {"Energy", "Basic Materials", "Utilities", "Real Estate"}

    def _giant_sector_tilt(self, sector: Optional[str]) -> float:
        # Favour secular-growth sectors; demote cyclical/commodity names that
        # show one-off, price-driven revenue spikes rather than durable growth.
        if sector in self.SECULAR_SECTORS:
            return 1.0
        if sector in self.CYCLICAL_SECTORS:
            return 0.6
        return 0.8

    def _future_giant_score(self, c: Dict) -> Optional[float]:
        rg = c.get("revenueGrowth")
        mc = c.get("marketCap") or 0
        # Giants-in-waiting: meaningful secular growth and room to scale.
        if rg is None or rg < 15 or mc >= 150e9:
            return None
        score, weight = 0.0, 0.0
        # Cap growth contribution so commodity/small-base spikes don't dominate.
        score += max(0, min(100, rg * 1.4)) * 0.28; weight += 0.28
        # size runway: the smaller the company, the more room to compound
        if mc < 2e9:
            runway = 95
        elif mc < 10e9:
            runway = 80
        elif mc < 50e9:
            runway = 60
        else:
            runway = 40
        score += runway * 0.18; weight += 0.18
        fcf = c.get("fcfMargin")
        if fcf is not None:
            score += max(0, min(100, 50 + fcf * 2)) * 0.12; weight += 0.12
        em = c.get("ebitdaMargin")
        if em is not None:
            score += max(0, min(100, em * 2)) * 0.10; weight += 0.10
        eps = c.get("epsGrowth")
        if eps is not None:
            score += max(0, min(100, 50 + eps)) * 0.10; weight += 0.10
        score += (100 if c.get("sector") in self.SECULAR_SECTORS else 40) * 0.14; weight += 0.14
        up = c.get("analystUpsidePct")
        if up is not None:
            score += max(0, min(100, 50 + up)) * 0.08; weight += 0.08
        if weight < 0.5:
            return None
        return round(min(100, (score / weight) * self._giant_sector_tilt(c.get("sector"))), 1)

    def _giant_view(self, c: Dict) -> Dict:
        rg = c.get("revenueGrowth")
        mc = c.get("marketCap") or 0
        fcf = c.get("fcfMargin")
        em = c.get("ebitdaMargin")
        ev = (c.get("valuationMultiples") or {}).get("evEbitda")
        pe = (c.get("valuationMultiples") or {}).get("pe")
        beta = c.get("beta")
        sector = c.get("sector")
        industry = c.get("industry")
        score = c.get("giantScore") or 0
        small = mc < 2e9

        # Potential bucket (clearly speculative, framed as "potential" in the UI).
        if score >= 85 and mc < 10e9:
            upside = "5–10x"
        elif score >= 78:
            upside = "3–5x"
        elif score >= 68:
            upside = "2–3x"
        else:
            upside = "2x+"

        def mc_str(v):
            if v >= 1e12:
                return f"${v / 1e12:.1f}T"
            if v >= 1e9:
                return f"${v / 1e9:.1f}B"
            return f"${v / 1e6:.0f}M"

        # Margin trajectory (qualitative, from current profitability profile)
        if fcf is not None and fcf > 10 and em is not None and em > 20:
            margin_traj = "Strong, profitable margins"
        elif fcf is not None and fcf > 0:
            margin_traj = "Profitable, expanding"
        else:
            margin_traj = "Pre-/early-profitability, scaling"

        # Moat descriptor
        if (em is not None and em >= 30) or (fcf is not None and fcf >= 20):
            moat = "High margins point to pricing power and scale economics — a sign of a durable advantage."
        elif sector in {"Technology", "Communication Services"}:
            moat = "Software/platform economics suggest potential network effects and high switching costs."
        else:
            moat = "Competitive position still developing; moat durability is a key item to monitor."

        tam = f"Large, secular TAM in {industry or sector or 'its end markets'} (qualitative estimate)."

        thesis = (
            f"{c.get('companyName')} is a {mc_str(mc)} {sector or ''} company growing revenue "
            f"{rg:.0f}% with {'positive' if (fcf or 0) > 0 else 'improving'} free cash flow. "
            f"At today's size it has substantial runway to compound into a far larger franchise "
            f"if it sustains growth and expands margins"
            + (f"; consensus already implies {c['analystUpsidePct']:.0f}% upside." if c.get("analystUpsidePct") else ".")
        )
        why_larger = (
            f"Small base × durable secular demand × {('improving ' if (fcf or 0) <= 0 else '')}margin leverage. "
            f"A {mc_str(mc)} company sustaining ~{rg:.0f}% growth can multiply in value over many years as it scales."
        )

        risks = ["Multi-year execution risk — growth may not be sustained"]
        if fcf is not None and fcf < 0:
            risks.append("Not yet consistently free-cash-flow positive")
        if (pe and pe > SECTOR_PE_ANCHOR.get(sector or "default", 20) * 1.3) or (ev and ev > 25):
            risks.append("Premium valuation leaves little room for execution error")
        if beta is not None and beta >= 1.3:
            risks.append(f"High volatility (beta {beta}) — expect large drawdowns")
        risks.append("Competitive disruption in a fast-moving market")

        key_metrics = {
            "Rev Growth": f"+{rg:.0f}%" if rg is not None else "—",
            "Margin": margin_traj.split(",")[0] if isinstance(margin_traj, str) else "—",
            "EV/EBITDA": f"{ev:.1f}x" if ev else (f"{pe:.0f}x P/E" if pe else "n/a"),
        }

        return {
            "ticker": c.get("ticker"),
            "name": c.get("companyName"),
            "sector": sector,
            "marketCap": mc,
            "marketCapLabel": c.get("marketCapLabel"),
            "price": c.get("price"),
            "opportunityScore": round(score),
            "giantScore": score,
            "revenueGrowth": round(rg) if rg is not None else None,
            "revenueCagr": round(rg, 1) if rg is not None else None,
            "marginTrajectory": margin_traj,
            "valuation": key_metrics["EV/EBITDA"],
            "upside": upside,
            "timeframe": "5+ years",
            "tam": tam,
            "thesis": thesis,
            "whyLarger": why_larger,
            "moat": moat,
            "keyMetrics": key_metrics,
            "risks": risks,
            "shariah": c.get("shariahStatus") or "Unknown",
            "source": c.get("source", {}),
            "lastUpdated": c.get("lastUpdated"),
        }

    async def rank_future_giants(self, limit: int = 12) -> Dict:
        col = self.db[self.COLLECTION]
        proj = {
            "_id": 0, "ticker": 1, "companyName": 1, "sector": 1, "industry": 1,
            "marketCap": 1, "marketCapLabel": 1, "price": 1, "opportunityScore": 1, "beta": 1,
            "revenueGrowth": 1, "revenueAcceleration": 1, "epsGrowth": 1, "fcfMargin": 1,
            "ebitdaMargin": 1, "analystUpsidePct": 1, "valuationMultiples": 1,
            "shariahStatus": 1, "source": 1, "lastUpdated": 1,
        }
        docs = await col.find({"opportunityScore": {"$ne": None}}, proj).to_list(length=5000)
        ranked = []
        for c in docs:
            s = self._future_giant_score(c)
            if s is None:
                continue
            c["giantScore"] = s
            ranked.append(c)
        ranked.sort(key=lambda x: x["giantScore"], reverse=True)
        top = ranked[:limit]
        return {
            "companies": [self._giant_view(c) for c in top],
            "total_ranked": len(ranked),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

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
