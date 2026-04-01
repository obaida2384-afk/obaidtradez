"""
Performance Tracker — Structured evaluation framework for paper trading validation.
Tracks: per-trade analytics, session summaries, pipeline efficiency, risk compliance,
market regime tagging, and trade quality analysis.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

ET_OFFSET = timedelta(hours=-4)


def _now_et():
    return datetime.now(timezone.utc) + ET_OFFSET


def _now_utc():
    return datetime.now(timezone.utc)


def _time_window(et_time) -> str:
    """Classify time into morning/midday/power_hour windows."""
    h = et_time.hour + et_time.minute / 60.0
    if 9.5 <= h < 11.5:
        return "morning_power"   # 9:30-11:30 AM
    elif 11.5 <= h < 14.0:
        return "midday"          # 11:30 AM - 2:00 PM
    elif 14.0 <= h < 16.0:
        return "afternoon_power" # 2:00 - 4:00 PM
    else:
        return "off_hours"


class PerformanceTracker:
    """Tracks and analyzes trading performance across sessions."""

    def __init__(self, db):
        self.db = db

    # =================== TRADE LOGGING ===================

    async def log_trade_entry(self, trade_data: Dict):
        """Log a trade entry with full context for post-session analysis."""
        now_et = _now_et()
        record = {
            "type": "entry",
            "symbol": trade_data.get("symbol", ""),
            "classification": trade_data.get("classification", "DAY_TRADE"),
            "action": "BUY",
            "shares": trade_data.get("shares", 0),
            "entry_price": trade_data.get("entry_price", 0),
            "position_value": trade_data.get("position_value", 0),
            "position_pct": trade_data.get("position_pct", 0),
            "confidence": trade_data.get("confidence", 0),
            "stop_loss": trade_data.get("stop_loss", 0),
            "take_profit": trade_data.get("take_profit", 0),
            "partial_target": trade_data.get("partial_target", 0),
            # Signal quality
            "entry_signals": trade_data.get("entry_reasons", []),
            "signal_count": trade_data.get("signal_count", 0),
            "signals_aligned": trade_data.get("signals_aligned", ""),
            "best_setup": trade_data.get("best_setup", ""),
            "direction": trade_data.get("direction", ""),
            "momentum_mode": trade_data.get("momentum_mode", False),
            "is_top_mover": trade_data.get("is_top_mover", False),
            "mover_source": trade_data.get("source", "universe"),
            # Market context
            "market_regime": trade_data.get("market_regime", {}),
            "regime_label": trade_data.get("regime_label", "unknown"),
            "risk_mode": trade_data.get("risk_mode", "NORMAL"),
            "dynamic_threshold": trade_data.get("dynamic_threshold", 60),
            # Timing
            "timestamp_utc": _now_utc().isoformat(),
            "timestamp_et": now_et.isoformat(),
            "time_window": _time_window(now_et),
            "date": now_et.date().isoformat(),
            # Entry quality assessment (populated post-exit)
            "entry_quality": None,  # "early", "on_time", "late", "chasing"
        }
        try:
            await self.db.trade_analytics.insert_one(record)
        except Exception as e:
            logger.error(f"Failed to log trade entry: {e}")
        return record

    async def log_trade_exit(self, exit_data: Dict):
        """Log a trade exit with P&L and quality analysis."""
        now_et = _now_et()
        symbol = exit_data.get("symbol", "")
        entry_price = exit_data.get("entry_price", 0)
        exit_price = exit_data.get("exit_price", 0)
        pnl = exit_data.get("pnl", 0)
        pnl_pct = ((exit_price / entry_price) - 1) * 100 if entry_price > 0 else 0

        # Determine exit type
        exit_reasons = exit_data.get("exit_reasons", [])
        exit_type = "manual"
        if any("stop" in str(r).lower() for r in exit_reasons):
            exit_type = "stop_loss"
        elif any("take profit" in str(r).lower() or "partial" in str(r).lower() for r in exit_reasons):
            exit_type = "take_profit"
        elif any("trailing" in str(r).lower() for r in exit_reasons):
            exit_type = "trailing_stop"
        elif any("time" in str(r).lower() for r in exit_reasons):
            exit_type = "time_exit"
        elif any("momentum" in str(r).lower() or "fade" in str(r).lower() for r in exit_reasons):
            exit_type = "momentum_fade"

        # Calculate hold duration
        entry_time = exit_data.get("entry_time")
        hold_minutes = 0
        if entry_time:
            if isinstance(entry_time, str):
                try:
                    entry_time = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    entry_time = None
            if entry_time:
                hold_minutes = (_now_utc() - entry_time).total_seconds() / 60

        # Entry quality assessment
        entry_quality = self._assess_entry_quality(exit_data, pnl, pnl_pct, hold_minutes)

        record = {
            "type": "exit",
            "symbol": symbol,
            "classification": exit_data.get("classification", "DAY_TRADE"),
            "action": "SELL",
            "shares": exit_data.get("shares", 0),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "is_winner": pnl > 0,
            "exit_type": exit_type,
            "exit_reasons": exit_reasons,
            "hold_minutes": round(hold_minutes, 1),
            # Entry context (copied from entry record)
            "confidence": exit_data.get("confidence", 0),
            "best_setup": exit_data.get("best_setup", ""),
            "entry_signals": exit_data.get("entry_signals", []),
            "signal_count": exit_data.get("signal_count", 0),
            "is_top_mover": exit_data.get("is_top_mover", False),
            "mover_source": exit_data.get("source", "universe"),
            # Market context
            "entry_regime": exit_data.get("entry_regime", "unknown"),
            "exit_regime": exit_data.get("exit_regime", "unknown"),
            "risk_mode": exit_data.get("risk_mode", "NORMAL"),
            # Risk compliance
            "stop_loss_price": exit_data.get("stop_loss", 0),
            "stop_loss_respected": exit_type == "stop_loss" or pnl >= 0 or (exit_price >= exit_data.get("stop_loss", 0) if exit_data.get("stop_loss", 0) > 0 else True),
            "trailing_effective": exit_type == "trailing_stop" and pnl > 0,
            # Quality
            "entry_quality": entry_quality,
            # Timing
            "timestamp_utc": _now_utc().isoformat(),
            "timestamp_et": now_et.isoformat(),
            "time_window": _time_window(now_et),
            "entry_time_window": exit_data.get("entry_time_window", "unknown"),
            "date": now_et.date().isoformat(),
        }

        try:
            await self.db.trade_analytics.insert_one(record)
            # Update the entry record with exit quality
            await self.db.trade_analytics.update_one(
                {"type": "entry", "symbol": symbol, "date": now_et.date().isoformat()},
                {"$set": {"entry_quality": entry_quality, "outcome": "win" if pnl > 0 else "loss"}}
            )
        except Exception as e:
            logger.error(f"Failed to log trade exit: {e}")
        return record

    def _assess_entry_quality(self, exit_data: Dict, pnl: float, pnl_pct: float, hold_minutes: float) -> str:
        """Assess if the entry was early, on_time, late, or chasing."""
        if pnl > 0:
            if hold_minutes < 5 and pnl_pct > 1.0:
                return "on_time"  # Quick profit = good timing
            elif hold_minutes < 30 and pnl_pct > 0.5:
                return "on_time"
            elif hold_minutes > 120:
                return "early"  # Had to wait too long for profit
            return "on_time"
        else:
            if hold_minutes < 10 and abs(pnl_pct) > 1.0:
                return "chasing"  # Quick loss = entered too late / chased
            elif abs(pnl_pct) > 1.5:
                return "late"  # Big loss = bad timing
            return "early"  # Small loss, quick stop = probably too early

    # =================== PIPELINE LOGGING ===================

    async def log_scan_cycle(self, cycle_data: Dict):
        """Log a complete scan cycle for pipeline efficiency tracking."""
        now_et = _now_et()
        record = {
            "type": "scan_cycle",
            "date": now_et.date().isoformat(),
            "timestamp_utc": _now_utc().isoformat(),
            "timestamp_et": now_et.isoformat(),
            "time_window": _time_window(now_et),
            # Pipeline metrics
            "total_scanned": cycle_data.get("total_scanned", 0),
            "top_movers_injected": cycle_data.get("top_movers_injected", 0),
            "prefilter_passed": cycle_data.get("prefilter_passed", 0),
            "ta_analyzed": cycle_data.get("ta_analyzed", 0),
            "setups_found": cycle_data.get("setups_found", 0),
            "filters_passed": cycle_data.get("filters_passed", 0),
            "confidence_passed": cycle_data.get("confidence_passed", 0),
            "candidates": cycle_data.get("candidates", 0),
            "executed": cycle_data.get("executed", 0),
            # Conversion rates
            "movers_to_setups_rate": round(
                cycle_data.get("setups_found", 0) / max(1, cycle_data.get("top_movers_injected", 1)) * 100, 1
            ),
            "setups_to_executed_rate": round(
                cycle_data.get("executed", 0) / max(1, cycle_data.get("setups_found", 1)) * 100, 1
            ),
            # Top rejection reasons
            "top_rejections": cycle_data.get("top_rejections", {}),
            # Market context
            "market_regime": cycle_data.get("market_regime", "unknown"),
            "risk_mode": cycle_data.get("risk_mode", "NORMAL"),
            "threshold_used": cycle_data.get("threshold_used", 60),
        }
        try:
            await self.db.pipeline_analytics.insert_one(record)
        except Exception as e:
            logger.error(f"Failed to log scan cycle: {e}")

    # =================== SESSION SUMMARY ===================

    async def get_session_summary(self, date: str = None) -> Dict:
        """Generate a full session performance summary."""
        if not date:
            date = _now_et().date().isoformat()

        # Get all exit records for the day
        exits = await self.db.trade_analytics.find(
            {"type": "exit", "date": date}, {"_id": 0}
        ).to_list(100)

        entries = await self.db.trade_analytics.find(
            {"type": "entry", "date": date}, {"_id": 0}
        ).to_list(100)

        if not exits:
            return {
                "date": date,
                "total_trades": len(entries),
                "completed_trades": 0,
                "open_positions": len(entries),
                "message": "No completed trades yet" if entries else "No trades today",
                "entries": entries,
            }

        # Core metrics
        total_trades = len(exits)
        winners = [e for e in exits if e.get("pnl", 0) > 0]
        losers = [e for e in exits if e.get("pnl", 0) <= 0]
        win_rate = round(len(winners) / total_trades * 100, 1) if total_trades > 0 else 0

        all_pnl = [e.get("pnl", 0) for e in exits]
        net_pnl = round(sum(all_pnl), 2)
        avg_win = round(sum(e.get("pnl", 0) for e in winners) / len(winners), 2) if winners else 0
        avg_loss = round(sum(e.get("pnl", 0) for e in losers) / len(losers), 2) if losers else 0

        # Max drawdown (running P&L)
        running = 0
        peak = 0
        max_dd = 0
        for e in sorted(exits, key=lambda x: x.get("timestamp_utc", "")):
            running += e.get("pnl", 0)
            peak = max(peak, running)
            dd = running - peak
            max_dd = min(max_dd, dd)

        # P&L by time window
        pnl_by_window = {}
        for e in exits:
            tw = e.get("time_window", "unknown")
            if tw not in pnl_by_window:
                pnl_by_window[tw] = {"trades": 0, "pnl": 0, "wins": 0}
            pnl_by_window[tw]["trades"] += 1
            pnl_by_window[tw]["pnl"] = round(pnl_by_window[tw]["pnl"] + e.get("pnl", 0), 2)
            if e.get("pnl", 0) > 0:
                pnl_by_window[tw]["wins"] += 1

        # Exit type breakdown
        exit_types = {}
        for e in exits:
            et = e.get("exit_type", "unknown")
            exit_types[et] = exit_types.get(et, 0) + 1

        # Entry quality breakdown
        entry_qualities = {}
        for e in exits:
            eq = e.get("entry_quality", "unknown")
            entry_qualities[eq] = entry_qualities.get(eq, 0) + 1

        # Risk compliance
        stop_loss_respected = sum(1 for e in exits if e.get("stop_loss_respected", True))
        trailing_effective = sum(1 for e in exits if e.get("trailing_effective", False))
        risk_violations = total_trades - stop_loss_respected

        # Regime performance
        regime_perf = {}
        for e in exits:
            regime = e.get("entry_regime", "unknown")
            if regime not in regime_perf:
                regime_perf[regime] = {"trades": 0, "pnl": 0, "wins": 0}
            regime_perf[regime]["trades"] += 1
            regime_perf[regime]["pnl"] = round(regime_perf[regime]["pnl"] + e.get("pnl", 0), 2)
            if e.get("pnl", 0) > 0:
                regime_perf[regime]["wins"] += 1

        return {
            "date": date,
            "performance": {
                "total_trades": total_trades,
                "win_rate_pct": win_rate,
                "winners": len(winners),
                "losers": len(losers),
                "net_pnl": net_pnl,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "avg_win_loss_ratio": round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else 0,
                "max_drawdown": round(max_dd, 2),
                "profit_factor": round(abs(sum(e.get("pnl", 0) for e in winners) / sum(e.get("pnl", 0) for e in losers)), 2) if losers and sum(e.get("pnl", 0) for e in losers) != 0 else 0,
            },
            "pnl_by_time_window": pnl_by_window,
            "exit_types": exit_types,
            "entry_quality": entry_qualities,
            "risk_compliance": {
                "stop_loss_respected": stop_loss_respected,
                "stop_loss_violations": risk_violations,
                "trailing_stops_effective": trailing_effective,
                "risk_violations_pct": round(risk_violations / total_trades * 100, 1) if total_trades > 0 else 0,
            },
            "regime_performance": regime_perf,
            "open_positions": len(entries) - len(exits),
        }

    # =================== TRADE QUALITY ===================

    async def get_trade_quality_analysis(self, date: str = None) -> Dict:
        """Analyze which signals led to wins vs losses."""
        if not date:
            date = _now_et().date().isoformat()

        exits = await self.db.trade_analytics.find(
            {"type": "exit", "date": date}, {"_id": 0}
        ).to_list(100)

        if not exits:
            return {"date": date, "message": "No completed trades to analyze"}

        # Signal analysis: which signals appear in wins vs losses
        win_signals = {}
        loss_signals = {}
        for e in exits:
            signals = e.get("entry_signals", [])
            bucket = win_signals if e.get("pnl", 0) > 0 else loss_signals
            for sig in signals:
                # Normalize signal name
                key = sig.split(":")[0].strip() if ":" in sig else sig.strip()
                if len(key) > 50:
                    key = key[:50]
                bucket[key] = bucket.get(key, 0) + 1

        # Setup analysis
        setup_results = {}
        for e in exits:
            setup = e.get("best_setup", "unknown")
            if setup not in setup_results:
                setup_results[setup] = {"wins": 0, "losses": 0, "total_pnl": 0}
            if e.get("pnl", 0) > 0:
                setup_results[setup]["wins"] += 1
            else:
                setup_results[setup]["losses"] += 1
            setup_results[setup]["total_pnl"] = round(
                setup_results[setup]["total_pnl"] + e.get("pnl", 0), 2)

        # Confidence vs outcome
        conf_buckets = {"60-70": {"wins": 0, "losses": 0, "pnl": 0},
                        "70-80": {"wins": 0, "losses": 0, "pnl": 0},
                        "80+": {"wins": 0, "losses": 0, "pnl": 0}}
        for e in exits:
            conf = e.get("confidence", 0)
            if conf >= 80:
                bucket = conf_buckets["80+"]
            elif conf >= 70:
                bucket = conf_buckets["70-80"]
            else:
                bucket = conf_buckets["60-70"]
            if e.get("pnl", 0) > 0:
                bucket["wins"] += 1
            else:
                bucket["losses"] += 1
            bucket["pnl"] = round(bucket["pnl"] + e.get("pnl", 0), 2)

        # Top mover performance
        mover_trades = [e for e in exits if e.get("is_top_mover")]
        universe_trades = [e for e in exits if not e.get("is_top_mover")]

        return {
            "date": date,
            "total_analyzed": len(exits),
            "winning_signals": dict(sorted(win_signals.items(), key=lambda x: x[1], reverse=True)[:10]),
            "losing_signals": dict(sorted(loss_signals.items(), key=lambda x: x[1], reverse=True)[:10]),
            "setup_results": setup_results,
            "confidence_vs_outcome": conf_buckets,
            "top_mover_performance": {
                "trades": len(mover_trades),
                "pnl": round(sum(e.get("pnl", 0) for e in mover_trades), 2),
                "win_rate": round(sum(1 for e in mover_trades if e.get("pnl", 0) > 0) / max(1, len(mover_trades)) * 100, 1),
            },
            "universe_performance": {
                "trades": len(universe_trades),
                "pnl": round(sum(e.get("pnl", 0) for e in universe_trades), 2),
                "win_rate": round(sum(1 for e in universe_trades if e.get("pnl", 0) > 0) / max(1, len(universe_trades)) * 100, 1),
            },
        }

    # =================== PIPELINE EFFICIENCY ===================

    async def get_pipeline_efficiency(self, date: str = None) -> Dict:
        """Analyze pipeline conversion rates and rejection patterns."""
        if not date:
            date = _now_et().date().isoformat()

        cycles = await self.db.pipeline_analytics.find(
            {"date": date}, {"_id": 0}
        ).to_list(200)

        if not cycles:
            return {"date": date, "message": "No scan cycles logged today", "total_cycles": 0}

        total_cycles = len(cycles)
        avg_scanned = round(sum(c.get("total_scanned", 0) for c in cycles) / total_cycles)
        avg_movers = round(sum(c.get("top_movers_injected", 0) for c in cycles) / total_cycles)
        avg_prefilter = round(sum(c.get("prefilter_passed", 0) for c in cycles) / total_cycles)
        avg_setups = round(sum(c.get("setups_found", 0) for c in cycles) / total_cycles)
        avg_executed = round(sum(c.get("executed", 0) for c in cycles) / total_cycles, 1)

        total_movers = sum(c.get("top_movers_injected", 0) for c in cycles)
        total_setups = sum(c.get("setups_found", 0) for c in cycles)
        total_executed = sum(c.get("executed", 0) for c in cycles)

        # Aggregate rejection reasons
        all_rejections = {}
        for c in cycles:
            for reason, count in c.get("top_rejections", {}).items():
                all_rejections[reason] = all_rejections.get(reason, 0) + count

        top_3_rejections = dict(sorted(all_rejections.items(), key=lambda x: x[1], reverse=True)[:3])

        return {
            "date": date,
            "total_cycles": total_cycles,
            "averages_per_cycle": {
                "scanned": avg_scanned,
                "top_movers": avg_movers,
                "prefilter_passed": avg_prefilter,
                "setups_found": avg_setups,
                "executed": avg_executed,
            },
            "conversion_rates": {
                "movers_to_setups_pct": round(total_setups / max(1, total_movers) * 100, 1),
                "setups_to_executed_pct": round(total_executed / max(1, total_setups) * 100, 1),
                "scanned_to_executed_pct": round(total_executed / max(1, sum(c.get("total_scanned", 0) for c in cycles)) * 100, 2),
            },
            "top_3_rejection_reasons": top_3_rejections,
            "all_rejection_reasons": dict(sorted(all_rejections.items(), key=lambda x: x[1], reverse=True)),
        }

    # =================== BEST/WORST TRADES ===================

    async def get_best_worst_trades(self, date: str = None, count: int = 3) -> Dict:
        """Get the top N best and worst trades with full reasoning."""
        if not date:
            date = _now_et().date().isoformat()

        exits = await self.db.trade_analytics.find(
            {"type": "exit", "date": date}, {"_id": 0}
        ).sort("pnl", -1).to_list(100)

        if not exits:
            return {"date": date, "message": "No completed trades"}

        def format_trade(t):
            return {
                "symbol": t.get("symbol"),
                "pnl": t.get("pnl"),
                "pnl_pct": t.get("pnl_pct"),
                "confidence": t.get("confidence"),
                "entry_price": t.get("entry_price"),
                "exit_price": t.get("exit_price"),
                "exit_type": t.get("exit_type"),
                "hold_minutes": t.get("hold_minutes"),
                "entry_quality": t.get("entry_quality"),
                "entry_signals": t.get("entry_signals", []),
                "exit_reasons": t.get("exit_reasons", []),
                "best_setup": t.get("best_setup"),
                "is_top_mover": t.get("is_top_mover"),
                "mover_source": t.get("mover_source"),
                "entry_regime": t.get("entry_regime"),
                "time_window": t.get("time_window"),
            }

        best = [format_trade(t) for t in exits[:count]]
        worst = [format_trade(t) for t in exits[-count:] if t.get("pnl", 0) < 0]
        if not worst:
            worst = [format_trade(t) for t in reversed(exits[-count:])]

        return {
            "date": date,
            "best_trades": best,
            "worst_trades": worst,
        }

    # =================== RISK COMPLIANCE ===================

    async def get_risk_compliance(self, date: str = None) -> Dict:
        """Verify risk rule compliance for all trades."""
        if not date:
            date = _now_et().date().isoformat()

        exits = await self.db.trade_analytics.find(
            {"type": "exit", "date": date}, {"_id": 0}
        ).to_list(100)

        entries = await self.db.trade_analytics.find(
            {"type": "entry", "date": date}, {"_id": 0}
        ).to_list(100)

        if not exits and not entries:
            return {"date": date, "message": "No trades to audit"}

        # Check stop-loss execution
        sl_trades = [e for e in exits if e.get("stop_loss_price", 0) > 0]
        sl_respected = sum(1 for e in sl_trades if e.get("stop_loss_respected", True))
        sl_violations = []
        for e in exits:
            if not e.get("stop_loss_respected", True):
                sl_violations.append({
                    "symbol": e.get("symbol"),
                    "stop_loss": e.get("stop_loss_price"),
                    "exit_price": e.get("exit_price"),
                    "pnl": e.get("pnl"),
                })

        # Check trailing stop effectiveness
        trailing_exits = [e for e in exits if e.get("exit_type") == "trailing_stop"]

        # Check position sizing compliance
        oversized = []
        for en in entries:
            pos_pct = en.get("position_pct", 0)
            if pos_pct > 22:  # 20% max + 2% tolerance
                oversized.append({"symbol": en.get("symbol"), "position_pct": pos_pct})

        # Check daily loss
        total_pnl = sum(e.get("pnl", 0) for e in exits)

        return {
            "date": date,
            "total_trades": len(exits),
            "stop_loss": {
                "trades_with_sl": len(sl_trades),
                "respected": sl_respected,
                "violations": sl_violations,
                "compliance_pct": round(sl_respected / max(1, len(sl_trades)) * 100, 1),
            },
            "trailing_stops": {
                "total_triggered": len(trailing_exits),
                "locked_profits": sum(1 for e in trailing_exits if e.get("pnl", 0) > 0),
            },
            "position_sizing": {
                "total_entries": len(entries),
                "oversized_violations": oversized,
                "all_compliant": len(oversized) == 0,
            },
            "daily_loss": {
                "total_pnl": round(total_pnl, 2),
                "max_loss_pct": 3.0,
                "within_limit": True,  # Will be updated when account equity is known
            },
        }

    # =================== REGIME PERFORMANCE ===================

    async def get_regime_performance(self, date: str = None) -> Dict:
        """Compare performance across market regimes."""
        if not date:
            date = _now_et().date().isoformat()

        exits = await self.db.trade_analytics.find(
            {"type": "exit", "date": date}, {"_id": 0}
        ).to_list(100)

        if not exits:
            return {"date": date, "message": "No trades to analyze by regime"}

        regime_data = {}
        for e in exits:
            regime = e.get("entry_regime", "unknown")
            if regime not in regime_data:
                regime_data[regime] = {
                    "trades": 0, "wins": 0, "losses": 0,
                    "total_pnl": 0, "avg_pnl": 0,
                    "avg_confidence": 0, "avg_hold_minutes": 0,
                }
            rd = regime_data[regime]
            rd["trades"] += 1
            if e.get("pnl", 0) > 0:
                rd["wins"] += 1
            else:
                rd["losses"] += 1
            rd["total_pnl"] = round(rd["total_pnl"] + e.get("pnl", 0), 2)
            rd["avg_confidence"] += e.get("confidence", 0)
            rd["avg_hold_minutes"] += e.get("hold_minutes", 0)

        # Calculate averages
        for regime, rd in regime_data.items():
            n = rd["trades"]
            rd["win_rate_pct"] = round(rd["wins"] / n * 100, 1) if n > 0 else 0
            rd["avg_pnl"] = round(rd["total_pnl"] / n, 2) if n > 0 else 0
            rd["avg_confidence"] = round(rd["avg_confidence"] / n, 1) if n > 0 else 0
            rd["avg_hold_minutes"] = round(rd["avg_hold_minutes"] / n, 1) if n > 0 else 0

        return {
            "date": date,
            "regimes": regime_data,
            "best_regime": max(regime_data.items(), key=lambda x: x[1]["total_pnl"])[0] if regime_data else "none",
            "worst_regime": min(regime_data.items(), key=lambda x: x[1]["total_pnl"])[0] if regime_data else "none",
        }

    # =================== FULL REPORT ===================

    async def get_full_report(self, date: str = None) -> Dict:
        """Generate the complete performance report the user requested."""
        if not date:
            date = _now_et().date().isoformat()

        session = await self.get_session_summary(date)
        quality = await self.get_trade_quality_analysis(date)
        pipeline = await self.get_pipeline_efficiency(date)
        best_worst = await self.get_best_worst_trades(date)
        risk = await self.get_risk_compliance(date)
        regime = await self.get_regime_performance(date)

        return {
            "report_date": date,
            "generated_at": _now_utc().isoformat(),
            "session_summary": session,
            "trade_quality": quality,
            "pipeline_efficiency": pipeline,
            "best_worst_trades": best_worst,
            "risk_compliance": risk,
            "regime_performance": regime,
        }
