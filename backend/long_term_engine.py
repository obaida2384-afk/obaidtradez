"""
ObaidTradez Long-Term Investment Engine
Completely separate from day trading. Manages a portfolio across 3 buckets:
  - Core (40-60%): ETF-heavy, broad market exposure
  - Quality Growth (25-40%): Proven compounders, strong FCF & moats
  - Opportunistic Value (10-25%): Deep value, turnarounds
Features: concentration limits, staged buying (25% chunks), monthly/quarterly rebalancing.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ===================== MODELS =====================

class LTPosition(BaseModel):
    symbol: str
    name: str = ""
    bucket: str  # core, quality_growth, opportunistic_value
    asset_type: str = "stock"  # etf, stock
    shares: float = 0
    avg_cost: float = 0
    current_price: float = 0
    current_value: float = 0
    allocation_pct: float = 0
    pnl_pct: float = 0
    pnl_usd: float = 0
    stage: int = 0  # 0-4 (how many 25% chunks bought)
    max_stages: int = 4
    thesis: str = ""
    added_at: str = ""
    last_stage_at: str = ""
    last_rebalanced: str = ""
    status: str = "active"  # active, trimming, exiting, staged
    score: float = 0
    score_drivers: Dict = {}


class LTRecommendation(BaseModel):
    symbol: str
    name: str = ""
    action: str  # BUY, ADD, TRIM, SELL, HOLD, REBALANCE
    bucket: str = ""
    reason: str = ""
    priority: str = "medium"  # high, medium, low
    suggested_allocation_pct: float = 0
    current_allocation_pct: float = 0
    stage_info: str = ""
    score: float = 0
    asset_type: str = "stock"


class LTPortfolioSummary(BaseModel):
    total_value: float = 0
    total_cost: float = 0
    total_pnl_pct: float = 0
    total_pnl_usd: float = 0
    position_count: int = 0
    bucket_allocation: Dict = {}
    diversification_score: float = 0
    needs_rebalance: bool = False
    rebalance_reasons: List[str] = []
    last_rebalance_check: str = ""


# ===================== UNIVERSES =====================

# Core ETFs — broad market, low cost, high liquidity
CORE_ETFS = {
    "VOO": {"name": "Vanguard S&P 500", "category": "us_large_cap", "target_pct": 15},
    "VTI": {"name": "Vanguard Total Market", "category": "us_total", "target_pct": 10},
    "QQQ": {"name": "Invesco Nasdaq 100", "category": "us_tech", "target_pct": 10},
    "SCHD": {"name": "Schwab US Dividend", "category": "us_dividend", "target_pct": 8},
    "VEA": {"name": "Vanguard Intl Developed", "category": "intl_developed", "target_pct": 5},
    "VWO": {"name": "Vanguard Emerging Markets", "category": "intl_emerging", "target_pct": 3},
    "BND": {"name": "Vanguard Total Bond", "category": "us_bond", "target_pct": 5},
    "GLD": {"name": "SPDR Gold Trust", "category": "commodities", "target_pct": 2},
    "VNQ": {"name": "Vanguard Real Estate", "category": "real_estate", "target_pct": 2},
}

# Quality Growth candidates — proven compounders
QUALITY_GROWTH_UNIVERSE = {
    "AAPL": {"name": "Apple", "sector": "Technology"},
    "MSFT": {"name": "Microsoft", "sector": "Technology"},
    "GOOGL": {"name": "Alphabet", "sector": "Technology"},
    "AMZN": {"name": "Amazon", "sector": "Consumer"},
    "NVDA": {"name": "NVIDIA", "sector": "Technology"},
    "META": {"name": "Meta Platforms", "sector": "Technology"},
    "V": {"name": "Visa", "sector": "Financials"},
    "MA": {"name": "Mastercard", "sector": "Financials"},
    "UNH": {"name": "UnitedHealth", "sector": "Healthcare"},
    "JNJ": {"name": "Johnson & Johnson", "sector": "Healthcare"},
    "LLY": {"name": "Eli Lilly", "sector": "Healthcare"},
    "COST": {"name": "Costco", "sector": "Consumer"},
    "HD": {"name": "Home Depot", "sector": "Consumer"},
    "PG": {"name": "Procter & Gamble", "sector": "Consumer Staples"},
    "KO": {"name": "Coca-Cola", "sector": "Consumer Staples"},
    "PEP": {"name": "PepsiCo", "sector": "Consumer Staples"},
    "AVGO": {"name": "Broadcom", "sector": "Technology"},
    "CRM": {"name": "Salesforce", "sector": "Technology"},
    "ADBE": {"name": "Adobe", "sector": "Technology"},
    "TMO": {"name": "Thermo Fisher", "sector": "Healthcare"},
    "ACN": {"name": "Accenture", "sector": "Technology"},
    "NEE": {"name": "NextEra Energy", "sector": "Utilities"},
    "LIN": {"name": "Linde", "sector": "Materials"},
    "TXN": {"name": "Texas Instruments", "sector": "Technology"},
    "ISRG": {"name": "Intuitive Surgical", "sector": "Healthcare"},
}

# Value Universe — deeper value, higher risk/reward
VALUE_UNIVERSE = {
    "BRK-B": {"name": "Berkshire Hathaway B", "sector": "Financials"},
    "JPM": {"name": "JPMorgan Chase", "sector": "Financials"},
    "BAC": {"name": "Bank of America", "sector": "Financials"},
    "WFC": {"name": "Wells Fargo", "sector": "Financials"},
    "CVX": {"name": "Chevron", "sector": "Energy"},
    "XOM": {"name": "ExxonMobil", "sector": "Energy"},
    "BMY": {"name": "Bristol-Myers Squibb", "sector": "Healthcare"},
    "ABBV": {"name": "AbbVie", "sector": "Healthcare"},
    "INTC": {"name": "Intel", "sector": "Technology"},
    "T": {"name": "AT&T", "sector": "Telecom"},
    "VZ": {"name": "Verizon", "sector": "Telecom"},
    "PFE": {"name": "Pfizer", "sector": "Healthcare"},
    "MO": {"name": "Altria", "sector": "Consumer Staples"},
    "GM": {"name": "General Motors", "sector": "Industrials"},
    "F": {"name": "Ford", "sector": "Industrials"},
    "C": {"name": "Citigroup", "sector": "Financials"},
    "USB": {"name": "US Bancorp", "sector": "Financials"},
    "DOW": {"name": "Dow Inc", "sector": "Materials"},
    "MMM": {"name": "3M", "sector": "Industrials"},
    "PARA": {"name": "Paramount Global", "sector": "Communication"},
}


# ===================== BUCKET RULES =====================

BUCKET_RULES = {
    "core": {
        "label": "Core Holdings",
        "target_allocation_min": 40,
        "target_allocation_max": 60,
        "max_single_position_pct": 35,  # ETFs can be larger
        "min_single_position_pct": 2,
        "rebalance_frequency_days": 90,  # Quarterly
        "preferred_asset_type": "etf",
        "description": "ETF-heavy broad market exposure. Low turnover, quarterly rebalance.",
    },
    "quality_growth": {
        "label": "Quality Growth",
        "target_allocation_min": 25,
        "target_allocation_max": 40,
        "max_single_position_pct": 10,
        "min_single_position_pct": 2,
        "rebalance_frequency_days": 30,  # Monthly
        "preferred_asset_type": "stock",
        "description": "Proven compounders with strong FCF, moats, and consistent earnings.",
    },
    "opportunistic_value": {
        "label": "Opportunistic Value",
        "target_allocation_min": 10,
        "target_allocation_max": 25,
        "max_single_position_pct": 5,
        "min_single_position_pct": 1,
        "rebalance_frequency_days": 30,  # Monthly
        "preferred_asset_type": "stock",
        "description": "Deep value, turnarounds, contrarian bets. Smaller positions, higher conviction needed.",
    },
}


# ===================== ENGINE =====================

class LongTermInvestingEngine:
    """
    Manages a long-term investment portfolio with 3 buckets.
    Completely separate from the day trading engine.
    """

    def __init__(self, db):
        self.db = db
        self.collection = "lt_portfolio"
        self.log_collection = "lt_rebalance_log"

    # ---------- PORTFOLIO CRUD ----------

    async def get_positions(self) -> List[Dict]:
        cursor = self.db[self.collection].find({"status": {"$ne": "closed"}}, {"_id": 0})
        return await cursor.to_list(length=200)

    async def get_position(self, symbol: str) -> Optional[Dict]:
        return await self.db[self.collection].find_one(
            {"symbol": symbol.upper(), "status": {"$ne": "closed"}}, {"_id": 0}
        )

    async def upsert_position(self, position: Dict):
        symbol = position["symbol"].upper()
        position["symbol"] = symbol
        position["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self.db[self.collection].update_one(
            {"symbol": symbol}, {"$set": position}, upsert=True
        )
        return position

    async def close_position(self, symbol: str, reason: str = ""):
        now = datetime.now(timezone.utc).isoformat()
        await self.db[self.collection].update_one(
            {"symbol": symbol.upper()},
            {"$set": {"status": "closed", "closed_at": now, "close_reason": reason}}
        )

    # ---------- PORTFOLIO SUMMARY ----------

    async def get_portfolio_summary(self, price_lookup: Dict = None) -> Dict:
        """Build full portfolio summary with live prices."""
        positions = await self.get_positions()
        if not positions:
            return {
                "summary": LTPortfolioSummary().dict(),
                "positions": [],
                "bucket_breakdown": {b: {"positions": [], "allocation_pct": 0, "target_min": r["target_allocation_min"],
                                          "target_max": r["target_allocation_max"], "status": "empty"}
                                     for b, r in BUCKET_RULES.items()},
            }

        # Update prices if lookup provided
        total_value = 0
        total_cost = 0
        for pos in positions:
            sym = pos["symbol"]
            if price_lookup and sym in price_lookup:
                pos["current_price"] = price_lookup[sym]
            shares = pos.get("shares", 0)
            price = pos.get("current_price", pos.get("avg_cost", 0))
            cost = pos.get("avg_cost", 0)
            pos["current_value"] = round(shares * price, 2)
            pos["pnl_usd"] = round(shares * (price - cost), 2) if cost > 0 else 0
            pos["pnl_pct"] = round(((price / cost) - 1) * 100, 2) if cost > 0 else 0
            total_value += pos["current_value"]
            total_cost += shares * cost

        # Compute allocation percentages
        for pos in positions:
            pos["allocation_pct"] = round((pos["current_value"] / total_value) * 100, 2) if total_value > 0 else 0

        # Bucket breakdown
        bucket_breakdown = {}
        for bucket_key, rules in BUCKET_RULES.items():
            bucket_positions = [p for p in positions if p.get("bucket") == bucket_key]
            bucket_value = sum(p.get("current_value", 0) for p in bucket_positions)
            bucket_alloc = round((bucket_value / total_value) * 100, 2) if total_value > 0 else 0

            status = "healthy"
            if bucket_alloc < rules["target_allocation_min"]:
                status = "underweight"
            elif bucket_alloc > rules["target_allocation_max"]:
                status = "overweight"

            bucket_breakdown[bucket_key] = {
                "label": rules["label"],
                "positions": bucket_positions,
                "position_count": len(bucket_positions),
                "total_value": round(bucket_value, 2),
                "allocation_pct": bucket_alloc,
                "target_min": rules["target_allocation_min"],
                "target_max": rules["target_allocation_max"],
                "status": status,
            }

        # Diversification score (0-100)
        diversification = self._compute_diversification(positions, total_value, bucket_breakdown)

        # Rebalance check
        rebalance_needed, rebalance_reasons = self._check_rebalance_needed(positions, bucket_breakdown)

        total_pnl_usd = round(total_value - total_cost, 2)
        total_pnl_pct = round(((total_value / total_cost) - 1) * 100, 2) if total_cost > 0 else 0

        summary = LTPortfolioSummary(
            total_value=round(total_value, 2),
            total_cost=round(total_cost, 2),
            total_pnl_pct=total_pnl_pct,
            total_pnl_usd=total_pnl_usd,
            position_count=len(positions),
            bucket_allocation={
                b: round((sum(p.get("current_value", 0) for p in positions if p.get("bucket") == b) / total_value) * 100, 2)
                if total_value > 0 else 0
                for b in BUCKET_RULES
            },
            diversification_score=diversification,
            needs_rebalance=rebalance_needed,
            rebalance_reasons=rebalance_reasons,
            last_rebalance_check=datetime.now(timezone.utc).isoformat(),
        )

        return {
            "summary": summary.dict(),
            "positions": positions,
            "bucket_breakdown": bucket_breakdown,
        }

    def _compute_diversification(self, positions: List[Dict], total_value: float, bucket_breakdown: Dict) -> float:
        """Score 0-100 based on position count, bucket balance, and concentration."""
        if not positions or total_value <= 0:
            return 0

        score = 0

        # Position count (max 25 pts)
        count = len(positions)
        if count >= 15:
            score += 25
        elif count >= 10:
            score += 20
        elif count >= 5:
            score += 15
        elif count >= 3:
            score += 10
        else:
            score += 5

        # Bucket balance (max 35 pts) — all 3 buckets represented and within target ranges
        buckets_present = sum(1 for b in bucket_breakdown.values() if b["position_count"] > 0)
        score += buckets_present * 8  # up to 24

        healthy_buckets = sum(1 for b in bucket_breakdown.values() if b["status"] == "healthy")
        score += healthy_buckets * 4  # up to 12 (but capped)

        # Concentration (max 25 pts) — no single position dominates
        max_alloc = max((p.get("allocation_pct", 0) for p in positions), default=0)
        if max_alloc <= 10:
            score += 25
        elif max_alloc <= 20:
            score += 20
        elif max_alloc <= 35:
            score += 15
        else:
            score += 5

        # Asset type mix (max 15 pts) — has both ETFs and stocks
        has_etf = any(p.get("asset_type") == "etf" for p in positions)
        has_stock = any(p.get("asset_type") == "stock" for p in positions)
        if has_etf and has_stock:
            score += 15
        elif has_etf or has_stock:
            score += 8

        return min(100, score)

    def _check_rebalance_needed(self, positions: List[Dict], bucket_breakdown: Dict) -> tuple:
        """Check if rebalancing is needed based on drift and timing."""
        reasons = []
        now = datetime.now(timezone.utc)

        for bucket_key, rules in BUCKET_RULES.items():
            info = bucket_breakdown.get(bucket_key, {})
            alloc = info.get("allocation_pct", 0)

            # Check allocation drift
            if alloc > 0:
                if alloc > rules["target_allocation_max"] + 5:
                    reasons.append(f"{rules['label']}: {alloc:.1f}% allocation exceeds {rules['target_allocation_max']}% target max by >5%")
                elif alloc < rules["target_allocation_min"] - 5:
                    reasons.append(f"{rules['label']}: {alloc:.1f}% allocation below {rules['target_allocation_min']}% target min by >5%")

            # Check position concentration within bucket
            for pos in info.get("positions", []):
                pos_alloc = pos.get("allocation_pct", 0)
                if pos_alloc > rules["max_single_position_pct"]:
                    reasons.append(f"{pos['symbol']}: {pos_alloc:.1f}% exceeds {rules['max_single_position_pct']}% max for {rules['label']}")

            # Check timing-based rebalance
            for pos in info.get("positions", []):
                last_rebal = pos.get("last_rebalanced", "")
                if last_rebal:
                    try:
                        last_dt = datetime.fromisoformat(last_rebal.replace("Z", "+00:00"))
                        days_since = (now - last_dt).days
                        if days_since >= rules["rebalance_frequency_days"]:
                            reasons.append(f"{pos['symbol']}: {days_since} days since last rebalance (target: {rules['rebalance_frequency_days']}d)")
                    except (ValueError, TypeError):
                        pass

        return len(reasons) > 0, reasons

    # ---------- STAGED BUYING ----------

    async def stage_buy(self, symbol: str, bucket: str, shares: float, price: float,
                        thesis: str = "", name: str = "") -> Dict:
        """Execute a staged buy (25% increment). Returns updated position."""
        symbol = symbol.upper()
        existing = await self.get_position(symbol)
        now = datetime.now(timezone.utc).isoformat()

        asset_type = "etf" if symbol in CORE_ETFS else "stock"

        if existing:
            # Add to existing position (next stage)
            old_shares = existing.get("shares", 0)
            old_cost = existing.get("avg_cost", 0)
            new_total_shares = old_shares + shares
            new_avg_cost = round(((old_shares * old_cost) + (shares * price)) / new_total_shares, 4) if new_total_shares > 0 else price
            current_stage = existing.get("stage", 1) + 1

            updated = {
                **existing,
                "shares": round(new_total_shares, 6),
                "avg_cost": new_avg_cost,
                "current_price": price,
                "current_value": round(new_total_shares * price, 2),
                "stage": min(current_stage, 4),
                "last_stage_at": now,
                "status": "active" if current_stage >= 4 else "staged",
            }
            if thesis:
                updated["thesis"] = thesis
        else:
            # New position — stage 1
            updated = {
                "symbol": symbol,
                "name": name or self._get_name(symbol),
                "bucket": bucket,
                "asset_type": asset_type,
                "shares": round(shares, 6),
                "avg_cost": round(price, 4),
                "current_price": price,
                "current_value": round(shares * price, 2),
                "stage": 1,
                "max_stages": 4,
                "thesis": thesis,
                "added_at": now,
                "last_stage_at": now,
                "last_rebalanced": now,
                "status": "staged",
                "score": 0,
                "score_drivers": {},
            }

        await self.upsert_position(updated)

        # Log the stage
        await self.db[self.log_collection].insert_one({
            "symbol": symbol,
            "action": "STAGE_BUY",
            "stage": updated["stage"],
            "shares_added": shares,
            "price": price,
            "bucket": bucket,
            "timestamp": now,
        })

        return updated

    async def trim_position(self, symbol: str, shares_to_sell: float, price: float, reason: str = "") -> Dict:
        """Trim a position (partial sell)."""
        symbol = symbol.upper()
        pos = await self.get_position(symbol)
        if not pos:
            return {"error": f"No active position for {symbol}"}

        old_shares = pos.get("shares", 0)
        if shares_to_sell >= old_shares:
            await self.close_position(symbol, reason or "Full exit via trim")
            return {"symbol": symbol, "action": "CLOSED", "shares_sold": old_shares}

        new_shares = round(old_shares - shares_to_sell, 6)
        pos["shares"] = new_shares
        pos["current_value"] = round(new_shares * price, 2)
        pos["current_price"] = price
        await self.upsert_position(pos)

        now = datetime.now(timezone.utc).isoformat()
        await self.db[self.log_collection].insert_one({
            "symbol": symbol,
            "action": "TRIM",
            "shares_sold": shares_to_sell,
            "shares_remaining": new_shares,
            "price": price,
            "reason": reason,
            "timestamp": now,
        })

        return {**pos, "action": "TRIMMED", "shares_sold": shares_to_sell}

    # ---------- RECOMMENDATIONS ----------

    async def generate_recommendations(self, price_lookup: Dict = None, investment_signals: Dict = None) -> List[Dict]:
        """
        Generate Buy/Add/Trim/Rebalance recommendations.
        Uses existing portfolio state + market data.
        """
        positions = await self.get_positions()
        portfolio_data = await self.get_portfolio_summary(price_lookup)
        summary = portfolio_data["summary"]
        bucket_breakdown = portfolio_data["bucket_breakdown"]
        total_value = summary.get("total_value", 0)
        recommendations = []

        # --- 1. Rebalance recommendations (trim overweight, add underweight) ---
        for bucket_key, info in bucket_breakdown.items():
            rules = BUCKET_RULES[bucket_key]
            alloc = info.get("allocation_pct", 0)

            if alloc > rules["target_allocation_max"] + 3:
                # Overweight — suggest trim on largest position in bucket
                bucket_positions = sorted(info.get("positions", []),
                                          key=lambda p: p.get("allocation_pct", 0), reverse=True)
                if bucket_positions:
                    top = bucket_positions[0]
                    recommendations.append(LTRecommendation(
                        symbol=top["symbol"],
                        name=top.get("name", ""),
                        action="TRIM",
                        bucket=bucket_key,
                        reason=f"{rules['label']} overweight ({alloc:.1f}% vs {rules['target_allocation_max']}% max). Trim largest position.",
                        priority="high",
                        current_allocation_pct=top.get("allocation_pct", 0),
                        suggested_allocation_pct=rules["max_single_position_pct"],
                        asset_type=top.get("asset_type", "stock"),
                    ).dict())

            elif alloc < rules["target_allocation_min"] - 3 and total_value > 0:
                # Underweight — suggest adding to bucket
                gap_pct = rules["target_allocation_min"] - alloc
                recommendations.append(LTRecommendation(
                    symbol="BUCKET:" + bucket_key.upper(),
                    name=rules["label"],
                    action="ADD",
                    bucket=bucket_key,
                    reason=f"{rules['label']} underweight ({alloc:.1f}% vs {rules['target_allocation_min']}% min). Add {gap_pct:.1f}% to reach target.",
                    priority="medium",
                    current_allocation_pct=alloc,
                    suggested_allocation_pct=rules["target_allocation_min"],
                ).dict())

        # --- 2. Staged buying recommendations (positions not at full 4 stages) ---
        for pos in positions:
            stage = pos.get("stage", 0)
            if stage < 4 and pos.get("status") in ("staged", "active"):
                last_stage = pos.get("last_stage_at", "")
                days_since_last = 0
                if last_stage:
                    try:
                        last_dt = datetime.fromisoformat(last_stage.replace("Z", "+00:00"))
                        days_since_last = (datetime.now(timezone.utc) - last_dt).days
                    except (ValueError, TypeError):
                        pass

                # Stage 2 after 7 days, stage 3 after 14 days, stage 4 after 21 days
                min_wait = 7 * stage
                if days_since_last >= min_wait:
                    pnl = pos.get("pnl_pct", 0)
                    priority = "high" if pnl < -5 else ("medium" if pnl < 5 else "low")

                    if pnl < -5:
                        reason = f"Stage {stage+1}/4: Price pulled back {abs(pnl):.1f}% — good averaging opportunity"
                    elif pnl > 5:
                        reason = f"Stage {stage+1}/4: Position up {pnl:.1f}% — thesis confirmed, add strength"
                    else:
                        reason = f"Stage {stage+1}/4: {days_since_last} days since last stage — time-based add"

                    recommendations.append(LTRecommendation(
                        symbol=pos["symbol"],
                        name=pos.get("name", ""),
                        action="ADD",
                        bucket=pos.get("bucket", ""),
                        reason=reason,
                        priority=priority,
                        stage_info=f"Stage {stage+1} of 4",
                        current_allocation_pct=pos.get("allocation_pct", 0),
                        asset_type=pos.get("asset_type", "stock"),
                    ).dict())

        # --- 3. New position recommendations from Core ETF universe ---
        held_symbols = {p["symbol"] for p in positions}
        core_alloc = bucket_breakdown.get("core", {}).get("allocation_pct", 0)

        if core_alloc < BUCKET_RULES["core"]["target_allocation_max"]:
            for sym, info in CORE_ETFS.items():
                if sym not in held_symbols:
                    recommendations.append(LTRecommendation(
                        symbol=sym,
                        name=info["name"],
                        action="BUY",
                        bucket="core",
                        reason=f"Core ETF not held. Target allocation: {info['target_pct']}%. Category: {info['category']}.",
                        priority="medium",
                        suggested_allocation_pct=info["target_pct"],
                        asset_type="etf",
                    ).dict())

        # --- 4. Score-based recommendations from investment signals ---
        if investment_signals:
            for sym, sig in investment_signals.items():
                if sym in held_symbols:
                    continue
                score = sig.get("overall_score", 0)
                signal = sig.get("signal", "")
                if score >= 75 and signal in ("Strong Buy", "Buy"):
                    bucket = "quality_growth"
                    if sig.get("valuation_summary", {}).get("classification") == "Undervalued":
                        bucket = "opportunistic_value"

                    bucket_alloc = bucket_breakdown.get(bucket, {}).get("allocation_pct", 0)
                    if bucket_alloc < BUCKET_RULES[bucket]["target_allocation_max"]:
                        recommendations.append(LTRecommendation(
                            symbol=sym,
                            name=sig.get("name", sym),
                            action="BUY",
                            bucket=bucket,
                            reason=f"Score {score:.0f}/100, Signal: {signal}. {sig.get('valuation_summary', {}).get('classification', 'N/A')} valuation.",
                            priority="medium" if score < 85 else "high",
                            score=score,
                            suggested_allocation_pct=BUCKET_RULES[bucket]["max_single_position_pct"],
                            asset_type="stock",
                        ).dict())

        # Sort: high priority first, then by score
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda r: (priority_order.get(r.get("priority", "low"), 3), -r.get("score", 0)))

        return recommendations

    # ---------- THESIS HEALTH ----------

    async def get_thesis_health(self, symbol: str, investment_signal: Dict = None) -> Dict:
        """Evaluate if the original investment thesis is still intact."""
        pos = await self.get_position(symbol)
        if not pos:
            return {"symbol": symbol, "error": "No position found"}

        health = {
            "symbol": symbol,
            "name": pos.get("name", ""),
            "bucket": pos.get("bucket", ""),
            "original_thesis": pos.get("thesis", "No thesis recorded"),
            "stage": pos.get("stage", 0),
            "pnl_pct": pos.get("pnl_pct", 0),
            "days_held": 0,
            "health_score": 50,
            "health_status": "neutral",
            "signals": [],
            "recommendation": "HOLD",
        }

        # Days held
        added = pos.get("added_at", "")
        if added:
            try:
                added_dt = datetime.fromisoformat(added.replace("Z", "+00:00"))
                health["days_held"] = (datetime.now(timezone.utc) - added_dt).days
            except (ValueError, TypeError):
                pass

        # Score based on P&L
        pnl = pos.get("pnl_pct", 0)
        if pnl > 20:
            health["health_score"] += 20
            health["signals"].append(f"Strong gain: +{pnl:.1f}%")
        elif pnl > 5:
            health["health_score"] += 10
            health["signals"].append(f"Positive: +{pnl:.1f}%")
        elif pnl < -20:
            health["health_score"] -= 25
            health["signals"].append(f"Deep loss: {pnl:.1f}% — thesis under pressure")
        elif pnl < -10:
            health["health_score"] -= 15
            health["signals"].append(f"Significant drawdown: {pnl:.1f}%")

        # Score based on investment signal (if available)
        if investment_signal:
            inv_score = investment_signal.get("overall_score", 0)
            inv_signal = investment_signal.get("signal", "")
            if inv_score >= 75:
                health["health_score"] += 15
                health["signals"].append(f"Fundamentals strong: {inv_score:.0f}/100")
            elif inv_score < 40:
                health["health_score"] -= 15
                health["signals"].append(f"Fundamentals deteriorating: {inv_score:.0f}/100")

            if inv_signal in ("Strong Sell", "Sell"):
                health["health_score"] -= 20
                health["signals"].append(f"Investment signal: {inv_signal}")

        # Determine health status and recommendation
        health["health_score"] = max(0, min(100, health["health_score"]))
        if health["health_score"] >= 70:
            health["health_status"] = "strong"
            health["recommendation"] = "HOLD" if pos.get("stage", 0) >= 4 else "ADD"
        elif health["health_score"] >= 40:
            health["health_status"] = "neutral"
            health["recommendation"] = "HOLD"
        else:
            health["health_status"] = "weak"
            health["recommendation"] = "TRIM" if pnl < -15 else "HOLD"

        return health

    # ---------- WATCHLIST / UNIVERSE ----------

    def get_universe(self) -> Dict:
        """Return the full LT investment universe organized by bucket."""
        return {
            "core": {sym: {**info, "asset_type": "etf"} for sym, info in CORE_ETFS.items()},
            "quality_growth": {sym: {**info, "asset_type": "stock"} for sym, info in QUALITY_GROWTH_UNIVERSE.items()},
            "opportunistic_value": {sym: {**info, "asset_type": "stock"} for sym, info in VALUE_UNIVERSE.items()},
            "bucket_rules": BUCKET_RULES,
        }

    # ---------- HELPERS ----------

    def _get_name(self, symbol: str) -> str:
        if symbol in CORE_ETFS:
            return CORE_ETFS[symbol]["name"]
        if symbol in QUALITY_GROWTH_UNIVERSE:
            return QUALITY_GROWTH_UNIVERSE[symbol]["name"]
        if symbol in VALUE_UNIVERSE:
            return VALUE_UNIVERSE[symbol]["name"]
        return symbol
