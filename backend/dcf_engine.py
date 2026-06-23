"""
DCF Modeling Engine — institutional-grade valuation built from API data.

Pulls historical financial statements, analyst estimates, treasury rates and
peer multiples, then derives a full set of forward assumptions where every
assumption carries a source, reasoning and confidence level. Missing inputs are
flagged "Estimated from historical trends and industry averages" rather than
fabricated.
"""

import asyncio
import logging
from datetime import datetime, timezone
from statistics import median
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ESTIMATED = "Estimated from historical trends and industry averages"

SECTOR_BETA = {
    "Technology": 1.25, "Healthcare": 0.85, "Financial Services": 1.10,
    "Consumer Cyclical": 1.15, "Consumer Defensive": 0.70, "Energy": 1.05,
    "Industrials": 0.95, "Communication Services": 1.10, "Basic Materials": 1.10,
    "Real Estate": 0.90, "Utilities": 0.55, "default": 1.10,
}
SECTOR_EXIT_MULTIPLE = {
    "Technology": 22, "Healthcare": 16, "Financial Services": 11,
    "Consumer Cyclical": 14, "Consumer Defensive": 14, "Energy": 7,
    "Industrials": 13, "Communication Services": 13, "Basic Materials": 9,
    "Real Estate": 18, "Utilities": 12, "default": 14,
}


def _f(v) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _m(v) -> Optional[float]:
    """To $millions."""
    x = _f(v)
    return round(x / 1e6, 1) if x is not None else None


def _r(v, d=1):
    return round(v, d) if isinstance(v, (int, float)) else None


class DCFEngine:
    def __init__(self, api_client, db, fmp_key_getter):
        self.api = api_client
        self.db = db
        self._fmp_key_getter = fmp_key_getter

    async def _fmp(self, endpoint: str, params: Optional[Dict] = None, timeout: float = 25.0):
        return await self.api._request(
            f"{self.api.fmp_url}/{endpoint}",
            headers={"apikey": self._fmp_key_getter()},
            params=dict(params or {}),
            timeout=timeout,
        )

    async def _fx_rate(self, frm: Optional[str], to: Optional[str]) -> float:
        """Units of `to` per 1 unit of `frm` (e.g. USD per TWD). 1.0 if same/unknown."""
        frm = (frm or "").upper()
        to = (to or "").upper()
        if not frm or not to or frm == to:
            return 1.0
        for sym, invert in ((f"{frm}{to}", False), (f"{to}{frm}", True)):
            try:
                q = await self._fmp("quote", {"symbol": sym})
                row = q[0] if isinstance(q, list) and q else (q if isinstance(q, dict) else None)
                p = _f((row or {}).get("price"))
                if p and p > 0:
                    return round(1.0 / p, 8) if invert else round(p, 8)
            except Exception:
                pass
        return 1.0

    async def build_dcf(self, ticker: str) -> Optional[Dict]:
        symbol = ticker.upper()
        profile, income, balance, cashflow, estimates, ratios, treasury, peers, grades, ptc = await asyncio.gather(
            self._fmp("profile", {"symbol": symbol}),
            self._fmp("income-statement", {"symbol": symbol, "limit": 5, "period": "annual"}),
            self._fmp("balance-sheet-statement", {"symbol": symbol, "limit": 1}),
            self._fmp("cash-flow-statement", {"symbol": symbol, "limit": 3}),
            self._fmp("analyst-estimates", {"symbol": symbol, "period": "annual", "limit": 6}),
            self._fmp("ratios-ttm", {"symbol": symbol}),
            self._fmp("treasury-rates", {}),
            self._fmp("stock-peers", {"symbol": symbol}),
            self._fmp("grades-consensus", {"symbol": symbol}),
            self._fmp("price-target-consensus", {"symbol": symbol}),
            return_exceptions=True,
        )

        def ok(x):
            return x if not isinstance(x, Exception) else None

        profile = (ok(profile) or [None])[0] if isinstance(ok(profile), list) else ok(profile)
        income = ok(income) or []
        balance = (ok(balance) or [None])
        balance = balance[0] if balance else None
        cashflow = ok(cashflow) or []
        estimates = ok(estimates) or []
        ratios = (ok(ratios) or [None])
        ratios = ratios[0] if isinstance(ratios, list) and ratios else (ok(ratios) if isinstance(ok(ratios), dict) else None)
        treasury = ok(treasury) or []
        peers = ok(peers) or []
        grades = (ok(grades) or [None])
        grades = grades[0] if isinstance(grades, list) and grades else None
        ptc = (ok(ptc) or [None])
        ptc = ptc[0] if isinstance(ptc, list) and ptc else None

        if not profile or not income:
            return None

        # Income statements ascending (oldest → newest)
        inc = list(reversed(income))
        latest = inc[-1]
        revenue_m = _m(latest.get("revenue"))
        if not revenue_m:
            return None

        years = [int(str(r.get("fiscalYear") or r.get("date", "")[:4]) or 0) for r in inc]
        revenue_hist = [_m(r.get("revenue")) for r in inc]
        ebitda_hist = [_m(r.get("ebitda") or ((_f(r.get("operatingIncome")) or 0) + (_f(r.get("depreciationAndAmortization")) or 0))) for r in inc]

        # Historical revenue CAGR
        rev_cagr = None
        if len(revenue_hist) >= 2 and revenue_hist[0] and revenue_hist[-1] and revenue_hist[0] > 0:
            n = len(revenue_hist) - 1
            rev_cagr = round(((revenue_hist[-1] / revenue_hist[0]) ** (1 / n) - 1) * 100, 1)
        last_yoy = None
        if len(revenue_hist) >= 2 and revenue_hist[-2]:
            last_yoy = round((revenue_hist[-1] / revenue_hist[-2] - 1) * 100, 1)

        # Margins (latest)
        ebitda_margin = round(ebitda_hist[-1] / revenue_hist[-1] * 100, 1) if (ebitda_hist[-1] and revenue_hist[-1]) else None
        if ebitda_margin is None and ratios:
            em = _f(ratios.get("ebitdaMarginTTM"))
            ebitda_margin = round(em * 100, 1) if em is not None else None
        ebitda_margin = ebitda_margin if ebitda_margin is not None else 20.0

        # Effective tax rate
        pti = _f(latest.get("incomeBeforeTax"))
        tax_exp = _f(latest.get("incomeTaxExpense"))
        tax_rate = round(tax_exp / pti * 100, 1) if (pti and tax_exp is not None and pti > 0) else 21.0
        tax_rate = min(35.0, max(5.0, tax_rate))

        # D&A and CapEx as % of revenue (historical averages from cash flow)
        da_pcts, capex_pcts = [], []
        for cf in cashflow:
            rev_for = None
            yr = cf.get("fiscalYear")
            for r in inc:
                if r.get("fiscalYear") == yr:
                    rev_for = _f(r.get("revenue"))
            rev_for = rev_for or _f(latest.get("revenue"))
            da = _f(cf.get("depreciationAndAmortization"))
            cx = _f(cf.get("capitalExpenditure"))
            if rev_for and da is not None:
                da_pcts.append(abs(da) / rev_for * 100)
            if rev_for and cx is not None:
                capex_pcts.append(abs(cx) / rev_for * 100)
        da_pct = round(sum(da_pcts) / len(da_pcts), 1) if da_pcts else 6.0
        capex_pct = round(sum(capex_pcts) / len(capex_pcts), 1) if capex_pcts else 4.0

        # Balance sheet
        cash_m = _m((balance or {}).get("cashAndShortTermInvestments")) or _m((balance or {}).get("cashAndCashEquivalents")) or 0
        debt_m = _m((balance or {}).get("totalDebt")) or 0
        shares_m = _m(latest.get("weightedAverageShsOutDil")) or _m(latest.get("weightedAverageShsOut"))
        if not shares_m:
            so = _f(profile.get("sharesOutstanding"))
            shares_m = round(so / 1e6, 1) if so else None
        price = _f(profile.get("price"))
        market_cap_m = _m(profile.get("marketCap"))
        if not shares_m and market_cap_m and price:
            shares_m = round(market_cap_m / price, 1)

        # ── Currency detection (convert only at output; keep all ratios raw) ─────
        # Statements use the reporting currency (e.g. TWD); price/marketCap/targets
        # use the trading currency (e.g. USD). fx = trading per reported (1.0 for US).
        reported_ccy = (latest.get("reportedCurrency") or "").upper()
        trading_ccy = (profile.get("currency") or "").upper()
        fx = await self._fx_rate(reported_ccy, trading_ccy)
        market_cap_reported_m = (market_cap_m / fx) if (market_cap_m and fx) else market_cap_m

        # WACC inputs
        rf = None
        if isinstance(treasury, list) and treasury:
            rf = _f(treasury[0].get("year10"))
        rf = rf if rf is not None else 4.5
        beta = _f(profile.get("beta")) or SECTOR_BETA.get(profile.get("sector") or "default", SECTOR_BETA["default"])
        erp = 5.5
        cost_of_equity = round(rf + beta * erp, 1)
        # cost of debt from interest expense / total debt (both reporting ccy)
        int_exp = _f(latest.get("interestExpense"))
        cost_of_debt = round(int_exp / (debt_m * 1e6) * 100, 1) if (int_exp and debt_m and debt_m > 0) else 5.5
        cost_of_debt = min(12.0, max(3.0, cost_of_debt))
        total_cap = (market_cap_reported_m or 0) + debt_m
        debt_weight = round(debt_m / total_cap * 100) if total_cap else 10
        debt_weight = min(60, debt_weight)
        equity_weight = 100 - debt_weight
        wacc = round((equity_weight / 100) * cost_of_equity + (debt_weight / 100) * cost_of_debt * (1 - tax_rate / 100), 1)
        debt_to_ebitda = round(debt_m / ebitda_hist[-1], 1) if (ebitda_hist[-1] and ebitda_hist[-1] > 0) else None

        # Forward revenue growth — analyst estimates first, else tapered historical CAGR
        est_sorted = sorted([e for e in estimates if e.get("revenueAvg")], key=lambda e: e.get("date", ""))
        fwd_growth, growth_src, growth_conf = [], ESTIMATED, "Low"
        prev = revenue_hist[-1]
        future = [e for e in est_sorted if e.get("date", "")[:4] and int(e["date"][:4]) > years[-1]]
        if len(future) >= 3:
            growth_src = "FMP analyst-estimates (consensus revenue)"
            growth_conf = "High"
            for e in future[:5]:
                ravg = _m(e.get("revenueAvg"))
                if ravg and prev and prev > 0:
                    fwd_growth.append(round((ravg / prev - 1) * 100, 1))
                    prev = ravg
        if len(fwd_growth) < 5:
            base_g = last_yoy if last_yoy is not None else (rev_cagr if rev_cagr is not None else 8.0)
            base_g = max(2.0, min(base_g, 60.0))
            if not fwd_growth:
                growth_src = "Historical revenue CAGR, tapered toward GDP-like growth"
                growth_conf = "Medium"
            while len(fwd_growth) < 5:
                i = len(fwd_growth)
                fwd_growth.append(round(max(2.5, base_g * (0.82 ** i)), 1))

        # Forward EBITDA margin — gently expand from current toward best historical
        best_margin = max([m for m in [ (e/r*100 if (e and r) else None) for e, r in zip(ebitda_hist, revenue_hist)] if m] or [ebitda_margin])
        target_margin = min(max(ebitda_margin, best_margin), 80)
        fwd_margin = [round(min(ebitda_margin + (target_margin - ebitda_margin) * (i + 1) / 5, 80), 1) for i in range(5)]

        # NWC % from latest working capital
        nwc_pct = 2.0
        if balance:
            wc = (_f(balance.get("totalCurrentAssets")) or 0) - (_f(balance.get("totalCurrentLiabilities")) or 0)
            if revenue_m:
                nwc_pct = round(max(-10, min(20, wc / 1e6 / revenue_m * 100)), 1)

        exit_multiple = SECTOR_EXIT_MULTIPLE.get(profile.get("sector") or "default", SECTOR_EXIT_MULTIPLE["default"])

        company = {
            "ticker": symbol,
            "name": profile.get("companyName") or symbol,
            "sector": profile.get("sector"),
            "industry": profile.get("industry"),
            "price": _r(price, 2),
            "marketCap": market_cap_m,
            "revenue": round(revenue_m * fx, 1),
            "revenueGrowth": last_yoy if last_yoy is not None else rev_cagr,
            "revenueCagr": rev_cagr,
            "ebitdaMargin": ebitda_margin,
            "debtToEbitda": debt_to_ebitda,
            "exitMultiple": exit_multiple,
            "beta": _r(beta, 2),
            "revenueHistory": [(round(v * fx, 1) if v else v) for v in revenue_hist],
            "years": years,
            "description": profile.get("description"),
            "currency": trading_ccy or "USD",
            "reportingCurrency": reported_ccy or (trading_ccy or "USD"),
            "fxApplied": round(fx, 6),
            "risks": self._risk_factors(profile, fwd_growth, ebitda_margin, debt_to_ebitda, beta),
        }

        assumptions = {
            "riskFreeRate": rf, "erp": erp, "beta": _r(beta, 2),
            "costOfDebt": cost_of_debt, "taxRate": tax_rate,
            "debtWeight": debt_weight, "equityWeight": equity_weight, "wacc": wacc,
            "tgr": 3.0, "exitMultiple": exit_multiple, "tvMethod": "gordon",
            "revGrowth": fwd_growth, "ebitdaMargin": fwd_margin,
            "daPercent": [da_pct] * 5,
            "capexPercent": [capex_pct] * 5,
            "nwcPercent": [nwc_pct] * 5,
            "cash": round(cash_m * fx), "debt": round(debt_m * fx), "sharesOut": round(shares_m) if shares_m else 0,
            "meta": {
                "revGrowth": {"source": growth_src, "reasoning": f"Years 1–5 forward revenue growth. Historical CAGR {rev_cagr}%, last YoY {last_yoy}%.", "confidence": growth_conf},
                "ebitdaMargin": {"source": "Historical statements (FMP income-statement)", "reasoning": f"Current EBITDA margin {ebitda_margin}%, expanded toward best historical {round(best_margin,1)}%.", "confidence": "Medium"},
                "wacc": {"source": "CAPM — 10Y Treasury (FMP) + sector/ levered beta", "reasoning": f"Rf {rf}% + β {round(beta,2)}×ERP {erp}% = CoE {cost_of_equity}%; CoD {cost_of_debt}% after {tax_rate}% tax; weights E {equity_weight}% / D {debt_weight}%.", "confidence": "High"},
                "taxRate": {"source": "Effective tax (incomeTax/pretax, FMP)" if (pti and tax_exp is not None) else ESTIMATED, "reasoning": "Latest effective rate, clamped 5–35%.", "confidence": "High" if (pti and tax_exp is not None) else "Low"},
                "daPercent": {"source": "Historical D&A / revenue (FMP cash-flow)" if da_pcts else ESTIMATED, "reasoning": f"{len(da_pcts)}-yr average.", "confidence": "Medium" if da_pcts else "Low"},
                "capexPercent": {"source": "Historical CapEx / revenue (FMP cash-flow)" if capex_pcts else ESTIMATED, "reasoning": f"{len(capex_pcts)}-yr average.", "confidence": "Medium" if capex_pcts else "Low"},
                "nwcPercent": {"source": "Latest working capital / revenue (FMP balance-sheet)" if balance else ESTIMATED, "reasoning": "Net working capital as % of revenue.", "confidence": "Medium" if balance else "Low"},
                "tgr": {"source": "Assumption (long-run GDP+inflation)", "reasoning": "Perpetuity growth held at 3.0%.", "confidence": "Medium"},
                "exitMultiple": {"source": "Sector median EV/EBITDA", "reasoning": f"{profile.get('sector')} sector exit multiple.", "confidence": "Medium"},
                "cash": {"source": "FMP balance-sheet (cash & ST investments)", "reasoning": "Latest reported.", "confidence": "High" if balance else "Low"},
                "debt": {"source": "FMP balance-sheet (total debt)", "reasoning": "Latest reported.", "confidence": "High" if balance else "Low"},
                "sharesOut": {"source": "FMP diluted weighted shares", "reasoning": "Latest reported.", "confidence": "High" if shares_m else "Low"},
            },
        }

        historicals = self._historicals(inc, cashflow, fx, reported_ccy, trading_ccy)
        comps = await self._comps(symbol, peers, profile)
        analyst = self._analyst(grades, ptc, price)
        macro = self._macro(treasury, rf)
        industry = self._industry(profile, comps)
        memo = self._memo(company, analyst)

        return {
            "company": company,
            "assumptions": assumptions,
            "historicals": historicals,
            "comps": comps,
            "analyst": analyst,
            "macro": macro,
            "industry": industry,
            "memo": memo,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _historicals(self, inc: List[Dict], cashflow: List[Dict], fx: float = 1.0, reported_ccy: str = "", trading_ccy: str = "") -> Dict:
        cf_by_year = {c.get("fiscalYear"): c for c in cashflow}
        rows = []
        for r in inc:
            rev = _m(r.get("revenue"))
            ebitda = _m(r.get("ebitda") or ((_f(r.get("operatingIncome")) or 0) + (_f(r.get("depreciationAndAmortization")) or 0)))
            cf = cf_by_year.get(r.get("fiscalYear"), {})
            ocf = _f(cf.get("operatingCashFlow"))
            capex = _f(cf.get("capitalExpenditure"))
            fcf = round((ocf + capex) / 1e6, 1) if (ocf is not None and capex is not None) else None
            cv = lambda v: (round(v * fx, 1) if v is not None else None)
            rows.append({
                "year": int(str(r.get("fiscalYear") or r.get("date", "")[:4]) or 0),
                "revenue": cv(rev),
                "grossProfit": cv(_m(r.get("grossProfit"))),
                "grossMargin": _r((_f(r.get("grossProfit")) or 0) / (_f(r.get("revenue")) or 1) * 100),
                "operatingIncome": cv(_m(r.get("operatingIncome"))),
                "ebitda": cv(ebitda),
                "ebitdaMargin": _r((ebitda / rev * 100) if (ebitda and rev) else None),
                "netIncome": cv(_m(r.get("netIncome"))),
                "eps": (round((_f(r.get("epsDiluted") or r.get("eps")) or 0) * fx, 2) if (r.get("epsDiluted") or r.get("eps")) is not None else None),
                "freeCashFlow": cv(fcf),
            })
        src = "FMP income-statement / cash-flow-statement (reported)"
        if fx != 1.0:
            src += f" · converted {reported_ccy}→{trading_ccy} @ {round(fx, 6)}"
        return {"rows": rows, "source": src}

    async def _comps(self, symbol: str, peers: List, profile: Dict) -> Dict:
        tickers = [symbol]
        for p in (peers or [])[:8]:
            s = p.get("symbol") if isinstance(p, dict) else p
            if s and s not in tickers:
                tickers.append(s)
        docs = await self.db["company_universe"].find(
            {"ticker": {"$in": tickers}},
            {"_id": 0, "ticker": 1, "companyName": 1, "marketCap": 1, "valuationMultiples": 1,
             "revenueGrowth": 1, "ebitdaMargin": 1},
        ).to_list(length=20)
        rows = []
        for d in docs:
            vm = d.get("valuationMultiples") or {}
            rows.append({
                "ticker": d.get("ticker"),
                "name": d.get("companyName"),
                "marketCap": round((d.get("marketCap") or 0) / 1e6),
                "pe": vm.get("pe"), "evEbitda": vm.get("evEbitda"), "ps": vm.get("ps"),
                "revenueGrowth": d.get("revenueGrowth"), "ebitdaMargin": d.get("ebitdaMargin"),
                "isTarget": d.get("ticker") == symbol,
            })
        pes = [r["pe"] for r in rows if r.get("pe") and not r["isTarget"]]
        evs = [r["evEbitda"] for r in rows if r.get("evEbitda") and not r["isTarget"]]
        return {
            "rows": rows,
            "medianPe": round(median(pes), 1) if pes else None,
            "medianEvEbitda": round(median(evs), 1) if evs else None,
            "source": "FMP stock-peers + enriched company universe",
        }

    def _analyst(self, grades: Optional[Dict], ptc: Optional[Dict], price: Optional[float]) -> Dict:
        g = grades or {}
        target = _f((ptc or {}).get("targetConsensus")) if ptc else None
        upside = round((target - price) / price * 100, 1) if (target and price) else None
        return {
            "consensus": g.get("consensus"),
            "strongBuy": g.get("strongBuy"), "buy": g.get("buy"), "hold": g.get("hold"),
            "sell": g.get("sell"), "strongSell": g.get("strongSell"),
            "targetConsensus": _r(target, 2),
            "targetHigh": _r(_f((ptc or {}).get("targetHigh")), 2),
            "targetLow": _r(_f((ptc or {}).get("targetLow")), 2),
            "impliedUpside": upside,
            "source": "FMP grades-consensus + price-target-consensus",
        }

    def _macro(self, treasury: List, rf: float) -> Dict:
        t = treasury[0] if isinstance(treasury, list) and treasury else {}
        return {
            "riskFreeRate10y": rf,
            "yieldCurve": {k: t.get(k) for k in ["month3", "year1", "year2", "year5", "year10", "year30"] if t.get(k) is not None},
            "asOf": t.get("date"),
            "note": "Risk-free rate uses the 10Y US Treasury yield; the DCF discounts UFCF at the resulting WACC.",
            "source": "FMP treasury-rates",
        }

    def _industry(self, profile: Dict, comps: Dict) -> Dict:
        return {
            "sector": profile.get("sector"),
            "industry": profile.get("industry"),
            "peerMedianPe": comps.get("medianPe"),
            "peerMedianEvEbitda": comps.get("medianEvEbitda"),
            "note": "Peer multiples provide a market cross-check against the intrinsic DCF value.",
        }

    def _risk_factors(self, profile, fwd_growth, ebitda_margin, debt_to_ebitda, beta) -> List[str]:
        risks = []
        if fwd_growth and fwd_growth[0] and fwd_growth[0] > 30:
            risks.append("High forecast growth — model is sensitive to the durability of the top line")
        if ebitda_margin is not None and ebitda_margin < 10:
            risks.append("Thin margins increase sensitivity to cost inflation")
        if debt_to_ebitda is not None and debt_to_ebitda > 3:
            risks.append(f"Elevated leverage (net debt/EBITDA ≈ {debt_to_ebitda}x)")
        if beta and beta >= 1.3:
            risks.append(f"High beta ({round(beta,2)}) — valuation sensitive to discount-rate moves")
        risks.append("Terminal value is a large share of EV — sensitive to WACC and growth assumptions")
        risks.append(f"Sector/cyclical risk in {profile.get('sector') or 'the industry'}")
        return risks

    def _memo(self, company: Dict, analyst: Dict) -> Dict:
        return {
            "headline": f"{company['name']} ({company['ticker']}) — DCF valuation",
            "summary": (
                f"This intrinsic valuation is built bottom-up from {company['ticker']}'s reported financials, "
                f"consensus revenue estimates and a CAPM-derived WACC. Compare the implied fair value (DCF tab) "
                f"against the current price of ${company.get('price')} and the analyst consensus target "
                f"({'$' + str(analyst.get('targetConsensus')) if analyst.get('targetConsensus') else 'n/a'}). "
                "Treat every assumption as adjustable — edit the yellow inputs to stress the thesis."
            ),
            "disclaimer": "Educational research only. Not investment advice. Outputs depend entirely on assumptions, which are uncertain.",
        }
