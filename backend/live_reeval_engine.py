"""
Live Re-Evaluation Engine for ObaidTradez
Triggers dynamic re-evaluation of trading logic when live price updates are significant.
Handles: stop-loss/take-profit checks, breakout/breakdown detection, VWAP reclaim/loss,
spread changes, and entry readiness — without waiting for the next full scan.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Throttle: minimum seconds between re-evals for the same symbol
REEVAL_THROTTLE_SECONDS = 30
# Cache settings/regime for this many seconds before refreshing
CACHE_TTL_SECONDS = 60


class ReEvalResult:
    """Captures what changed during a re-evaluation."""
    __slots__ = (
        "symbol", "trigger_reason", "old_price", "new_price", "data_source",
        "setup_changed", "confidence_changed", "entry_readiness_changed",
        "stop_target_changed", "old_confidence", "new_confidence",
        "old_action", "new_action", "details", "timestamp",
        "position_action", "position_pnl_pct",
    )

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.trigger_reason = ""
        self.old_price = 0.0
        self.new_price = 0.0
        self.data_source = ""
        self.setup_changed = False
        self.confidence_changed = False
        self.entry_readiness_changed = False
        self.stop_target_changed = False
        self.old_confidence = 0
        self.new_confidence = 0
        self.old_action = ""
        self.new_action = ""
        self.details = []
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.position_action = ""  # "HOLD", "SELL_STOP", "SELL_TP"
        self.position_pnl_pct = 0.0

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "trigger_reason": self.trigger_reason,
            "old_price": self.old_price,
            "new_price": self.new_price,
            "data_source": self.data_source,
            "setup_changed": self.setup_changed,
            "confidence_changed": self.confidence_changed,
            "entry_readiness_changed": self.entry_readiness_changed,
            "stop_target_changed": self.stop_target_changed,
            "old_confidence": self.old_confidence,
            "new_confidence": self.new_confidence,
            "old_action": self.old_action,
            "new_action": self.new_action,
            "details": self.details,
            "timestamp": self.timestamp,
            "position_action": self.position_action,
            "position_pnl_pct": self.position_pnl_pct,
        }


class LiveReEvaluationEngine:
    """Dynamically re-evaluates trading signals on meaningful live price changes."""

    def __init__(self, db, orchestrator):
        self.db = db
        self.orchestrator = orchestrator
        self._last_eval_time: Dict[str, float] = {}
        self._cached_settings = None
        self._cached_regime = None
        self._cache_ts: float = 0
        self._last_candidate_state: Dict[str, Dict] = {}
        self._reeval_log: list = []
        self._max_log_size = 200
        self._verifier = None  # Set externally
        self._stats = {
            "total_triggers": 0,
            "throttled": 0,
            "position_checks": 0,
            "candidate_checks": 0,
            "stop_loss_triggered": 0,
            "take_profit_triggered": 0,
            "setup_changes": 0,
            "confidence_changes": 0,
            "stale_blocked": 0,
        }

    def set_verifier(self, verifier):
        self._verifier = verifier

    async def on_price_change(self, symbol: str, price_state):
        """Callback from LivePriceEngine when a significant price change occurs."""
        self._stats["total_triggers"] += 1
        now = time.time()

        # Throttle check
        last = self._last_eval_time.get(symbol, 0)
        if (now - last) < REEVAL_THROTTLE_SECONDS:
            self._stats["throttled"] += 1
            return
        self._last_eval_time[symbol] = now

        # Stale check — don't re-eval on stale data
        if price_state.stale:
            self._stats["stale_blocked"] += 1
            return

        try:
            # Refresh settings/regime cache if stale
            if (now - self._cache_ts) > CACHE_TTL_SECONDS:
                self._cached_settings = await self.orchestrator.get_settings()
                self._cached_regime = await self.orchestrator.regime_detector.detect()
                self._cache_ts = now

            settings = self._cached_settings
            regime = self._cached_regime
            new_price = price_state.display_price
            old_price = price_state.prev_display_price
            source = price_state.source

            # 1. Check open positions for stop-loss / take-profit
            await self._check_position(symbol, new_price, old_price, source, settings)

            # 2. Check candidate signals for setup changes
            await self._check_candidate(symbol, new_price, old_price, source, settings, regime, price_state)

        except Exception as e:
            logger.error(f"ReEval error for {symbol}: {e}")

    async def _check_position(self, symbol: str, new_price: float, old_price: float,
                              source: str, settings):
        """Check if an open position's stop-loss or take-profit has been hit."""
        self._stats["position_checks"] += 1

        # Find open position for this symbol
        try:
            positions = await self.orchestrator.get_positions()
        except Exception:
            return

        pos = None
        for p in positions:
            if p.get("symbol") == symbol:
                pos = p
                break
        if not pos:
            return

        entry_price = float(pos.get("avg_entry_price", 0))
        if entry_price <= 0:
            return

        pnl_pct = ((new_price / entry_price) - 1) * 100
        result = ReEvalResult(symbol)
        result.old_price = old_price
        result.new_price = new_price
        result.data_source = source
        result.position_pnl_pct = round(pnl_pct, 2)

        # Check trade log for classification
        trade_log = await self.db.auto_trade_log.find_one(
            {"symbol": symbol, "action": {"$in": ["BUY", "SELL"]}},
            sort=[("timestamp", -1)]
        )
        classification = trade_log.get("classification", "DAY_TRADE") if trade_log else "DAY_TRADE"

        if classification == "DAY_TRADE":
            tp_pct = settings.dt_take_profit_pct
            sl_pct = settings.dt_stop_loss_pct
        else:
            tp_pct = 25.0  # LT positions have wider targets
            sl_pct = settings.lt_trailing_stop_pct

        action = "HOLD"
        trigger = ""

        if pnl_pct >= tp_pct:
            action = "SELL_TAKE_PROFIT"
            trigger = f"Take-profit hit: +{pnl_pct:.1f}% >= {tp_pct}%"
            self._stats["take_profit_triggered"] += 1
        elif pnl_pct <= -sl_pct:
            action = "SELL_STOP_LOSS"
            trigger = f"Stop-loss hit: {pnl_pct:.1f}% <= -{sl_pct}%"
            self._stats["stop_loss_triggered"] += 1

        if action != "HOLD":
            result.position_action = action
            result.trigger_reason = trigger
            result.stop_target_changed = True
            result.details.append(trigger)
            result.details.append(f"Classification: {classification}")
            result.details.append(f"Entry: ${entry_price:.2f} | Current: ${new_price:.2f}")

            self._log_result(result)
            await self._persist_reeval_log(result)

            # Log as alert for the UI
            await self.db.reeval_events.insert_one({
                "symbol": symbol,
                "event": action,
                "trigger": trigger,
                "old_price": old_price,
                "new_price": new_price,
                "pnl_pct": round(pnl_pct, 2),
                "entry_price": entry_price,
                "source": source,
                "classification": classification,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            logger.warning(f"REEVAL POSITION {symbol}: {trigger} | price=${new_price:.2f} entry=${entry_price:.2f} pnl={pnl_pct:.1f}%")

    async def _check_candidate(self, symbol: str, new_price: float, old_price: float,
                               source: str, settings, regime, price_state):
        """Re-evaluate a candidate signal using the latest live price."""
        self._stats["candidate_checks"] += 1

        # Get the cached TA signal for this symbol
        ta_signal = await self.db.trading_signals.find_one({"symbol": symbol}, {"_id": 0})
        if not ta_signal:
            return

        # Build trigger reason from price movement analysis
        triggers = []
        indicators = ta_signal.get("indicators", {})
        structure = ta_signal.get("structure", {})

        # Check key level crossings
        vwap = indicators.get("vwap", 0)
        if vwap > 0:
            old_above_vwap = old_price > vwap
            new_above_vwap = new_price > vwap
            if old_above_vwap != new_above_vwap:
                direction = "reclaim" if new_above_vwap else "loss"
                triggers.append(f"VWAP {direction}: price ${new_price:.2f} crossed VWAP ${vwap:.2f}")

        # Support/resistance touches
        support = structure.get("nearest_support", 0) or indicators.get("support", 0)
        resistance = structure.get("nearest_resistance", 0) or indicators.get("resistance", 0)
        if support > 0 and new_price <= support * 1.002 and old_price > support * 1.002:
            triggers.append(f"Support touch: price ${new_price:.2f} reached support ${support:.2f}")
        if resistance > 0 and new_price >= resistance * 0.998 and old_price < resistance * 0.998:
            triggers.append(f"Resistance touch: price ${new_price:.2f} reached resistance ${resistance:.2f}")

        # Breakout/breakdown detection
        if resistance > 0 and new_price > resistance and old_price <= resistance:
            triggers.append(f"BREAKOUT: price ${new_price:.2f} broke above resistance ${resistance:.2f}")
        if support > 0 and new_price < support and old_price >= support:
            triggers.append(f"BREAKDOWN: price ${new_price:.2f} broke below support ${support:.2f}")

        # Overextension from VWAP
        if vwap > 0:
            ext_pct = abs(new_price - vwap) / vwap * 100
            old_ext_pct = abs(old_price - vwap) / vwap * 100 if old_price > 0 else 0
            if ext_pct > 2.0 and old_ext_pct <= 2.0:
                triggers.append(f"Overextension from VWAP: {ext_pct:.1f}% (threshold 2%)")
            elif ext_pct <= 2.0 and old_ext_pct > 2.0:
                triggers.append(f"VWAP reversion: extension reduced to {ext_pct:.1f}%")

        # Spread change (using live bid/ask)
        if price_state.spread_pct > 0:
            old_spread = indicators.get("spread_pct", 0)
            new_spread = price_state.spread_pct
            if old_spread <= 0.5 and new_spread > 0.5:
                triggers.append(f"Spread widened beyond limit: {new_spread:.2f}% (was {old_spread:.2f}%)")
            elif old_spread > 0.5 and new_spread <= 0.5:
                triggers.append(f"Spread narrowed within limit: {new_spread:.2f}% (was {old_spread:.2f}%)")

        # Only proceed if there's a meaningful trigger
        if not triggers:
            # Still check general price movement magnitude
            if old_price > 0:
                move_pct = abs(new_price - old_price) / old_price * 100
                if move_pct < 0.1:
                    return  # Too small to matter
                triggers.append(f"Price moved {move_pct:.2f}%: ${old_price:.2f} -> ${new_price:.2f}")
            else:
                return

        # Now re-evaluate the signal with the updated price
        # Update the TA signal's price field for re-evaluation
        updated_signal = dict(ta_signal)
        updated_signal["price"] = new_price
        # Update spread with live data
        if price_state.spread_pct > 0:
            if "indicators" not in updated_signal:
                updated_signal["indicators"] = {}
            updated_signal["indicators"]["spread_pct"] = price_state.spread_pct

        # Check overextension with new price
        if vwap > 0:
            ext_pct = abs(new_price - vwap) / vwap * 100
            updated_signal["overextended"] = ext_pct > 2.0
            if ext_pct > 2.0:
                updated_signal["overextension_reason"] = f"Price {ext_pct:.1f}% from VWAP"

        # Get previous state
        prev_state = self._last_candidate_state.get(symbol, {})
        old_confidence = prev_state.get("confidence", ta_signal.get("confidence", 0))
        old_action = prev_state.get("action", "UNKNOWN")

        # Re-evaluate using DayTradingEngine
        from ai_trading_system import DayTradingEngine

        news_data = None
        if isinstance(ta_signal.get("news_sentiment"), dict):
            news_data = ta_signal["news_sentiment"]

        explanation = DayTradingEngine.evaluate_buy(updated_signal, news_data, regime, settings)
        new_confidence = explanation.confidence_score
        new_action = explanation.action

        # Store new state
        self._last_candidate_state[symbol] = {
            "confidence": new_confidence,
            "action": new_action,
        }

        # Entry readiness reclassification based on current price vs setup levels
        entry_status = "UNKNOWN"
        old_entry_status = prev_state.get("entry_status", "UNKNOWN")
        exit_plan = explanation.exit_plan
        if isinstance(exit_plan, dict):
            setup_entry = exit_plan.get("entry", 0)
            setup_stop = exit_plan.get("stop_loss", 0)
            setup_target = exit_plan.get("take_profit", 0)
            direction = updated_signal.get("direction", "NONE")

            if setup_entry > 0 and new_price > 0:
                # Check setup staleness via price drift
                ta_price = ta_signal.get("price", 0)
                drift_pct = abs((new_price - ta_price) / ta_price) * 100 if ta_price > 0 else 0
                if drift_pct > 10:
                    entry_status = "STALE_SETUP"
                elif direction == "LONG":
                    if new_price <= setup_stop and setup_stop > 0:
                        entry_status = "BLOWN_STOP"
                    elif new_price <= setup_entry * 1.005:
                        entry_status = "TRADE_NOW"
                    elif new_price <= setup_entry * 1.02:
                        entry_status = "WATCHLIST"
                    elif setup_target > 0 and new_price >= setup_target:
                        entry_status = "MISSED"
                    else:
                        entry_status = "WATCHLIST"
                elif direction == "SHORT":
                    if new_price >= setup_stop and setup_stop > 0:
                        entry_status = "BLOWN_STOP"
                    elif new_price >= setup_entry * 0.995:
                        entry_status = "TRADE_NOW"
                    elif new_price >= setup_entry * 0.98:
                        entry_status = "WATCHLIST"
                    elif setup_target > 0 and new_price <= setup_target:
                        entry_status = "MISSED"
                    else:
                        entry_status = "WATCHLIST"

        self._last_candidate_state[symbol]["entry_status"] = entry_status

        # Detect changes
        result = ReEvalResult(symbol)
        result.old_price = old_price
        result.new_price = new_price
        result.data_source = source
        result.trigger_reason = " | ".join(triggers)
        result.old_confidence = old_confidence
        result.new_confidence = new_confidence
        result.old_action = old_action
        result.new_action = new_action

        if new_action != old_action and old_action != "UNKNOWN":
            result.setup_changed = True
            result.entry_readiness_changed = True
            result.details.append(f"Action changed: {old_action} -> {new_action}")
            self._stats["setup_changes"] += 1

        if entry_status != old_entry_status and old_entry_status != "UNKNOWN":
            result.entry_readiness_changed = True
            result.details.append(f"Entry status: {old_entry_status} -> {entry_status}")

        if abs(new_confidence - old_confidence) >= 3:
            result.confidence_changed = True
            result.details.append(f"Confidence: {old_confidence} -> {new_confidence}")
            self._stats["confidence_changes"] += 1

        # Check if stop/target conditions changed
        ki = explanation.key_indicators
        if isinstance(ki, dict):
            if ki.get("overextension_block") and not prev_state.get("overextended"):
                result.stop_target_changed = True
                result.details.append("Now overextended from VWAP")
            if ki.get("spread_block") and not prev_state.get("spread_blocked"):
                result.stop_target_changed = True
                result.details.append(f"Spread now blocking: {price_state.spread_pct:.2f}%")

        # Only log if something meaningful changed
        has_change = (result.setup_changed or result.confidence_changed or
                      result.entry_readiness_changed or result.stop_target_changed)

        if has_change:
            result.details.extend(triggers)
            result.details.append(f"Entry readiness: {entry_status}")
            self._log_result(result)
            await self._persist_reeval_log(result)
            logger.info(
                f"REEVAL {symbol}: {result.trigger_reason} | "
                f"price=${old_price:.2f}->${new_price:.2f} | source={source} | "
                f"action={old_action}->{new_action} | conf={old_confidence}->{new_confidence} | "
                f"entry_status={entry_status}"
            )

    def _log_result(self, result: ReEvalResult):
        """Add to in-memory ring buffer and verifier."""
        event_dict = result.to_dict()
        self._reeval_log.append(event_dict)
        if len(self._reeval_log) > self._max_log_size:
            self._reeval_log = self._reeval_log[-self._max_log_size:]
        # Feed to verifier if active
        if self._verifier and self._verifier.is_active:
            self._verifier.record_event(event_dict)

    async def _persist_reeval_log(self, result: ReEvalResult):
        """Persist re-evaluation event to MongoDB."""
        try:
            doc = result.to_dict()
            doc["_type"] = "reeval"
            await self.db.reeval_events.insert_one(doc)
        except Exception as e:
            logger.error(f"Failed to persist reeval log: {e}")

    def get_recent_events(self, limit: int = 50) -> list:
        """Get recent re-evaluation events from in-memory buffer."""
        return self._reeval_log[-limit:][::-1]

    def get_stats(self) -> Dict:
        return {
            **self._stats,
            "throttle_seconds": REEVAL_THROTTLE_SECONDS,
            "cached_candidates": len(self._last_candidate_state),
            "recent_events": len(self._reeval_log),
        }
