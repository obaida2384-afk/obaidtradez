"""
ObaidTradez AI Trading System
Dual-engine autonomous trading with Day Trading + Long-Term Investment modes.
Modular architecture: Classification → Scoring → Risk → Sizing → Execution → Monitoring
"""

import asyncio
import logging
import math
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _safe_float(val, default=0):
    """Safely convert any value to float"""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

# ===================== MODELS =====================

class AutoTradeSettings(BaseModel):
    """Master auto-trade configuration"""
    auto_enabled: bool = False
    
    # Day Trading Settings
    dt_enabled: bool = True
    dt_risk_per_trade_pct: float = 0.04  # 4% of capital
    dt_high_conf_risk_pct: float = 0.08  # 8% for high confidence
    dt_max_positions: int = 6
    dt_confidence_threshold: int = 65  # TA-first: lowered from 80
    dt_take_profit_pct: float = 2.5  # 2.5%
    dt_stop_loss_pct: float = 0.8  # 0.8%
    dt_time_exit_days: int = 2
    dt_carry_overnight: bool = False
    dt_cooldown_after_loss: int = 15  # minutes
    
    # Long-Term Settings
    lt_enabled: bool = True
    lt_max_position_pct: float = 0.15  # 15% of capital
    lt_max_positions: int = 8
    lt_confidence_threshold: int = 70  # Adjusted from 75
    lt_trailing_stop_pct: float = 15.0  # 15%
    lt_rebalance_threshold_pct: float = 25.0  # rebalance if +25% overweight
    lt_valuation_margin_pct: float = 10.0  # margin of safety
    
    # Global Risk Settings
    max_daily_loss_pct: float = 3.0
    max_portfolio_drawdown_pct: float = 10.0
    max_sector_concentration_pct: float = 30.0
    emergency_pause: bool = False
    alert_only_mode: bool = False


class TradeExplanation(BaseModel):
    """Explainability for every trade decision"""
    ticker: str
    classification: str  # DAY_TRADE, LONG_TERM, NO_TRADE
    confidence_score: int = 0
    action: str = "HOLD"  # BUY, SELL, HOLD, REJECT, WATCHLIST
    entry_reasons: List[str] = []
    exit_reasons: List[str] = []
    reject_reasons: List[str] = []
    risk_checks: List[str] = []
    exit_plan: Dict = {}
    position_size_logic: str = ""
    key_indicators: Dict = {}
    timestamp: str = ""


# ===================== DYNAMIC THRESHOLD MANAGER =====================

class DynamicThresholdManager:
    """Adjusts confidence thresholds based on market regime, recent performance, post-cooldown state"""

    DT_FLOOR = 55
    DT_DEFAULT = 65
    LT_FLOOR = 60
    LT_DEFAULT = 70

    @staticmethod
    def get_thresholds(market_regime: Dict, settings: "AutoTradeSettings",
                       post_cooldown: bool = False, daily_loss_pct: float = 0) -> Dict:
        regime = market_regime.get("regime", "neutral")
        vol_pct = _safe_float(market_regime.get("volatility_pct", 0))

        dt_thresh = settings.dt_confidence_threshold
        lt_thresh = settings.lt_confidence_threshold

        # Regime adjustments (calibrated for TA-first engine)
        # User-specified: Neutral/Neutral Bearish: 65, Bullish: 60-65, Bearish: 68-70
        if regime == "bearish":
            dt_thresh += 5
            lt_thresh += 4
        elif regime == "neutral_bearish":
            dt_thresh += 0  # Stays at base (65)
            lt_thresh += 2
        elif regime == "high_volatility":
            dt_thresh += 3
            lt_thresh += 2
        elif regime == "bullish":
            dt_thresh = max(DynamicThresholdManager.DT_FLOOR, dt_thresh - 5)
            lt_thresh = max(DynamicThresholdManager.LT_FLOOR, lt_thresh - 4)
        elif regime == "neutral_bullish":
            dt_thresh = max(DynamicThresholdManager.DT_FLOOR, dt_thresh - 3)
            lt_thresh = max(DynamicThresholdManager.LT_FLOOR, lt_thresh - 2)

        # Post-cooldown boost (+5 for safety after consecutive losses)
        if post_cooldown:
            dt_thresh += 5
            lt_thresh += 5

        # Near daily loss limit (at 80%+) → further tighten
        if daily_loss_pct >= 80:
            dt_thresh += 5
            lt_thresh += 5

        # Enforce floors
        dt_thresh = max(DynamicThresholdManager.DT_FLOOR, dt_thresh)
        lt_thresh = max(DynamicThresholdManager.LT_FLOOR, lt_thresh)

        # Risk mode
        if regime in ("bearish", "high_volatility") or daily_loss_pct >= 60:
            risk_mode = "DEFENSIVE"
        elif regime == "bullish" and daily_loss_pct < 30:
            risk_mode = "NORMAL"
        else:
            risk_mode = "CAUTIOUS"

        return {
            "dt_threshold": dt_thresh,
            "lt_threshold": lt_thresh,
            "risk_mode": risk_mode,
            "regime_adjustment": regime,
            "post_cooldown_active": post_cooldown,
            "daily_loss_factor": daily_loss_pct,
        }

    @staticmethod
    def get_max_positions(classification: str, settings: "AutoTradeSettings",
                          market_regime: Dict) -> int:
        regime = market_regime.get("regime", "neutral")
        base = settings.dt_max_positions if classification == "DAY_TRADE" else settings.lt_max_positions
        if regime in ("bearish", "neutral_bearish"):
            return max(1, int(base * 0.5))
        if regime == "high_volatility":
            return max(1, int(base * 0.6))
        return base


# ===================== TRADE PIPELINE FUNNEL =====================

class TradePipelineFunnel:
    """Tracks stocks at each pipeline stage for debugging"""

    def __init__(self):
        self.stages = {
            "universe_scanned": 0,
            "prefilter_passed": 0,
            "ta_analyzed": 0,
            "setup_found": 0,
            "filters_passed": 0,
            "confidence_passed": 0,
            "risk_approved": 0,
            "executed": 0,
        }
        self.stage_details = {}
        self.rejections = {}  # reason -> count

    def record(self, stage: str, count: int = 1):
        self.stages[stage] = self.stages.get(stage, 0) + count

    def reject(self, reason: str):
        self.rejections[reason] = self.rejections.get(reason, 0) + 1

    def to_dict(self) -> Dict:
        # Compute bottleneck
        ordered = list(self.stages.items())
        bottleneck = ""
        max_drop = 0
        for i in range(1, len(ordered)):
            prev_count = ordered[i - 1][1]
            curr_count = ordered[i][1]
            if prev_count > 0:
                drop = prev_count - curr_count
                if drop > max_drop:
                    max_drop = drop
                    bottleneck = ordered[i][0]
        return {
            "funnel": self.stages,
            "bottleneck": bottleneck,
            "top_rejections": dict(sorted(self.rejections.items(), key=lambda x: -x[1])[:10]),
        }


# ===================== TRADE FREQUENCY CONTROLLER =====================

class TradeFrequencyController:
    """Limits trade frequency to prevent overtrading"""

    MAX_DT_PER_HOUR = 3
    MAX_LT_PER_HOUR = 1

    def __init__(self, db):
        self.db = db

    async def can_trade(self, classification: str, market_regime: Dict) -> Tuple[bool, str]:
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        regime = market_regime.get("regime", "neutral")

        recent = await self.db.auto_trade_log.count_documents({
            "action": "BUY",
            "classification": classification,
            "timestamp": {"$gte": one_hour_ago.isoformat()},
        })

        limit = (self.MAX_DT_PER_HOUR if classification == "DAY_TRADE"
                 else self.MAX_LT_PER_HOUR)

        # Reduce frequency in weak regime
        if regime in ("bearish", "neutral_bearish", "high_volatility"):
            limit = max(1, limit // 2)

        if recent >= limit:
            return False, f"Frequency limit: {recent}/{limit} trades this hour ({classification})"

        # Check recent performance (if last 3 trades all negative, reduce)
        last_sells = await self.db.auto_trade_log.find(
            {"action": "SELL"}, {"_id": 0, "pnl": 1}
        ).sort("timestamp", -1).limit(3).to_list(3)
        if len(last_sells) >= 3 and all(s.get("pnl", 0) < 0 for s in last_sells):
            return False, "Recent performance negative (last 3 trades all losses)"

        return True, "OK"


# ===================== ZERO-TRADE DIAGNOSTICS =====================

class ZeroTradeDiagnostics:
    """Diagnoses why no trades are generated and tracks near-misses"""

    def __init__(self):
        self.no_trade_reasons = []
        self.near_misses = []  # confidence 68-79 range (close to threshold)
        self.filter_stage_counts = {}

    def add_reason(self, reason: str):
        if reason not in self.no_trade_reasons:
            self.no_trade_reasons.append(reason)

    def add_near_miss(self, symbol: str, classification: str, confidence: int,
                       action: str, reject_reasons: List[str]):
        self.near_misses.append({
            "symbol": symbol,
            "classification": classification,
            "confidence": confidence,
            "action": action,
            "reject_reasons": reject_reasons[:3],
            "label": "Almost Trade Candidate"
        })

    def track_filter(self, stage: str, passed: int, total: int):
        self.filter_stage_counts[stage] = {"passed": passed, "total": total}

    def get_opportunity_quality(self, dt_candidates: int, lt_candidates: int,
                                 market_regime: Dict) -> str:
        regime = market_regime.get("regime", "neutral")
        regime_score = market_regime.get("score", 50)
        total = dt_candidates + lt_candidates

        if total >= 10 and regime_score >= 60:
            return "HIGH_OPPORTUNITY"
        elif total >= 5 or (total >= 3 and regime in ("bullish", "neutral_bullish")):
            return "MEDIUM_OPPORTUNITY"
        else:
            return "LOW_OPPORTUNITY"

    def build_no_trade_summary(self, dt_count: int, lt_count: int,
                                 market_regime: Dict) -> Dict:
        reasons = list(self.no_trade_reasons)
        if dt_count == 0:
            if not any("volume" in r.lower() for r in reasons):
                reasons.append("No high-confidence day trade setups found")
        if lt_count == 0:
            if not any("long" in r.lower() for r in reasons):
                reasons.append("No qualifying long-term investment candidates")

        return {
            "has_trades": dt_count > 0 or lt_count > 0,
            "dt_candidates": dt_count,
            "lt_candidates": lt_count,
            "top_reasons": reasons[:5],
            "near_misses": sorted(self.near_misses,
                                   key=lambda x: x["confidence"], reverse=True)[:10],
            "opportunity_quality": self.get_opportunity_quality(
                dt_count, lt_count, market_regime),
            "filter_stages": self.filter_stage_counts,
        }


# ===================== MARKET REGIME DETECTOR =====================

class MarketRegimeDetector:
    """Detects current market environment to adjust strategy parameters"""
    
    def __init__(self, api_client):
        self.api_client = api_client
    
    async def detect(self) -> Dict:
        """Detect market regime using SPY as proxy"""
        try:
            spy_data = await self.api_client.fmp_historical("SPY", days=60)
            if not spy_data or len(spy_data) < 30:
                return {"regime": "neutral", "volatility": "normal", "trend": "unclear", "score": 50}
            
            prices = [d.get("close", 0) for d in reversed(spy_data) if d.get("close")]
            if len(prices) < 30:
                return {"regime": "neutral", "volatility": "normal", "trend": "unclear", "score": 50}
            
            # Trend: compare 10-day vs 30-day SMA
            sma_10 = sum(prices[-10:]) / 10
            sma_30 = sum(prices[-30:]) / 30
            trend_pct = ((sma_10 / sma_30) - 1) * 100
            
            # Volatility: 20-day historical vol
            daily_returns = [(prices[i] / prices[i-1] - 1) for i in range(1, len(prices))]
            recent_returns = daily_returns[-20:]
            if recent_returns:
                mean_ret = sum(recent_returns) / len(recent_returns)
                variance = sum((r - mean_ret) ** 2 for r in recent_returns) / len(recent_returns)
                vol = math.sqrt(variance * 252) * 100
            else:
                vol = 20
            
            # 20-day momentum
            momentum_20d = ((prices[-1] / prices[-20]) - 1) * 100 if len(prices) >= 20 else 0
            
            # Classify regime
            if trend_pct > 1.5 and vol < 25:
                regime = "bullish"
                score = 80
            elif trend_pct > 0.5 and vol < 35:
                regime = "neutral_bullish"
                score = 65
            elif trend_pct < -1.5 and vol > 30:
                regime = "bearish"
                score = 25
            elif vol > 35:
                regime = "high_volatility"
                score = 30
            elif trend_pct < -0.5:
                regime = "neutral_bearish"
                score = 40
            else:
                regime = "neutral"
                score = 50
            
            vol_label = "low" if vol < 15 else "normal" if vol < 25 else "high" if vol < 40 else "extreme"
            trend_label = "strong_up" if trend_pct > 2 else "up" if trend_pct > 0.5 else "flat" if trend_pct > -0.5 else "down" if trend_pct > -2 else "strong_down"
            
            return {
                "regime": regime,
                "volatility": vol_label,
                "volatility_pct": round(vol, 1),
                "trend": trend_label,
                "trend_pct": round(trend_pct, 2),
                "momentum_20d": round(momentum_20d, 2),
                "score": score,
                "sma_10": round(sma_10, 2),
                "sma_30": round(sma_30, 2)
            }
        except Exception as e:
            logger.error(f"Market regime detection error: {e}")
            return {"regime": "neutral", "volatility": "normal", "trend": "unclear", "score": 50}


# ===================== STOCK CLASSIFIER =====================

class StockClassifier:
    """Classifies stocks as DAY_TRADE, LONG_TERM, or NO_TRADE"""
    
    @staticmethod
    def classify(trading_signal: Optional[Dict], investment_signal: Optional[Dict]) -> Dict:
        """
        Compare day trading score vs long-term score.
        Returns classification with scores.
        """
        dt_score = 0
        lt_score = 0
        reasons = []
        
        # Day Trading Score (0-100)
        if trading_signal:
            conf = trading_signal.get("confidence", 0)
            if isinstance(conf, (int, float)):
                dt_score += conf * 40  # Base confidence: 40%
            
            indicators = trading_signal.get("indicators", {})
            
            # Volume factor: 20%
            vol_ratio = indicators.get("volume_ratio", 0)
            if vol_ratio >= 2.0:
                dt_score += 20
                reasons.append("Strong volume surge")
            elif vol_ratio >= 1.5:
                dt_score += 14
            elif vol_ratio >= 1.0:
                dt_score += 8
            
            # ATR/Volatility factor: 15%
            atr_pct = indicators.get("atr_pct", 0)
            if 2.0 <= atr_pct <= 8.0:
                dt_score += 15
                reasons.append(f"Good volatility range ({atr_pct:.1f}%)")
            elif 1.0 <= atr_pct < 2.0:
                dt_score += 8
            
            # Momentum factor: 15%
            momentum_5d = indicators.get("momentum_5d", 0)
            if momentum_5d > 3:
                dt_score += 15
                reasons.append("Strong 5-day momentum")
            elif momentum_5d > 1:
                dt_score += 10
            
            # Structure bonus: 10%
            if indicators.get("structure_type"):
                dt_score += 10
                reasons.append(f"Technical structure: {indicators['structure_type']}")
        
        # Long-Term Score (0-100)
        if investment_signal:
            inv_score = investment_signal.get("overall_score", 0)
            lt_score += min(inv_score * 0.35, 35)  # Fundamentals: 35%
            
            val = investment_signal.get("valuation_summary", {})
            bq = investment_signal.get("business_quality", {})
            gp = investment_signal.get("growth_profile", {})
            hp = investment_signal.get("historical_performance", {})
            
            # Valuation: 30%
            val_status = val.get("valuation_status", "")
            if "Undervalued" in val_status:
                lt_score += 30
                reasons.append("Undervalued stock")
            elif "Fair" in val_status:
                lt_score += 20
            elif "Premium" in val_status or "Overvalued" in val_status:
                lt_score += 5
            
            # Growth: 15%
            rev_growth = _safe_float(gp.get("revenue_growth"))
            if rev_growth > 15:
                lt_score += 15
                reasons.append(f"Strong revenue growth ({rev_growth:.0f}%)")
            elif rev_growth > 5:
                lt_score += 10
            elif rev_growth > 0:
                lt_score += 5
            
            # Quality: 10%
            quality_rating = bq.get("quality_rating", "")
            if quality_rating in ["Excellent", "Very Good"]:
                lt_score += 10
                reasons.append(f"Business quality: {quality_rating}")
            elif quality_rating == "Good":
                lt_score += 6
            
            # Historical track record: 10%
            if hp:
                hist_rating = hp.get("historical_rating", "")
                if hist_rating == "Exceptional":
                    lt_score += 10
                elif hist_rating == "Strong":
                    lt_score += 7
                elif hist_rating == "Average":
                    lt_score += 4
        
        # Classification decision
        dt_score = min(round(dt_score), 100)
        lt_score = min(round(lt_score), 100)
        
        if dt_score >= 50 and dt_score > lt_score and trading_signal:
            classification = "DAY_TRADE"
        elif lt_score >= 45 and lt_score >= dt_score and investment_signal:
            classification = "LONG_TERM"
        elif dt_score >= 40 or lt_score >= 35:
            classification = "WATCHLIST"
        else:
            classification = "NO_TRADE"
        
        return {
            "classification": classification,
            "day_trading_score": dt_score,
            "long_term_score": lt_score,
            "reasons": reasons
        }


# ===================== CONFIDENCE SCORING ENGINE =====================

class ConfidenceScoringEngine:
    """Weighted confidence scoring for trade decisions"""
    
    @staticmethod
    def score_day_trade(signal: Dict, market_regime: Dict) -> int:
        """Score day trade confidence (0-100)"""
        score = 0
        indicators = signal.get("indicators", {})
        
        # Technical setup: 30%
        structure = indicators.get("structure_type", "")
        confluence = indicators.get("confluence_factors", 0)
        if structure and confluence >= 3:
            score += 30
        elif structure and confluence >= 2:
            score += 25
        elif confluence >= 2:
            score += 20
        elif structure or confluence >= 1:
            score += 12
        else:
            score += 5
        
        # Volume/Liquidity: 20%
        vol_ratio = indicators.get("volume_ratio", 0)
        if vol_ratio >= 2.5:
            score += 20
        elif vol_ratio >= 1.5:
            score += 14
        elif vol_ratio >= 1.0:
            score += 8
        
        # Sentiment/Catalyst: 20%
        news = signal.get("news_sentiment")
        if news and isinstance(news, dict):
            sent_score = _safe_float(news.get("composite_score", 0.5), 0.5)
            if sent_score >= 0.7:
                score += 20
            elif sent_score >= 0.55:
                score += 12
            else:
                score += 4
        else:
            score += 6  # Neutral if no news
        
        # Risk-Reward: 15%
        rr = indicators.get("rr_ratio", 0)
        if rr >= 3:
            score += 15
        elif rr >= 2:
            score += 11
        elif rr >= 1.5:
            score += 7
        
        # Market regime: 15%
        regime_score = market_regime.get("score", 50)
        score += int(regime_score * 0.15)
        
        return min(score, 100)
    
    @staticmethod
    def score_long_term(signal: Dict, market_regime: Dict) -> int:
        """Score long-term investment confidence (0-100)"""
        score = 0
        
        # Fundamentals: 35%
        overall = _safe_float(signal.get("overall_score", 0))
        score += min(int(overall * 0.45), 35)
        
        # Valuation: 30%
        val = signal.get("valuation_summary", {})
        pe = val.get("pe_ratio")
        upside = val.get("upside_potential", 0)
        try:
            upside = float(upside) if upside else 0
            pe = float(pe) if pe else None
        except (ValueError, TypeError):
            upside = 0
            pe = None
        if upside > 30:
            score += 30
        elif upside and upside > 15:
            score += 22
        elif upside and upside > 0:
            score += 15
        elif pe and pe < 15:
            score += 18
        elif pe and pe < 25:
            score += 10
        
        # Growth: 15%
        gp = signal.get("growth_profile", {})
        trend = gp.get("growth_trend", "")
        if trend == "Accelerating":
            score += 15
        elif trend == "Stable":
            score += 10
        elif trend == "Decelerating":
            score += 5
        
        # Industry: 10%
        sector = signal.get("sector", "")
        if sector in ["Technology", "Healthcare", "Consumer Cyclical"]:
            score += 8
        else:
            score += 5
        
        # Technical stability: 10%
        hp = signal.get("historical_performance", {})
        if hp:
            sma_trend = hp.get("sma_200_trend", "")
            if sma_trend == "Above":
                score += 10
            else:
                score += 3
        
        return min(score, 100)


# ===================== RISK MANAGER =====================

class RiskManager:
    """Enforces all risk rules before trade execution"""
    
    def __init__(self, db):
        self.db = db
    
    async def check_all(self, signal: Dict, confidence: int, classification: str,
                        settings: AutoTradeSettings, account: Dict, 
                        open_positions: List[Dict], market_regime: Dict) -> Tuple[bool, List[str]]:
        """Run all risk checks. Returns (approved, list_of_checks)"""
        checks = []
        violations = []
        
        equity = float(account.get("equity", 0))
        buying_power = float(account.get("buying_power", 0))
        
        # 1. Emergency pause
        if settings.emergency_pause:
            violations.append("Emergency pause is active")
            return False, violations
        
        # 2. Confidence threshold
        threshold = settings.dt_confidence_threshold if classification == "DAY_TRADE" else settings.lt_confidence_threshold
        if confidence < threshold:
            violations.append(f"Confidence {confidence} below threshold {threshold}")
        else:
            checks.append(f"Confidence {confidence} >= {threshold} threshold")
        
        # 3. Market regime adjustment
        regime = market_regime.get("regime", "neutral")
        regime_score = market_regime.get("score", 50)
        if classification == "DAY_TRADE" and regime in ["bearish", "high_volatility"]:
            adjusted_threshold = threshold + 10
            if confidence < adjusted_threshold:
                violations.append(f"Weak market ({regime}): raised threshold to {adjusted_threshold}")
        if regime in ["bearish", "high_volatility"]:
            checks.append(f"Market regime: {regime} (caution)")
        else:
            checks.append(f"Market regime: {regime}")
        
        # 4. Max positions
        max_pos = settings.dt_max_positions if classification == "DAY_TRADE" else settings.lt_max_positions
        if len(open_positions) >= max_pos:
            violations.append(f"Max positions reached ({len(open_positions)}/{max_pos})")
        else:
            checks.append(f"Positions: {len(open_positions)}/{max_pos}")
        
        # 5. Daily loss limit
        daily_pnl = await self._get_daily_pnl()
        max_daily_loss = equity * (settings.max_daily_loss_pct / 100)
        if daily_pnl < -max_daily_loss:
            violations.append(f"Daily loss limit hit: ${daily_pnl:.0f} (max -${max_daily_loss:.0f})")
        else:
            checks.append(f"Daily P&L: ${daily_pnl:.0f} (limit: -${max_daily_loss:.0f})")
        
        # 6. Drawdown protection
        peak_equity = await self._get_peak_equity(equity)
        drawdown = ((equity - peak_equity) / peak_equity * 100) if peak_equity > 0 else 0
        if drawdown < -settings.max_portfolio_drawdown_pct:
            violations.append(f"Drawdown limit hit: {drawdown:.1f}% (max -{settings.max_portfolio_drawdown_pct}%)")
        else:
            checks.append(f"Drawdown: {drawdown:.1f}% (limit: -{settings.max_portfolio_drawdown_pct}%)")
        
        # 7. Sector concentration
        symbol = signal.get("symbol", "")
        sector = signal.get("sector", signal.get("profile", {}).get("sector", "Unknown"))
        sector_exposure = self._calc_sector_exposure(open_positions, sector, equity)
        if sector_exposure > settings.max_sector_concentration_pct:
            violations.append(f"Sector concentration too high: {sector}={sector_exposure:.0f}%")
        else:
            checks.append(f"Sector exposure ({sector}): {sector_exposure:.0f}%")
        
        # 8. Buying power
        if buying_power < equity * 0.05:
            violations.append("Insufficient buying power (<5%)")
        else:
            checks.append(f"Buying power: ${buying_power:,.0f}")
        
        # 9. Cooldown after loss (day trading)
        if classification == "DAY_TRADE":
            last_loss = await self._last_loss_time()
            if last_loss:
                minutes_since = (datetime.now(timezone.utc) - last_loss).total_seconds() / 60
                if minutes_since < settings.dt_cooldown_after_loss:
                    violations.append(f"Cooldown: {settings.dt_cooldown_after_loss - minutes_since:.0f}min remaining")
        
        approved = len(violations) == 0
        all_checks = checks + [f"VIOLATION: {v}" for v in violations]
        return approved, all_checks
    
    async def _get_daily_pnl(self) -> float:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        trades = await self.db.auto_trade_log.find(
            {"date": today, "action": "SELL"}
        ).to_list(100)
        return sum(t.get("pnl", 0) for t in trades)
    
    async def _get_peak_equity(self, current: float) -> float:
        record = await self.db.auto_trade_metrics.find_one({"_id": "peak_equity"})
        peak = record.get("value", current) if record else current
        if current > peak:
            await self.db.auto_trade_metrics.update_one(
                {"_id": "peak_equity"}, {"$set": {"value": current}}, upsert=True
            )
            return current
        return peak
    
    async def _last_loss_time(self) -> Optional[datetime]:
        last = await self.db.auto_trade_log.find_one(
            {"action": "SELL", "pnl": {"$lt": 0}},
            sort=[("timestamp", -1)]
        )
        if last and last.get("timestamp"):
            ts = last["timestamp"]
            if isinstance(ts, str):
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return ts
        return None
    
    def _calc_sector_exposure(self, positions: List[Dict], sector: str, equity: float) -> float:
        if equity <= 0:
            return 100
        sector_value = sum(
            float(p.get("market_value", 0))
            for p in positions
            if p.get("sector", "Unknown") == sector
        )
        return (sector_value / equity) * 100


# ===================== POSITION SIZER =====================

class PositionSizer:
    """Smart position sizing based on confidence, risk, regime, and classification"""
    
    # Caps
    DT_MAX_PCT = 5.0   # max 5% per day trade
    LT_MAX_PCT = 20.0  # max 20% per long-term position
    
    @staticmethod
    def calculate(classification: str, confidence: int, settings: AutoTradeSettings,
                  equity: float, stop_distance_pct: float, signal: Dict,
                  market_regime: Dict = None, dynamic_thresholds: Dict = None) -> Dict:
        """Calculate position size with regime-aware risk-based logic"""
        
        if equity <= 0:
            return {"shares": 0, "value": 0, "logic": "No equity", "regime_adj": 1.0}

        # Regime-based multiplier
        regime_mult = 1.0
        regime = (market_regime or {}).get("regime", "neutral")
        if regime in ("bearish", "neutral_bearish"):
            regime_mult = 0.5  # -50% in bearish
        elif regime == "high_volatility":
            regime_mult = 0.6  # -40% in high vol
        elif regime == "neutral":
            regime_mult = 0.85

        # Confidence-near-threshold reduction (if just barely above threshold, reduce size)
        threshold = 65 if classification == "DAY_TRADE" else 70
        if dynamic_thresholds:
            threshold = (dynamic_thresholds.get("dt_threshold", 80) if classification == "DAY_TRADE"
                         else dynamic_thresholds.get("lt_threshold", 75))
        margin = confidence - threshold
        conf_mult = 1.0
        if 0 <= margin <= 5:
            conf_mult = 0.6  # Just barely passed → 60% size
        elif 5 < margin <= 10:
            conf_mult = 0.8  # Moderate margin → 80%
        # Above 10 margin → full size

        if classification == "DAY_TRADE":
            if confidence >= 90:
                risk_pct = settings.dt_high_conf_risk_pct
                label = "High confidence"
            elif confidence >= 85:
                risk_pct = (settings.dt_risk_per_trade_pct + settings.dt_high_conf_risk_pct) / 2
                label = "Above average confidence"
            else:
                risk_pct = settings.dt_risk_per_trade_pct
                label = "Standard confidence"
            
            risk_amount = equity * risk_pct
            
            if stop_distance_pct > 0:
                position_value = risk_amount / (stop_distance_pct / 100)
            else:
                position_value = risk_amount * 10
            
            # Apply caps: max 5% per day trade
            max_value = equity * (PositionSizer.DT_MAX_PCT / 100)
            position_value = min(position_value, max_value)
            
        else:
            if confidence >= 90:
                alloc_pct = settings.lt_max_position_pct
                label = "High conviction"
            elif confidence >= 85:
                alloc_pct = settings.lt_max_position_pct * 0.7
                label = "Medium-high conviction"
            elif confidence >= 80:
                alloc_pct = settings.lt_max_position_pct * 0.5
                label = "Standard conviction"
            else:
                alloc_pct = settings.lt_max_position_pct * 0.3
                label = "Low conviction"
            
            position_value = equity * alloc_pct
            
            # Apply caps: max 20% per long-term position
            max_value = equity * (PositionSizer.LT_MAX_PCT / 100)
            position_value = min(position_value, max_value)
        
        # Apply regime and confidence multipliers
        position_value *= regime_mult * conf_mult
        
        price = signal.get("price", signal.get("entry", 0))
        if not price or price <= 0:
            return {"shares": 0, "value": 0, "logic": "No valid price", "regime_adj": regime_mult}
        
        shares = max(1, int(position_value / price))
        actual_value = shares * price
        pct_equity = round((actual_value / equity) * 100, 1) if equity > 0 else 0
        
        return {
            "shares": shares,
            "value": round(actual_value, 2),
            "pct_of_equity": pct_equity,
            "regime_adj": round(regime_mult, 2),
            "conf_adj": round(conf_mult, 2),
            "logic": f"{label} | {confidence}/100 conf | regime:{regime}({regime_mult:.0%}) | ${actual_value:,.0f} ({pct_equity}%)"
        }


# ===================== DAY TRADING ENGINE =====================

class DayTradingEngine:
    """Day trading buy/sell decision engine"""
    
    @staticmethod
    def evaluate_buy(ta_signal: Dict, news_data: Optional[Dict],
                     market_regime: Dict, settings: AutoTradeSettings) -> TradeExplanation:
        """Evaluate day trade using Technical Analysis signal as PRIMARY driver.
        News is used ONLY as a confidence boost, never as a gate.
        Technical structure drives the decision. No catalyst gate."""
        symbol = ta_signal.get("symbol", "")
        explanation = TradeExplanation(
            ticker=symbol,
            classification="DAY_TRADE",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        indicators = ta_signal.get("indicators", {})
        structure = ta_signal.get("structure", {})
        best_setup = ta_signal.get("best_setup")
        all_setups = ta_signal.get("all_setups", [])
        direction = ta_signal.get("direction", "NONE")
        mtf = ta_signal.get("mtf_confirmation", {})
        momentum_mode = ta_signal.get("momentum_mode", False)

        entry_reasons = list(ta_signal.get("entry_reasons", []))
        reject_reasons = []

        price = ta_signal.get("price", 0)
        confidence = ta_signal.get("confidence", 0)

        # === TECHNICAL SETUP EVALUATION (PRIMARY DRIVER) ===

        # 1. Must have a direction
        if direction == "NONE":
            reject_reasons.append("No trade direction identified from TA")
            explanation.action = "REJECT"
            explanation.reject_reasons = reject_reasons
            explanation.confidence_score = confidence
            explanation.key_indicators = {"direction": "NONE", "reject_stage": "no_direction"}
            return explanation

        # 2. Must have at least one setup
        if not best_setup:
            reject_reasons.append("No technical setup detected (breakout/FVG/VWAP reclaim)")
            explanation.action = "REJECT"
            explanation.reject_reasons = reject_reasons
            explanation.confidence_score = confidence
            explanation.key_indicators = {"direction": direction, "reject_stage": "no_setup"}
            return explanation

        # 3. Spread filter (<= 0.5%)
        spread = indicators.get("spread_pct", 0)
        if spread > 0.5:
            reject_reasons.append(f"Spread too wide: {spread:.2f}% (max 0.5%)")

        # 4. RelVol filter (>= 1.3, momentum mode bypasses)
        rel_vol = indicators.get("rel_vol", 0)
        if rel_vol < 1.3 and not momentum_mode:
            reject_reasons.append(f"RelVol too low: {rel_vol:.1f}x (min 1.3x)")
        elif rel_vol >= 2.0:
            entry_reasons.append(f"Strong volume surge: {rel_vol:.1f}x")

        # 5. Overextension check
        if ta_signal.get("overextended"):
            reject_reasons.append(f"Overextended: {ta_signal.get('overextension_reason', 'price too far from VWAP')}")

        # 6. Fake breakout penalty (not a hard reject, but heavy confidence penalty)
        fake = ta_signal.get("fake_breakout")
        if fake:
            reject_reasons.append(f"Fake breakout: {fake.get('reason', 'bull/bear trap detected')}")

        # 7. R:R ratio check
        rr = ta_signal.get("rr_ratio", 0)
        if rr >= 2.0:
            entry_reasons.append(f"Good R:R ratio: {rr:.1f}:1")
        elif 0 < rr < 1.2:
            reject_reasons.append(f"Poor R:R ratio: {rr:.1f}:1")

        # 8. Structure alignment
        struct_type = structure.get("structure", "ranging")
        if direction == "LONG" and struct_type == "bullish":
            entry_reasons.append("Bullish market structure (HH+HL)")
        elif direction == "SHORT" and struct_type == "bearish":
            entry_reasons.append("Bearish market structure (LH+LL)")
        elif struct_type == "ranging":
            entry_reasons.append("Ranging structure (breakout potential)")

        # 9. MTF confirmation
        if mtf.get("aligned"):
            entry_reasons.append(f"Multi-timeframe aligned ({mtf.get('score', 0)}/4)")

        # 10. RSI context
        rsi = indicators.get("rsi", 50)
        if direction == "LONG" and rsi > 75:
            reject_reasons.append(f"RSI overbought: {rsi:.0f}")
        elif direction == "SHORT" and rsi < 25:
            reject_reasons.append(f"RSI oversold: {rsi:.0f}")

        # === NEWS BOOST (SECONDARY - NOT A GATE) ===
        news_boost = 0
        if news_data and isinstance(news_data, dict):
            composite = _safe_float(news_data.get("composite_score", 0.5), 0.5)
            catalyst_score = _safe_float(news_data.get("catalyst_score", 0), 0)

            if composite >= 0.7 or catalyst_score >= 70:
                news_boost = 5
                entry_reasons.append(f"News sentiment boost: strong ({composite:.2f})")
            elif composite >= 0.55 or catalyst_score >= 50:
                news_boost = 2
                entry_reasons.append(f"News sentiment boost: moderate ({composite:.2f})")
            elif composite < 0.3:
                entry_reasons.append(f"News: negative sentiment ({composite:.2f}), no boost")

        confidence += news_boost

        # === MARKET REGIME SOFT CHECK ===
        regime = market_regime.get("regime", "neutral")
        if regime in ("bearish", "high_volatility") and direction == "LONG":
            confidence -= 3
            entry_reasons.append(f"Caution: long in {regime} market (-3 conf)")

        confidence = max(0, min(100, confidence))

        # === DECISION ===
        # Hard filter rejects: spread, RelVol, overextension
        hard_reject_keywords = ["spread too wide", "relvol too low", "overextended"]
        hard_rejects = [r for r in reject_reasons if any(kw in r.lower() for kw in hard_reject_keywords)]

        if hard_rejects:
            explanation.action = "REJECT"
            explanation.reject_reasons = reject_reasons
        elif len(reject_reasons) >= 3:
            explanation.action = "REJECT"
            explanation.reject_reasons = reject_reasons
        elif len(entry_reasons) >= 2 and len(reject_reasons) <= 1:
            explanation.action = "BUY"
            explanation.entry_reasons = entry_reasons
            explanation.reject_reasons = reject_reasons
        elif len(entry_reasons) >= 1:
            explanation.action = "WATCHLIST"
            explanation.entry_reasons = entry_reasons
            explanation.reject_reasons = reject_reasons
        else:
            explanation.action = "REJECT"
            explanation.reject_reasons = reject_reasons if reject_reasons else ["Insufficient technical signals"]

        # Exit plan from TA signal
        stop_loss = ta_signal.get("stop_loss", 0)
        take_profit = ta_signal.get("take_profit", 0)
        if stop_loss and take_profit and price:
            explanation.exit_plan = {
                "entry": round(price, 2),
                "take_profit": round(take_profit, 2),
                "take_profit_pct": round(((take_profit / price) - 1) * 100, 1) if price > 0 else 0,
                "stop_loss": round(stop_loss, 2),
                "stop_loss_pct": round(((stop_loss / price) - 1) * 100, 1) if price > 0 else 0,
                "rr_ratio": rr,
                "time_exit": f"{settings.dt_time_exit_days} day(s)"
            }

        explanation.confidence_score = confidence
        explanation.key_indicators = {
            "direction": direction,
            "best_setup": best_setup.get("type", "") if best_setup else "none",
            "setup_count": len(all_setups),
            "structure": struct_type,
            "rel_vol": rel_vol,
            "spread_pct": spread,
            "rsi": rsi,
            "ema_bullish": indicators.get("ema_bullish", False),
            "ema_bearish": indicators.get("ema_bearish", False),
            "macd_crossover": indicators.get("macd", {}).get("crossover", "none"),
            "vwap_distance_pct": indicators.get("vwap_distance_pct", 0),
            "above_vwap": indicators.get("above_vwap"),
            "mtf_aligned": mtf.get("aligned", False),
            "mtf_score": f"{mtf.get('score', 0)}/4",
            "momentum_mode": momentum_mode,
            "news_boost": news_boost,
            "rr_ratio": rr,
            "overextended": ta_signal.get("overextended", False),
            "fake_breakout": bool(fake),
        }

        return explanation
    
    @staticmethod
    def evaluate_sell(position: Dict, current_price: float, entry_price: float,
                      settings: AutoTradeSettings, entry_time: datetime) -> TradeExplanation:
        """Evaluate if a day trade position should be sold"""
        ticker = position.get("symbol", "")
        explanation = TradeExplanation(
            ticker=ticker,
            classification="DAY_TRADE",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        exit_reasons = []
        pnl_pct = ((current_price / entry_price) - 1) * 100 if entry_price > 0 else 0
        
        # Take profit
        if pnl_pct >= settings.dt_take_profit_pct:
            exit_reasons.append(f"Take profit hit: +{pnl_pct:.1f}% (target: {settings.dt_take_profit_pct}%)")
        
        # Stop loss
        if pnl_pct <= -settings.dt_stop_loss_pct:
            exit_reasons.append(f"Stop loss hit: {pnl_pct:.1f}% (limit: -{settings.dt_stop_loss_pct}%)")
        
        # Time exit
        if entry_time:
            hours_held = (datetime.now(timezone.utc) - entry_time).total_seconds() / 3600
            max_hours = settings.dt_time_exit_days * 24
            if hours_held >= max_hours:
                exit_reasons.append(f"Time exit: held {hours_held:.0f}h (max: {max_hours}h)")
        
        if exit_reasons:
            explanation.action = "SELL"
            explanation.exit_reasons = exit_reasons
        else:
            explanation.action = "HOLD"
        
        explanation.key_indicators = {
            "pnl_pct": round(pnl_pct, 2),
            "current_price": current_price,
            "entry_price": entry_price
        }
        
        return explanation


# ===================== LONG-TERM INVESTMENT ENGINE =====================

class LongTermEngine:
    """Long-term investment buy/sell decision engine"""
    
    @staticmethod
    def evaluate_buy(signal: Dict, market_regime: Dict, settings: AutoTradeSettings) -> TradeExplanation:
        """Evaluate if a long-term investment buy should be triggered.
        Quality filters: reject weak revenue, poor FCF, excessive debt, value traps."""
        ticker = signal.get("symbol", "")
        explanation = TradeExplanation(
            ticker=ticker,
            classification="LONG_TERM",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        entry_reasons = []
        reject_reasons = []
        diagnostic_tags = []
        
        val = signal.get("valuation_summary", {})
        bq = signal.get("business_quality", {})
        gp = signal.get("growth_profile", {})
        hp = signal.get("historical_performance", {})
        sd = signal.get("score_drivers", {})
        
        # 1. Valuation check
        val_status = val.get("valuation_status", "")
        upside = _safe_float(val.get("upside_potential"))
        if "Undervalued" in val_status:
            entry_reasons.append(f"Undervalued: {upside:.0f}% upside potential")
        elif "Fair" in val_status:
            entry_reasons.append(f"Fair value with {upside:.0f}% potential")
        elif "Overvalued" in val_status or "Premium" in val_status:
            reject_reasons.append(f"Overvalued: {val_status}")
        
        # 2. Revenue & earnings growth (QUALITY FILTER)
        rev = _safe_float(gp.get("revenue_growth"))
        eps = _safe_float(gp.get("earnings_growth"))
        growth_trend = gp.get("growth_trend", "")
        
        if rev > 10:
            entry_reasons.append(f"Strong revenue growth: +{rev:.0f}%")
        elif rev > 0:
            entry_reasons.append(f"Positive revenue: +{rev:.0f}%")
        elif rev < -5:
            reject_reasons.append(f"Revenue declining: {rev:.0f}%")
            diagnostic_tags.append("weak_revenue")
        
        if eps > 10:
            entry_reasons.append(f"Strong earnings growth: +{eps:.0f}%")
        elif eps < -10:
            reject_reasons.append(f"Earnings declining: {eps:.0f}%")
        
        if growth_trend == "Decelerating":
            reject_reasons.append("Growth decelerating")
            diagnostic_tags.append("declining_growth")
        elif growth_trend == "Accelerating":
            entry_reasons.append("Growth accelerating")
        
        # 3. Business quality
        quality = bq.get("quality_rating", "")
        if quality in ["Excellent", "Very Good"]:
            entry_reasons.append(f"Business quality: {quality}")
        elif quality in ["Poor", "Very Poor"]:
            reject_reasons.append(f"Weak business quality: {quality}")
            diagnostic_tags.append("poor_quality")
        
        # 4. Margins & profitability
        margin = _safe_float(bq.get("operating_margin"))
        roe = _safe_float(bq.get("roe"))
        if margin > 20:
            entry_reasons.append(f"Strong margins: {margin:.0f}%")
        elif margin < 5 and margin != 0:
            reject_reasons.append(f"Thin margins: {margin:.0f}%")
        if roe > 15:
            entry_reasons.append(f"Good ROE: {roe:.0f}%")
        elif roe < 5 and roe != 0:
            diagnostic_tags.append("low_roe")
        
        # 5. Debt health (QUALITY FILTER)
        de_ratio = bq.get("debt_to_equity")
        if de_ratio is not None:
            de_ratio = _safe_float(de_ratio)
            if de_ratio < 0.5:
                entry_reasons.append(f"Low debt: D/E={de_ratio:.1f}")
            elif de_ratio > 2.0:
                reject_reasons.append(f"Excessive debt: D/E={de_ratio:.1f}")
                diagnostic_tags.append("excessive_debt")
            elif de_ratio > 1.5:
                reject_reasons.append(f"High debt: D/E={de_ratio:.1f}")
        
        # 6. Free Cash Flow quality (QUALITY FILTER)
        fcf_margin = _safe_float(bq.get("fcf_margin", bq.get("free_cash_flow_margin")))
        fcf_yield = _safe_float(val.get("fcf_yield", bq.get("fcf_yield")))
        if fcf_margin > 10:
            entry_reasons.append(f"Strong FCF margin: {fcf_margin:.0f}%")
        elif fcf_margin < 0:
            reject_reasons.append(f"Negative FCF margin: {fcf_margin:.0f}%")
            diagnostic_tags.append("poor_fcf")
        
        # 7. VALUE TRAP DETECTION
        # Low valuation + weak fundamentals = value trap
        is_cheap = "Undervalued" in val_status or (upside > 20)
        has_weak_fundamentals = (
            (rev < 0 and eps < 0) or
            (quality in ("Poor", "Very Poor")) or
            (margin < 5 and roe < 5 and margin != 0 and roe != 0) or
            (growth_trend == "Decelerating" and rev < 5)
        )
        if is_cheap and has_weak_fundamentals:
            reject_reasons.append("VALUE TRAP: cheap valuation but weak fundamentals")
            diagnostic_tags.append("value_trap")
        
        # 8. Historical track record
        if hp:
            hist_rating = hp.get("historical_rating", "")
            cagr_10 = _safe_float(hp.get("cagr_10yr"))
            if hist_rating in ["Exceptional", "Strong"]:
                entry_reasons.append(f"Historical: {hist_rating}" + (f" ({cagr_10:.0f}% 10yr CAGR)" if cagr_10 else ""))
            elif hist_rating == "Poor":
                reject_reasons.append("Poor historical performance")
        
        # 9. Long-term trend
        if hp and hp.get("sma_200_trend") == "Below":
            reject_reasons.append("Below 200-day SMA (downtrend)")
        elif hp and hp.get("sma_200_trend") == "Above":
            entry_reasons.append("Above 200-day SMA (uptrend)")
        
        # 10. Industry outlook check
        sector = signal.get("sector", "")
        # Cyclical sectors get extra scrutiny in bearish regime
        regime = market_regime.get("regime", "neutral")
        cyclical_sectors = ["Consumer Cyclical", "Energy", "Basic Materials", "Real Estate"]
        if sector in cyclical_sectors and regime in ("bearish", "neutral_bearish"):
            reject_reasons.append(f"Cyclical sector ({sector}) in {regime} regime")
            diagnostic_tags.append("negative_industry_outlook")
        
        # === DECISION (stricter: require 4+ entry with <=1 reject for BUY) ===
        buy_strength = len(entry_reasons)
        reject_strength = len(reject_reasons)
        
        if buy_strength >= 5 and reject_strength <= 1:
            explanation.action = "BUY"
            explanation.entry_reasons = entry_reasons
        elif buy_strength >= 4 and reject_strength == 0:
            explanation.action = "BUY"
            explanation.entry_reasons = entry_reasons
        elif reject_strength >= 3:
            explanation.action = "REJECT"
            explanation.reject_reasons = reject_reasons
        elif buy_strength >= 3 and reject_strength <= 1:
            explanation.action = "WATCHLIST"
            explanation.entry_reasons = entry_reasons
            explanation.reject_reasons = reject_reasons
        else:
            explanation.action = "REJECT"
            explanation.reject_reasons = reject_reasons if reject_reasons else ["Insufficient investment thesis"]
        
        explanation.key_indicators = {
            "valuation_status": val_status,
            "upside_potential": upside,
            "revenue_growth": rev,
            "earnings_growth": eps,
            "quality_rating": quality,
            "operating_margin": margin,
            "roe": roe,
            "de_ratio": de_ratio if de_ratio is not None else None,
            "historical_rating": hp.get("historical_rating") if hp else None,
            "sma_200": hp.get("sma_200_trend") if hp else None,
            "diagnostic_tags": diagnostic_tags,
        }
        
        return explanation
    
    @staticmethod
    def evaluate_sell(position: Dict, investment_signal: Optional[Dict],
                      current_price: float, entry_price: float,
                      settings: AutoTradeSettings) -> TradeExplanation:
        """Evaluate if a long-term position should be sold"""
        ticker = position.get("symbol", "")
        explanation = TradeExplanation(
            ticker=ticker,
            classification="LONG_TERM",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        exit_reasons = []
        pnl_pct = ((current_price / entry_price) - 1) * 100 if entry_price > 0 else 0
        
        # Trailing stop
        if pnl_pct <= -settings.lt_trailing_stop_pct:
            exit_reasons.append(f"Trailing stop hit: {pnl_pct:.1f}% (limit: -{settings.lt_trailing_stop_pct}%)")
        
        # Thesis break checks
        if investment_signal:
            bq = investment_signal.get("business_quality", {})
            gp = investment_signal.get("growth_profile", {})
            val = investment_signal.get("valuation_summary", {})
            
            # Revenue collapse
            rev = _safe_float(gp.get("revenue_growth"))
            if rev < -10:
                exit_reasons.append(f"Revenue deterioration: {rev:.0f}%")
            
            # Quality collapse
            quality = bq.get("quality_rating", "")
            if quality in ["Poor", "Very Poor"]:
                exit_reasons.append(f"Business quality collapsed: {quality}")
            
            # Severe overvaluation
            val_status = val.get("valuation_status", "")
            if "Overvalued" in val_status:
                pe = _safe_float(val.get("pe_ratio"))
                if pe > 50:
                    exit_reasons.append(f"Severely overvalued: P/E={pe:.0f}")
        
        # Portfolio rebalance (position too large)
        # This would be checked at portfolio level
        
        if exit_reasons:
            explanation.action = "SELL"
            explanation.exit_reasons = exit_reasons
        else:
            explanation.action = "HOLD"
        
        explanation.key_indicators = {
            "pnl_pct": round(pnl_pct, 2),
            "current_price": current_price,
            "entry_price": entry_price
        }
        
        return explanation


# ===================== AUTO TRADE ORCHESTRATOR =====================

class AutoTradeOrchestrator:
    """Main orchestrator that ties all components together"""
    
    def __init__(self, db, api_client, execution_engine):
        self.db = db
        self.api_client = api_client
        self.execution_engine = execution_engine
        self.regime_detector = MarketRegimeDetector(api_client)
        self.risk_manager = RiskManager(db)
    
    async def get_settings(self) -> AutoTradeSettings:
        doc = await self.db.auto_trade_settings.find_one({"_id": "config"})
        if doc:
            doc.pop("_id", None)
            return AutoTradeSettings(**doc)
        return AutoTradeSettings()
    
    async def save_settings(self, settings: AutoTradeSettings) -> Dict:
        data = settings.dict()
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self.db.auto_trade_settings.update_one(
            {"_id": "config"}, {"$set": data}, upsert=True
        )
        return data
    
    async def get_account(self) -> Dict:
        """Get Alpaca account info"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.execution_engine.alpaca_url}/v2/account",
                    headers=self.execution_engine.headers,
                    timeout=10
                )
                if resp.status_code == 200:
                    return resp.json()
        except:
            pass
        return {"equity": "0", "buying_power": "0", "cash": "0"}
    
    async def get_positions(self) -> List[Dict]:
        """Get current Alpaca positions"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.execution_engine.alpaca_url}/v2/positions",
                    headers=self.execution_engine.headers,
                    timeout=10
                )
                if resp.status_code == 200:
                    return resp.json()
        except:
            pass
        return []
    
    async def scan_opportunities(self) -> Dict:
        """Tiered TA pipeline: Tier 1 fast scan → composite ranking → Tier 2 deep analysis.
        Day trades: TA engine (Polygon OHLCV) → setup detection → confidence → risk check.
        Long-term: Existing fundamental scoring.
        News is used ONLY as a confidence boost for day trades."""
        import time as _time
        cycle_start = _time.monotonic()

        settings = await self.get_settings()
        market_regime = await self.regime_detector.detect()

        dynamic = DynamicThresholdManager.get_thresholds(market_regime, settings)
        dt_threshold = dynamic["dt_threshold"]
        lt_threshold = dynamic["lt_threshold"]
        risk_mode = dynamic["risk_mode"]

        funnel = TradePipelineFunnel()
        diagnostics = ZeroTradeDiagnostics()

        # Get cached signals from DB
        trading_signals = await self.db.trading_signals.find({}, {"_id": 0}).to_list(2000)
        investment_signals = await self.db.investment_signals.find({}, {"_id": 0}).to_list(2000)

        inv_lookup = {s["symbol"]: s for s in investment_signals if s.get("symbol")}
        trade_lookup = {s["symbol"]: s for s in trading_signals if s.get("symbol")}

        all_symbols = set(list(trade_lookup.keys()) + list(inv_lookup.keys()))
        funnel.record("universe_scanned", len(all_symbols))

        dt_max_pos = DynamicThresholdManager.get_max_positions("DAY_TRADE", settings, market_regime)
        lt_max_pos = DynamicThresholdManager.get_max_positions("LONG_TERM", settings, market_regime)

        from technical_analysis_engine import TechnicalSignalGenerator, TACache, BarCache
        TACache.reset_counters()

        # === PHASE 1: Pre-filter liquid stocks for TA (volume >= 0.5) ===
        dt_prefilter_symbols = []
        if settings.dt_enabled:
            for symbol in all_symbols:
                t_sig = trade_lookup.get(symbol)
                if t_sig:
                    indicators = t_sig.get("indicators", {})
                    vol_ratio = indicators.get("volume_ratio", 0)
                    if vol_ratio >= 0.5:
                        dt_prefilter_symbols.append(symbol)
                    else:
                        funnel.reject("pre_filter_low_volume")

        funnel.record("prefilter_passed", len(dt_prefilter_symbols))

        # === PHASE 2 (TIER 1): Fast scan on top 80 most liquid names ===
        # Sort by volume ratio descending for initial ordering, take top 80
        dt_prefilter_symbols.sort(
            key=lambda s: trade_lookup.get(s, {}).get("indicators", {}).get("volume_ratio", 0),
            reverse=True
        )
        tier1_candidates = dt_prefilter_symbols[:80]

        tier1_start = _time.monotonic()
        tier1_results = await TechnicalSignalGenerator.batch_analyze_fast(tier1_candidates, max_concurrent=10)
        tier1_duration = round(_time.monotonic() - tier1_start, 1)

        # Compute composite prefilter score for each Tier 1 result
        for r in tier1_results:
            r["tier1_score"] = TechnicalSignalGenerator.compute_tier1_score(r)

        # Tier 1 early rejection: remove obviously bad candidates
        tier1_passed = []
        tier1_rejected_early = []
        for r in tier1_results:
            indicators = r.get("indicators", {})
            spread = indicators.get("spread_pct", 0)
            rel_vol = indicators.get("rel_vol", 0)
            overextended = r.get("overextended", False)

            # Tier 1 quality gates (same discipline, applied early)
            if spread > 0.5:
                tier1_rejected_early.append({**r, "tier1_reject": "wide_spread"})
                funnel.reject("t1_wide_spread")
            elif rel_vol < 0.5:
                tier1_rejected_early.append({**r, "tier1_reject": "illiquid"})
                funnel.reject("t1_illiquid")
            elif overextended:
                tier1_rejected_early.append({**r, "tier1_reject": "overextended"})
                funnel.reject("t1_overextended")
            elif r.get("direction") == "NONE" and not r.get("best_setup"):
                tier1_rejected_early.append({**r, "tier1_reject": "no_signal"})
                funnel.reject("t1_no_signal")
            else:
                tier1_passed.append(r)

        # Rank Tier 1 passed by composite score and take top 20 for deep analysis
        tier1_passed.sort(key=lambda x: x.get("tier1_score", 0), reverse=True)
        tier2_candidates = tier1_passed[:20]

        funnel.record("ta_analyzed", len(tier1_results))

        # === PHASE 3 (TIER 2): Deep multi-timeframe analysis on top candidates ===
        tier2_symbols = [r["symbol"] for r in tier2_candidates]
        tier2_start = _time.monotonic()
        tier2_results = await TechnicalSignalGenerator.batch_analyze(tier2_symbols, max_concurrent=8)
        tier2_duration = round(_time.monotonic() - tier2_start, 1)

        # Merge: prefer Tier 2 (full analysis) over Tier 1 (fast)
        tier2_lookup = {r["symbol"]: r for r in tier2_results}
        final_ta_results = []
        for r in tier1_passed:
            sym = r["symbol"]
            if sym in tier2_lookup:
                deep = tier2_lookup[sym]
                deep["tier1_score"] = r.get("tier1_score", 0)
                deep["analysis_mode"] = "full"
                final_ta_results.append(deep)
            else:
                final_ta_results.append(r)

        # Also add Tier 1 results that didn't go to Tier 2 (still valid candidates)
        tier2_set = set(tier2_symbols)
        for r in tier1_passed:
            if r["symbol"] not in tier2_set and r not in final_ta_results:
                final_ta_results.append(r)

        ta_lookup = {r["symbol"]: r for r in final_ta_results}

        # === PHASE 4: Evaluate final TA results for day trades ===
        day_trade_candidates = []
        long_term_candidates = []
        watchlist = []
        rejected = []
        setup_count = 0
        filters_passed_count = 0

        for ta_sig in final_ta_results:
            symbol = ta_sig["symbol"]
            cached_sig = trade_lookup.get(symbol, {})

            news_data = None
            if isinstance(cached_sig.get("news_sentiment"), dict):
                news_data = cached_sig["news_sentiment"]
            elif cached_sig.get("news_impact"):
                news_data = {"composite_score": 0.5 + (cached_sig.get("news_impact", 0) / 100)}

            explanation = DayTradingEngine.evaluate_buy(ta_sig, news_data, market_regime, settings)
            confidence = explanation.confidence_score

            if ta_sig.get("best_setup"):
                setup_count += 1

            indicators = ta_sig.get("indicators", {})
            spread_ok = indicators.get("spread_pct", 0) <= 0.5
            relvol_ok = indicators.get("rel_vol", 0) >= 1.3 or ta_sig.get("momentum_mode", False)
            not_overextended = not ta_sig.get("overextended", False)
            if spread_ok and relvol_ok and not_overextended:
                filters_passed_count += 1

            entry = {
                "symbol": symbol,
                "classification": "DAY_TRADE",
                "confidence": confidence,
                "action": explanation.action,
                "explanation": explanation.dict(),
                "signal": ta_sig,
                "direction": ta_sig.get("direction", "NONE"),
                "best_setup": ta_sig.get("best_setup", {}).get("type", "none") if ta_sig.get("best_setup") else "none",
                "tier1_score": ta_sig.get("tier1_score", 0),
                "analysis_mode": ta_sig.get("analysis_mode", "fast"),
                "dt_score": confidence,
                "lt_score": 0,
            }

            if explanation.action == "BUY" and confidence >= dt_threshold:
                funnel.record("confidence_passed")
                day_trade_candidates.append(entry)
            elif explanation.action == "BUY" and confidence >= (dt_threshold - 10):
                diagnostics.add_near_miss(
                    symbol, "DAY_TRADE", confidence, "NEAR_MISS",
                    explanation.reject_reasons or [f"Confidence {confidence} < {dt_threshold}"])
                watchlist.append(entry)
            elif explanation.action == "WATCHLIST":
                if confidence >= (dt_threshold - 10):
                    diagnostics.add_near_miss(
                        symbol, "DAY_TRADE", confidence, "WATCHLIST",
                        explanation.reject_reasons)
                watchlist.append(entry)
            else:
                for reason in explanation.reject_reasons[:3]:
                    funnel.reject(reason[:60])
                rejected.append(entry)

        # === PHASE 5: Process Long-Term candidates (unchanged logic) ===
        for symbol in all_symbols:
            i_sig = inv_lookup.get(symbol)
            if not i_sig or not settings.lt_enabled:
                continue
            if symbol in ta_lookup:
                continue

            t_sig = trade_lookup.get(symbol)
            cls_result = StockClassifier.classify(t_sig, i_sig)
            classification = cls_result["classification"]

            if classification in ("LONG_TERM", "WATCHLIST") and i_sig:
                confidence = ConfidenceScoringEngine.score_long_term(i_sig, market_regime)
                explanation = LongTermEngine.evaluate_buy(i_sig, market_regime, settings)
                explanation.confidence_score = confidence

                entry = {
                    "symbol": symbol,
                    "classification": "LONG_TERM",
                    "confidence": confidence,
                    "action": explanation.action,
                    "explanation": explanation.dict(),
                    "signal": i_sig,
                    "dt_score": cls_result["day_trading_score"],
                    "lt_score": cls_result["long_term_score"],
                }

                if explanation.action == "BUY" and confidence >= lt_threshold:
                    funnel.record("confidence_passed")
                    long_term_candidates.append(entry)
                elif explanation.action == "BUY" and confidence >= (lt_threshold - 10):
                    diagnostics.add_near_miss(
                        symbol, "LONG_TERM", confidence, "NEAR_MISS",
                        explanation.reject_reasons or [f"Confidence {confidence} < {lt_threshold}"])
                    watchlist.append(entry)
                elif explanation.action == "WATCHLIST":
                    if confidence >= (lt_threshold - 10):
                        diagnostics.add_near_miss(
                            symbol, "LONG_TERM", confidence, "WATCHLIST",
                            explanation.reject_reasons)
                    watchlist.append(entry)
                else:
                    tags = explanation.key_indicators.get("diagnostic_tags", [])
                    for tag in tags:
                        funnel.reject(tag)
                    rejected.append(entry)

        funnel.record("setup_found", setup_count)
        funnel.record("filters_passed", filters_passed_count)

        day_trade_candidates.sort(key=lambda x: x["confidence"], reverse=True)
        long_term_candidates.sort(key=lambda x: x["confidence"], reverse=True)

        # Zero-trade diagnosis
        if not day_trade_candidates:
            regime = market_regime.get("regime", "neutral")
            if regime in ("bearish", "high_volatility"):
                diagnostics.add_reason(f"Market regime ({regime}) reducing day trade opportunities")
            if len(tier1_results) == 0:
                diagnostics.add_reason("No stocks returned valid TA data from Polygon")
            elif setup_count == 0:
                diagnostics.add_reason(f"TA analyzed {len(tier1_results)} stocks but no technical setups found")
            elif filters_passed_count == 0:
                diagnostics.add_reason(f"{setup_count} setups found but all filtered by spread/RelVol/overextension")
            else:
                diagnostics.add_reason(
                    f"{filters_passed_count} stocks passed filters but confidence below threshold ({dt_threshold})")

        no_trade_summary = diagnostics.build_no_trade_summary(
            len(day_trade_candidates), len(long_term_candidates), market_regime)

        cycle_duration = round(_time.monotonic() - cycle_start, 1)
        cache_stats = TACache.stats()
        bar_cache_stats = BarCache.stats()

        # Timing diagnostics
        timing = {
            "total_cycle_sec": cycle_duration,
            "tier1_scan_sec": tier1_duration,
            "tier2_scan_sec": tier2_duration,
            "tier1_symbols": len(tier1_candidates),
            "tier1_results": len(tier1_results),
            "tier1_passed": len(tier1_passed),
            "tier1_rejected_early": len(tier1_rejected_early),
            "tier2_symbols": len(tier2_symbols),
            "tier2_results": len(tier2_results),
            "final_evaluated": len(final_ta_results),
            "ta_cache": cache_stats,
            "bar_cache": bar_cache_stats,
        }

        logger.info(
            f"Scan complete in {cycle_duration}s | T1: {len(tier1_results)}/{len(tier1_candidates)} in {tier1_duration}s | "
            f"T2: {len(tier2_results)}/{len(tier2_symbols)} in {tier2_duration}s | "
            f"DT: {len(day_trade_candidates)}, LT: {len(long_term_candidates)} | "
            f"Cache hit: {cache_stats.get('hit_rate', 0)}%"
        )

        return {
            "auto_enabled": settings.auto_enabled,
            "market_regime": market_regime,
            "day_trades": day_trade_candidates[:20],
            "long_term": long_term_candidates[:20],
            "watchlist": sorted(watchlist, key=lambda x: x.get("confidence", 0), reverse=True)[:30],
            "rejected_details": sorted(
                [r for r in rejected if r.get("classification") == "DAY_TRADE"],
                key=lambda x: x.get("confidence", 0), reverse=True
            )[:20] + sorted(
                [r for r in rejected if r.get("classification") != "DAY_TRADE"],
                key=lambda x: x.get("confidence", 0), reverse=True
            )[:15],
            "stats": {
                "total_scanned": len(all_symbols),
                "ta_analyzed": len(tier1_results),
                "tier1_passed": len(tier1_passed),
                "tier2_deep": len(tier2_results),
                "setups_found": setup_count,
                "filters_passed": filters_passed_count,
                "day_trade_candidates": len(day_trade_candidates),
                "long_term_candidates": len(long_term_candidates),
                "watchlist": len(watchlist),
                "rejected": len(rejected),
            },
            "timing": timing,
            "dynamic_thresholds": dynamic,
            "risk_mode": risk_mode,
            "pipeline_funnel": funnel.to_dict(),
            "no_trade_summary": no_trade_summary,
            "settings": settings.dict(),
        }
    
    async def execute_auto_cycle(self) -> Dict:
        """Run one full auto-trade cycle: scan → classify → risk check → execute"""
        settings = await self.get_settings()
        
        if not settings.auto_enabled:
            return {"status": "disabled", "message": "Auto-trading is OFF"}
        
        if settings.emergency_pause:
            return {"status": "paused", "message": "Emergency pause active"}
        
        if settings.alert_only_mode:
            # Just scan and log, don't execute
            opportunities = await self.scan_opportunities()
            return {"status": "alert_only", "opportunities": opportunities["stats"]}
        
        # Get account and positions
        account = await self.get_account()
        positions = await self.get_positions()
        market_regime = await self.regime_detector.detect()
        
        opportunities = await self.scan_opportunities()
        
        executed = []
        skipped = []
        
        # Process day trade candidates
        for candidate in opportunities["day_trades"][:5]:  # Top 5
            symbol = candidate["symbol"]
            confidence = candidate["confidence"]
            signal = candidate.get("signal", {})
            
            approved, checks = await self.risk_manager.check_all(
                signal, confidence, "DAY_TRADE", settings, account, positions, market_regime
            )
            
            if approved:
                # Calculate position size using TA-computed stop loss
                ta_price = signal.get("price", 0)
                ta_stop = signal.get("stop_loss", 0)
                if ta_price > 0 and ta_stop > 0:
                    stop_pct = abs((ta_price - ta_stop) / ta_price * 100)
                else:
                    stop_pct = abs(signal.get("indicators", {}).get("atr_pct", settings.dt_stop_loss_pct))
                size = PositionSizer.calculate(
                    "DAY_TRADE", confidence, settings,
                    float(account.get("equity", 0)), stop_pct, signal
                )
                
                if size["shares"] > 0:
                    # Execute via Alpaca
                    result = await self._place_order(symbol, size["shares"], "buy", "DAY_TRADE", candidate)
                    if result.get("success"):
                        executed.append(result)
                    else:
                        skipped.append({"symbol": symbol, "reason": result.get("error", "Order failed")})
            else:
                skipped.append({"symbol": symbol, "reason": "; ".join(c for c in checks if "VIOLATION" in c)})
        
        # Process long-term candidates
        for candidate in opportunities["long_term"][:3]:  # Top 3
            symbol = candidate["symbol"]
            confidence = candidate["confidence"]
            signal = candidate.get("signal", {})
            
            approved, checks = await self.risk_manager.check_all(
                signal, confidence, "LONG_TERM", settings, account, positions, market_regime
            )
            
            if approved:
                size = PositionSizer.calculate(
                    "LONG_TERM", confidence, settings,
                    float(account.get("equity", 0)), settings.lt_trailing_stop_pct, signal
                )
                
                if size["shares"] > 0:
                    result = await self._place_order(symbol, size["shares"], "buy", "LONG_TERM", candidate)
                    if result.get("success"):
                        executed.append(result)
                    else:
                        skipped.append({"symbol": symbol, "reason": result.get("error", "Order failed")})
            else:
                skipped.append({"symbol": symbol, "reason": "; ".join(c for c in checks if "VIOLATION" in c)})
        
        # Monitor existing positions for sell signals
        sell_results = await self._monitor_positions(settings, market_regime)
        
        return {
            "status": "completed",
            "cycle_time": datetime.now(timezone.utc).isoformat(),
            "executed_buys": len(executed),
            "skipped": len(skipped),
            "sells_triggered": len(sell_results),
            "details": {
                "buys": executed,
                "skipped": skipped,
                "sells": sell_results
            },
            "market_regime": market_regime
        }
    
    async def _place_order(self, symbol: str, shares: int, side: str, 
                           classification: str, candidate: Dict) -> Dict:
        """Place order via Alpaca"""
        try:
            from server import PaperExecutionEngine
            if symbol.upper() in PaperExecutionEngine.RISKY_STOCKS:
                return {"success": False, "error": f"{symbol} is blocked (risky stock)"}
            
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.execution_engine.alpaca_url}/v2/orders",
                    headers=self.execution_engine.headers,
                    json={
                        "symbol": symbol,
                        "qty": str(shares),
                        "side": side,
                        "type": "market",
                        "time_in_force": "day"
                    },
                    timeout=10
                )
                
                if resp.status_code in [200, 201]:
                    order = resp.json()
                    # Log the trade
                    await self.db.auto_trade_log.insert_one({
                        "symbol": symbol,
                        "action": side.upper(),
                        "shares": shares,
                        "classification": classification,
                        "confidence": candidate.get("confidence", 0),
                        "explanation": candidate.get("explanation", {}),
                        "order_id": order.get("id"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    })
                    return {"success": True, "symbol": symbol, "shares": shares, "order_id": order.get("id")}
                else:
                    return {"success": False, "error": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _monitor_positions(self, settings: AutoTradeSettings, market_regime: Dict) -> List[Dict]:
        """Check existing positions for sell signals"""
        positions = await self.get_positions()
        sell_results = []
        
        for pos in positions:
            symbol = pos.get("symbol", "")
            current_price = float(pos.get("current_price", 0))
            entry_price = float(pos.get("avg_entry_price", 0))
            
            if not current_price or not entry_price:
                continue
            
            # Check trade log for classification
            trade_log = await self.db.auto_trade_log.find_one(
                {"symbol": symbol, "action": "BUY"},
                sort=[("timestamp", -1)]
            )
            
            classification = trade_log.get("classification", "DAY_TRADE") if trade_log else "DAY_TRADE"
            entry_time = None
            if trade_log and trade_log.get("timestamp"):
                ts = trade_log["timestamp"]
                if isinstance(ts, str):
                    try:
                        entry_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except:
                        pass
            
            if classification == "DAY_TRADE":
                explanation = DayTradingEngine.evaluate_sell(
                    pos, current_price, entry_price, settings, entry_time
                )
            else:
                inv_signal = await self.db.investment_signals.find_one(
                    {"symbol": symbol}, {"_id": 0}
                )
                explanation = LongTermEngine.evaluate_sell(
                    pos, inv_signal, current_price, entry_price, settings
                )
            
            if explanation.action == "SELL":
                qty = int(pos.get("qty", 0))
                if qty > 0:
                    result = await self._place_order(symbol, qty, "sell", classification, {
                        "confidence": 0,
                        "explanation": explanation.dict()
                    })
                    if result.get("success"):
                        pnl = (current_price - entry_price) * qty
                        await self.db.auto_trade_log.update_one(
                            {"order_id": result.get("order_id")},
                            {"$set": {"pnl": round(pnl, 2)}}
                        )
                        sell_results.append({
                            "symbol": symbol,
                            "reason": explanation.exit_reasons,
                            "pnl": round(pnl, 2)
                        })
        
        return sell_results
    
    async def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get auto-trade history with explanations"""
        cursor = self.db.auto_trade_log.find(
            {}, {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def get_status(self) -> Dict:
        """Get current auto-trade system status"""
        settings = await self.get_settings()
        account = await self.get_account()
        positions = await self.get_positions()
        market_regime = await self.regime_detector.detect()
        
        # Today's stats
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_trades = await self.db.auto_trade_log.count_documents({"date": today})
        today_buys = await self.db.auto_trade_log.count_documents({"date": today, "action": "BUY"})
        today_sells = await self.db.auto_trade_log.count_documents({"date": today, "action": "SELL"})
        
        # Daily PnL
        sell_trades = await self.db.auto_trade_log.find(
            {"date": today, "action": "SELL"}, {"_id": 0, "pnl": 1}
        ).to_list(100)
        daily_pnl = sum(t.get("pnl", 0) for t in sell_trades)
        
        return {
            "auto_enabled": settings.auto_enabled,
            "emergency_pause": settings.emergency_pause,
            "alert_only": settings.alert_only_mode,
            "market_regime": market_regime,
            "account": {
                "equity": account.get("equity"),
                "buying_power": account.get("buying_power"),
                "cash": account.get("cash")
            },
            "positions": len(positions),
            "today": {
                "trades": today_trades,
                "buys": today_buys,
                "sells": today_sells,
                "pnl": round(daily_pnl, 2)
            },
            "settings": settings.dict()
        }
