"""
ObaidTradez Auto-Trade Scheduler
Safety-first, strategy-aware autonomous trading system.
Handles: market session detection, dual-engine scheduling, event-driven triggers,
safety controls, deployment stages, notifications, and execution logging.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta, time
from typing import Dict, List, Optional, Tuple
from enum import Enum

from execution_transparency import ExecutionTransparencyTracker

logger = logging.getLogger(__name__)


def _safe_float(val, default=0):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


class MarketSession(str, Enum):
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    CLOSING = "closing"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"


class DeploymentMode(str, Enum):
    PAPER = "paper"
    SHADOW = "shadow"
    LIMITED_LIVE = "limited_live"
    FULL_LIVE = "full_live"


class SchedulerStatus(str, Enum):
    OFF = "off"
    RUNNING = "running"
    PAUSED = "paused"
    EMERGENCY_STOP = "emergency_stop"


# Eastern Time offset (UTC-4 during EDT, UTC-5 during EST)
# Use -4 for simplicity (EDT covers most trading days)
ET_OFFSET = timedelta(hours=-4)


def _now_et() -> datetime:
    return datetime.now(timezone.utc) + ET_OFFSET


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class MarketSessionManager:
    """Determines current market session and applies session-specific rules"""

    @staticmethod
    def get_session() -> MarketSession:
        now = _now_et()
        weekday = now.weekday()
        if weekday >= 5:
            return MarketSession.CLOSED

        t = now.time()
        if t < time(4, 0):
            return MarketSession.CLOSED
        elif t < time(9, 30):
            return MarketSession.PRE_MARKET
        elif t < time(15, 0):
            return MarketSession.REGULAR
        elif t < time(16, 0):
            return MarketSession.CLOSING
        elif t < time(20, 0):
            return MarketSession.AFTER_HOURS
        else:
            return MarketSession.CLOSED

    @staticmethod
    def can_execute(session: MarketSession, settings: dict) -> Tuple[bool, str]:
        if session == MarketSession.REGULAR:
            return True, "Regular market hours - full execution"
        elif session == MarketSession.PRE_MARKET:
            if settings.get("pre_market_execution", False):
                return True, "Pre-market execution explicitly enabled"
            return False, "Pre-market: scan only (execution disabled)"
        elif session == MarketSession.CLOSING:
            return True, "Closing session - tightened risk controls"
        elif session == MarketSession.AFTER_HOURS:
            if settings.get("after_hours_execution", False):
                return True, "After-hours execution explicitly enabled"
            return False, "After-hours: monitoring only"
        return False, "Market closed"

    @staticmethod
    def get_risk_multiplier(session: MarketSession) -> float:
        if session == MarketSession.CLOSING:
            return 0.5
        elif session == MarketSession.PRE_MARKET:
            return 0.3
        elif session == MarketSession.AFTER_HOURS:
            return 0.3
        return 1.0


class AutoTradeScheduler:
    """Main scheduler orchestrating all auto-trade operations"""

    DT_SCAN_INTERVAL = 180  # Scan every 3 minutes (aggressive)
    LT_SCAN_INTERVAL = 1800
    LOOP_TICK = 15
    MAX_CONSECUTIVE_LOSSES_COOLDOWN = 2
    COOLDOWN_MINUTES = 30
    STALE_DATA_MINUTES = 15
    MAX_API_FAILURES = 3

    def __init__(self, db, orchestrator, news_engine):
        self.db = db
        self.orchestrator = orchestrator
        self.news_engine = news_engine
        self.session_manager = MarketSessionManager()
        self.transparency = ExecutionTransparencyTracker(db)

        self._task: Optional[asyncio.Task] = None
        self._status = SchedulerStatus.OFF
        self._deployment_mode = DeploymentMode.PAPER
        self._pause_reason = ""

        self._last_dt_scan: Optional[datetime] = None
        self._last_lt_scan: Optional[datetime] = None
        self._next_dt_scan: Optional[datetime] = None
        self._next_lt_scan: Optional[datetime] = None
        self._last_cycle_result: Optional[Dict] = None
        self._cycle_count = 0

        self._consecutive_losses = 0
        self._cooldown_until: Optional[datetime] = None
        self._post_cooldown_active = False  # Post-cooldown threshold boost active
        self._api_failure_count = 0
        self._last_api_failure: Optional[datetime] = None
        self._daily_loss_pct_of_max = 0  # Track how close to daily loss limit

        self._scheduler_settings = {
            "dt_interval_seconds": self.DT_SCAN_INTERVAL,
            "lt_interval_seconds": self.LT_SCAN_INTERVAL,
            "pre_market_execution": False,
            "after_hours_execution": False,
            "max_daily_loss_pct": 3.0,
            "max_portfolio_drawdown_pct": 10.0,
            "max_consecutive_losses": 2,
            "cooldown_minutes": 30,
            "min_confidence_day": 60,  # Aggressive momentum: base 60
            "min_confidence_long": 70,
            "stale_data_minutes": 15,
            "max_api_failures": 3,
            "live_position_size_multiplier": 0.5,
            "live_confidence_boost": 10,
            "post_cooldown_threshold_boost": 3,  # Reduced from 5
            "soft_lock_daily_loss_pct": 80,
            "max_daily_losses": 3,  # Hard stop: 3 total losses/day
            "prioritize_power_hours": True,  # First 2h + last 2h priority
        }

    async def initialize(self):
        """Load saved state from DB"""
        doc = await self.db.scheduler_state.find_one({"_id": "config"})
        if doc:
            self._deployment_mode = DeploymentMode(doc.get("deployment_mode", "paper"))
            saved_settings = doc.get("settings", {})
            self._scheduler_settings.update(saved_settings)

    async def _save_state(self):
        await self.db.scheduler_state.update_one(
            {"_id": "config"},
            {"$set": {
                "deployment_mode": self._deployment_mode.value,
                "status": self._status.value,
                "settings": self._scheduler_settings,
                "last_dt_scan": self._last_dt_scan.isoformat() if self._last_dt_scan else None,
                "last_lt_scan": self._last_lt_scan.isoformat() if self._last_lt_scan else None,
                "cycle_count": self._cycle_count,
                "updated_at": _now_utc().isoformat()
            }},
            upsert=True
        )

    async def start(self) -> Dict:
        if self._status == SchedulerStatus.RUNNING:
            return {"status": "already_running"}
        if self._status == SchedulerStatus.EMERGENCY_STOP:
            return {"status": "emergency_stop", "message": "Clear emergency stop first"}

        self._status = SchedulerStatus.RUNNING
        self._pause_reason = ""
        self._api_failure_count = 0
        self._cycle_count = 0
        now = _now_utc()
        self._next_dt_scan = now
        self._next_lt_scan = now
        self._task = asyncio.create_task(self._scheduler_loop())
        await self._save_state()
        await self._notify("scheduler_started", "Auto-trade scheduler started", "info")
        return {"status": "started", "deployment_mode": self._deployment_mode.value}

    async def stop(self) -> Dict:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._status = SchedulerStatus.OFF
        self._task = None
        await self._save_state()
        await self._notify("scheduler_stopped", "Auto-trade scheduler stopped", "info")
        return {"status": "stopped"}

    async def emergency_stop(self) -> Dict:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._status = SchedulerStatus.EMERGENCY_STOP
        self._pause_reason = "Emergency stop activated by user"
        self._task = None

        settings = await self.orchestrator.get_settings()
        settings.emergency_pause = True
        await self.orchestrator.save_settings(settings)

        await self._save_state()
        await self._notify("emergency_stop", "EMERGENCY STOP ACTIVATED - All trading halted", "critical")
        return {"status": "emergency_stop", "message": "All trading halted"}

    async def clear_emergency(self) -> Dict:
        if self._status != SchedulerStatus.EMERGENCY_STOP:
            return {"status": self._status.value, "message": "No emergency to clear"}
        self._status = SchedulerStatus.OFF
        self._pause_reason = ""

        settings = await self.orchestrator.get_settings()
        settings.emergency_pause = False
        await self.orchestrator.save_settings(settings)

        await self._save_state()
        await self._notify("emergency_cleared", "Emergency stop cleared", "info")
        return {"status": "off", "message": "Emergency cleared. Start scheduler to resume."}

    async def set_deployment_mode(self, mode: str) -> Dict:
        try:
            new_mode = DeploymentMode(mode)
        except ValueError:
            return {"error": f"Invalid mode: {mode}. Valid: paper, shadow, limited_live, full_live"}

        if new_mode in (DeploymentMode.LIMITED_LIVE, DeploymentMode.FULL_LIVE):
            if self._deployment_mode == DeploymentMode.PAPER:
                return {"error": "Must progress through shadow mode before live trading"}

        old = self._deployment_mode
        self._deployment_mode = new_mode
        await self._save_state()
        await self._notify("mode_changed", f"Deployment mode: {old.value} -> {new_mode.value}", "warning")
        return {"deployment_mode": new_mode.value, "previous": old.value}

    async def update_settings(self, new_settings: Dict) -> Dict:
        allowed_keys = set(self._scheduler_settings.keys())
        updated = {}
        for k, v in new_settings.items():
            if k in allowed_keys:
                self._scheduler_settings[k] = v
                updated[k] = v
        if updated:
            await self._save_state()
        return {"updated": updated, "settings": self._scheduler_settings}

    async def get_status(self) -> Dict:
        session = self.session_manager.get_session()
        can_exec, exec_reason = self.session_manager.can_execute(session, self._scheduler_settings)
        now = _now_utc()

        next_dt = None
        next_lt = None
        if self._next_dt_scan:
            diff = (self._next_dt_scan - now).total_seconds()
            next_dt = max(0, int(diff))
        if self._next_lt_scan:
            diff = (self._next_lt_scan - now).total_seconds()
            next_lt = max(0, int(diff))

        cooldown_remaining = None
        if self._cooldown_until and now < self._cooldown_until:
            cooldown_remaining = int((self._cooldown_until - now).total_seconds())
        elif self._cooldown_until and now >= self._cooldown_until:
            # Cooldown just ended → activate post-cooldown boost
            if not self._post_cooldown_active:
                self._post_cooldown_active = True
                self._cooldown_until = None

        # Fetch recovery metadata from DB
        saved_state = await self.db.scheduler_state.find_one({"_id": "config"}, {"_id": 0})
        last_recovery = saved_state.get("last_auto_recovery") if saved_state else None
        last_updated = saved_state.get("updated_at") if saved_state else None

        return {
            "status": self._status.value,
            "deployment_mode": self._deployment_mode.value,
            "market_session": session.value,
            "can_execute": can_exec,
            "execution_reason": exec_reason,
            "risk_multiplier": self.session_manager.get_risk_multiplier(session),
            "pause_reason": self._pause_reason,
            "next_dt_scan_seconds": next_dt,
            "next_lt_scan_seconds": next_lt,
            "last_dt_scan": self._last_dt_scan.isoformat() if self._last_dt_scan else None,
            "last_lt_scan": self._last_lt_scan.isoformat() if self._last_lt_scan else None,
            "last_cycle_result": self._last_cycle_result,
            "cycle_count": self._cycle_count,
            "consecutive_losses": self._consecutive_losses,
            "cooldown_remaining_seconds": cooldown_remaining,
            "post_cooldown_active": self._post_cooldown_active,
            "daily_loss_pct_of_max": self._daily_loss_pct_of_max,
            "api_failure_count": self._api_failure_count,
            "auto_recovery_enabled": True,
            "last_auto_recovery": last_recovery,
            "last_state_save": last_updated,
            "settings": self._scheduler_settings,
        }

    async def get_notifications(self, limit: int = 50) -> List[Dict]:
        cursor = self.db.scheduler_notifications.find(
            {}, {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(limit)

    async def get_execution_log(self, limit: int = 50) -> List[Dict]:
        cursor = self.db.scheduler_execution_log.find(
            {}, {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(limit)

    # =================== INTERNAL LOOP ===================

    async def _scheduler_loop(self):
        logger.info("Scheduler loop started")
        while self._status == SchedulerStatus.RUNNING:
            try:
                now = _now_utc()
                session = self.session_manager.get_session()

                if session == MarketSession.CLOSED:
                    await asyncio.sleep(60)
                    continue

                # Day Trading Engine scan
                if self._next_dt_scan and now >= self._next_dt_scan:
                    await self._run_day_trade_cycle(session)
                    interval = self._scheduler_settings["dt_interval_seconds"]
                    
                    # Power Hours: First 2h (9:30-11:30) and last 2h (14:00-16:00) — scan faster
                    if self._scheduler_settings.get("prioritize_power_hours", True) and session == MarketSession.REGULAR:
                        try:
                            import pytz
                            et = pytz.timezone("US/Eastern")
                            now_et = now.astimezone(et)
                            hour_et = now_et.hour + now_et.minute / 60.0
                            if (9.5 <= hour_et <= 11.5) or (14.0 <= hour_et <= 16.0):
                                interval = max(120, interval // 2)  # 2x faster in power hours
                        except Exception:
                            pass
                    
                    self._next_dt_scan = now + timedelta(seconds=interval)
                    self._last_dt_scan = now

                # Long-Term Engine scan
                if self._next_lt_scan and now >= self._next_lt_scan:
                    await self._run_long_term_cycle(session)
                    interval = self._scheduler_settings["lt_interval_seconds"]
                    self._next_lt_scan = now + timedelta(seconds=interval)
                    self._last_lt_scan = now

                # Monitor existing positions (every tick)
                await self._monitor_positions_cycle(session)

                # Top Movers Scanner auto-refresh during regular hours
                if session == MarketSession.REGULAR:
                    try:
                        scanner = getattr(self.orchestrator, 'top_movers_scanner', None)
                        if scanner and scanner.should_refresh():
                            await scanner.scan()
                            logger.info(f"Top Movers Scanner refreshed: {len(scanner.get_accepted_symbols())} symbols")
                    except Exception as e:
                        logger.warning(f"Top movers auto-refresh failed: {e}")

                await asyncio.sleep(self.LOOP_TICK)

            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                self._api_failure_count += 1
                self._last_api_failure = _now_utc()
                if self._api_failure_count >= self._scheduler_settings["max_api_failures"]:
                    await self._auto_pause(f"API failures exceeded limit ({self._api_failure_count})")
                    break
                await asyncio.sleep(30)

        logger.info("Scheduler loop ended")

    async def _run_day_trade_cycle(self, session: MarketSession):
        """Run one day trading scan + execution cycle with enhanced safety.
        Uses the full TA pipeline (scan_opportunities) for enriched signals,
        then applies the scheduler's 7-gate execution pipeline."""
        safe, reasons = await self._check_safety("DAY_TRADE", session)
        if not safe:
            await self._log_execution("day_trade_skipped", {"reasons": reasons})
            return

        can_exec, exec_reason = self.session_manager.can_execute(session, self._scheduler_settings)

        try:
            settings = await self.orchestrator.get_settings()
            if not settings.dt_enabled:
                return

            market_regime = await self.orchestrator.regime_detector.detect()

            from ai_trading_system import (
                DynamicThresholdManager, ConfidenceScoringEngine,
                PositionSizer, TradeFrequencyController,
                TradePipelineFunnel, ZeroTradeDiagnostics
            )

            dynamic = DynamicThresholdManager.get_thresholds(
                market_regime, settings,
                post_cooldown=self._post_cooldown_active,
                daily_loss_pct=self._daily_loss_pct_of_max
            )
            threshold = dynamic["dt_threshold"]

            # Frequency control
            freq_ctrl = TradeFrequencyController(self.db)
            can_freq, freq_reason = await freq_ctrl.can_trade("DAY_TRADE", market_regime)
            if not can_freq:
                await self._log_execution("day_trade_freq_limited", {"reason": freq_reason})
                return

            # === CORE FIX: Use the full TA pipeline for enriched signals ===
            # scan_opportunities runs: prefilter → Tier1 fast TA → Tier2 deep TA → DayTradingEngine.evaluate_buy
            # This produces candidates with proper direction, structure, setup, MTF data
            scan_result = await self.orchestrator.scan_opportunities()

            # Extract TA-evaluated candidates from scan
            # These already passed DayTradingEngine.evaluate_buy with action=BUY/SELL
            candidates = scan_result.get("day_trades", [])
            scan_stats = scan_result.get("stats", {})

            # Dynamic max positions
            max_pos = DynamicThresholdManager.get_max_positions("DAY_TRADE", settings, market_regime)

            funnel = TradePipelineFunnel()
            diagnostics = ZeroTradeDiagnostics()
            funnel.record("universe_scanned", scan_stats.get("total_scanned", 0))
            funnel.record("prefilter_passed", scan_stats.get("prefilter_passed", 0))
            funnel.record("ta_analyzed", scan_stats.get("ta_analyzed", 0))
            funnel.record("setup_found", scan_stats.get("setups_found", 0))

            # Also score stored signals for confidence distribution tracking
            conf_distribution = scan_stats.get("confidence_distribution", {
                "elite_80_plus": 0, "strong_70_80": 0, "acceptable_60_70": 0, "below_60": 0
            })

            # Build score breakdowns for diagnostics from top candidates
            score_breakdowns = []
            for c in candidates[:15]:
                sig = c.get("signal", {})
                confidence = c.get("confidence", 0)
                _, breakdown = ConfidenceScoringEngine.score_day_trade(sig, market_regime, return_breakdown=True)
                score_breakdowns.append({
                    "symbol": c.get("symbol", ""),
                    "confidence": confidence,
                    "breakdown": breakdown,
                    "direction": c.get("direction", "NONE"),
                    "best_setup": c.get("best_setup", "none"),
                })

            top_breakdowns = score_breakdowns[:10]
            if top_breakdowns:
                logger.info(f"DT SCAN CANDIDATES ({len(candidates)} from TA pipeline):")
                for sb in top_breakdowns[:5]:
                    bd = sb["breakdown"]
                    logger.info(
                        f"  {sb['symbol']}: conf={sb['confidence']} dir={sb['direction']} setup={sb['best_setup']} | "
                        f"tech:{bd.get('technical_setup',{}).get('pts',0)} "
                        f"vol:{bd.get('volume',{}).get('pts',0)} "
                        f"rr:{bd.get('risk_reward',{}).get('pts',0)} "
                        f"trend:{bd.get('trend_alignment',{}).get('pts',0)} "
                        f"atr:{bd.get('volatility',{}).get('pts',0)}"
                    )

            # Filter candidates by scheduler threshold (scan may use a different one)
            qualified_candidates = []
            for c in candidates:
                confidence = c.get("confidence", 0)
                if confidence >= threshold:
                    qualified_candidates.append(c)
                    funnel.record("confidence_passed")
                elif confidence >= threshold - 5:
                    diagnostics.add_near_miss(
                        c.get("symbol", ""), "DAY_TRADE", confidence, "NEAR_MISS",
                        [f"Confidence {confidence} < scheduler threshold {threshold}"])

            account = await self.orchestrator.get_account()
            positions = await self.orchestrator.get_positions()
            equity = float(account.get("equity", 0))

            executed = []
            skipped = []
            scan_cycle_id = f"dt_{_now_utc().strftime('%Y%m%d_%H%M%S')}_{self._cycle_count}"

            # === TRANSPARENCY: Log every candidate's journey through execution gates ===
            if not can_exec:
                # All candidates blocked by timing/session/mode
                block_reason = "timing_block"
                block_detail = f"can_exec=False, session={session.value}, mode={self._deployment_mode.value}"
                if self._status == SchedulerStatus.PAUSED:
                    block_reason = "scheduler_paused"
                    block_detail = f"Scheduler paused: {self._pause_reason}"
                elif self._status == SchedulerStatus.EMERGENCY_STOP:
                    block_reason = "scheduler_paused"
                    block_detail = "Emergency stop active"
                elif session == MarketSession.CLOSED:
                    block_reason = "session_phase"
                    block_detail = "Market is closed"
                elif session in (MarketSession.PRE_MARKET, MarketSession.AFTER_HOURS):
                    block_reason = "session_phase"
                    block_detail = f"Session={session.value}, pre/after hours execution disabled"

                for c in qualified_candidates:
                    exp = c.get("explanation", {})
                    ki = exp.get("key_indicators", {})
                    await self.transparency.log_candidate_journey({
                        "symbol": c.get("symbol", ""), "engine": "day_trade",
                        "scan_cycle_id": scan_cycle_id,
                        "confidence": c.get("confidence", 0),
                        "signal_count": ki.get("signal_count", 0),
                        "direction": c.get("direction", ""),
                        "best_setup": c.get("best_setup", ""),
                        "is_top_mover": c.get("is_top_mover", False),
                        "price": c.get("signal", {}).get("price", 0),
                        "entry_reasons": exp.get("entry_reasons", []),
                        "stage_reached": "timing_blocked",
                        "outcome": "blocked",
                        "rejection_category": block_reason,
                        "rejection_reason": block_detail,
                        "market_session": session.value,
                        "market_regime": market_regime.get("regime", ""),
                        "risk_mode": dynamic["risk_mode"],
                        "threshold_used": threshold,
                    })

            elif self._deployment_mode in (DeploymentMode.SHADOW,):
                for c in qualified_candidates:
                    exp = c.get("explanation", {})
                    ki = exp.get("key_indicators", {})
                    await self.transparency.log_candidate_journey({
                        "symbol": c.get("symbol", ""), "engine": "day_trade",
                        "scan_cycle_id": scan_cycle_id,
                        "confidence": c.get("confidence", 0),
                        "signal_count": ki.get("signal_count", 0),
                        "direction": c.get("direction", ""),
                        "best_setup": c.get("best_setup", ""),
                        "price": c.get("signal", {}).get("price", 0),
                        "entry_reasons": exp.get("entry_reasons", []),
                        "stage_reached": "not_reached",
                        "outcome": "blocked",
                        "rejection_category": "shadow_mode",
                        "rejection_reason": "Shadow mode — logging only, no execution",
                        "market_session": session.value,
                        "market_regime": market_regime.get("regime", ""),
                        "risk_mode": dynamic["risk_mode"],
                        "threshold_used": threshold,
                    })

            else:
                risk_mult = self.session_manager.get_risk_multiplier(session)
                max_to_exec = min(3, max_pos) if session == MarketSession.CLOSING else min(5, max_pos)

                # Soft lock: reduce sizes if near daily loss limit
                soft_lock_mult = 1.0
                if self._daily_loss_pct_of_max >= 80:
                    soft_lock_mult = 0.5
                elif self._daily_loss_pct_of_max >= 60:
                    soft_lock_mult = 0.75

                # Check existing bot DT positions to prevent duplicates
                existing_bot_positions = set()
                try:
                    pos_list = await self.orchestrator.api_client.alpaca_positions()
                    if pos_list:
                        for p in pos_list:
                            existing_bot_positions.add(p.get("symbol", ""))
                except Exception:
                    pass

                exec_count = 0
                for i, c in enumerate(qualified_candidates):
                    exp = c.get("explanation", {})
                    ki = exp.get("key_indicators", {})
                    sig = c.get("signal", {})
                    base_entry = {
                        "symbol": c.get("symbol", ""), "engine": "day_trade",
                        "scan_cycle_id": scan_cycle_id,
                        "confidence": c.get("confidence", 0),
                        "signal_count": ki.get("signal_count", 0),
                        "direction": c.get("direction", ""),
                        "best_setup": c.get("best_setup", ""),
                        "is_top_mover": c.get("is_top_mover", False),
                        "price": sig.get("price", 0),
                        "entry_reasons": exp.get("entry_reasons", []),
                        "market_session": session.value,
                        "market_regime": market_regime.get("regime", ""),
                        "risk_mode": dynamic["risk_mode"],
                        "threshold_used": threshold,
                    }

                    symbol = c.get("symbol", "")

                    # Gate 1: Max trades per cycle
                    if exec_count >= max_to_exec:
                        await self.transparency.log_candidate_journey({
                            **base_entry,
                            "stage_reached": "candidate",
                            "outcome": "blocked",
                            "rejection_category": "max_trades_reached",
                            "rejection_reason": f"Max {max_to_exec} trades per cycle reached (executed {exec_count})",
                        })
                        skipped.append({"symbol": symbol, "reason": f"max_trades_reached ({max_to_exec})"})
                        continue

                    # Gate 2: Cooldown
                    if self._cooldown_until and _now_utc() < self._cooldown_until:
                        await self.transparency.log_candidate_journey({
                            **base_entry,
                            "stage_reached": "candidate",
                            "outcome": "blocked",
                            "rejection_category": "cooldown_active",
                            "rejection_reason": f"Post-loss cooldown until {self._cooldown_until.isoformat()}",
                        })
                        skipped.append({"symbol": symbol, "reason": "cooldown_active"})
                        continue

                    # Gate 3: Duplicate position
                    if symbol in existing_bot_positions:
                        await self.transparency.log_candidate_journey({
                            **base_entry,
                            "stage_reached": "candidate",
                            "outcome": "rejected",
                            "rejection_category": "duplicate_position",
                            "rejection_reason": f"Already holding {symbol}",
                        })
                        skipped.append({"symbol": symbol, "reason": "duplicate_position"})
                        continue

                    # Gate 3.5: Re-entry cooldown (prevent buying same symbol too soon after selling)
                    reentry_cooldown_min = self._scheduler_settings.get("reentry_cooldown_minutes", 30)
                    if reentry_cooldown_min > 0:
                        cutoff = _now_utc() - timedelta(minutes=reentry_cooldown_min)
                        recent_exit = await self.db.auto_trade_log.find_one({
                            "symbol": symbol,
                            "confidence": 0,  # exits are logged with confidence=0
                            "timestamp": {"$gte": cutoff.isoformat()},
                        })
                        if recent_exit:
                            exit_time = recent_exit.get("timestamp", "?")
                            await self.transparency.log_candidate_journey({
                                **base_entry,
                                "stage_reached": "candidate",
                                "outcome": "blocked",
                                "rejection_category": "reentry_cooldown",
                                "rejection_reason": f"Sold {symbol} at {str(exit_time)[:19]}, cooldown {reentry_cooldown_min}min",
                            })
                            skipped.append({"symbol": symbol, "reason": f"reentry_cooldown ({reentry_cooldown_min}min)"})
                            continue

                    # Gate 4: Soft lock
                    if self._daily_loss_pct_of_max >= 95:
                        await self.transparency.log_candidate_journey({
                            **base_entry,
                            "stage_reached": "candidate",
                            "outcome": "blocked",
                            "rejection_category": "soft_lock_block",
                            "rejection_reason": f"Near daily loss limit ({self._daily_loss_pct_of_max:.0f}% of max)",
                        })
                        skipped.append({"symbol": symbol, "reason": "soft_lock_block"})
                        continue

                    # Gate 5: Risk manager
                    approved, checks = await self.orchestrator.risk_manager.check_all(
                        sig, c.get("confidence", 0), "DAY_TRADE",
                        settings, account, positions, market_regime
                    )
                    if not approved:
                        violations = [ch for ch in checks if "VIOLATION" in ch]
                        await self.transparency.log_candidate_journey({
                            **base_entry,
                            "stage_reached": "rejected_by_risk",
                            "outcome": "rejected",
                            "rejection_category": "risk_violation",
                            "rejection_reason": "; ".join(violations) if violations else "Risk check failed",
                            "rejection_details": {"risk_checks": checks},
                        })
                        skipped.append({"symbol": symbol, "reason": "; ".join(violations)})
                        continue

                    # Gate 6: Position sizing
                    funnel.record("risk_approved")
                    stop_pct = abs(sig.get("indicators", {}).get("atr_pct", settings.dt_stop_loss_pct))
                    # Use TA-computed stop loss if available
                    ta_price = sig.get("price", 0)
                    ta_stop = sig.get("stop_loss", 0)
                    if ta_price > 0 and ta_stop > 0:
                        stop_pct = abs((ta_price - ta_stop) / ta_price * 100)
                    size = PositionSizer.calculate(
                        "DAY_TRADE", c.get("confidence", 0), settings, equity, stop_pct,
                        sig, market_regime, dynamic
                    )
                    shares = max(1, int(size["shares"] * risk_mult * self._get_size_multiplier() * soft_lock_mult))

                    if shares <= 0:
                        await self.transparency.log_candidate_journey({
                            **base_entry,
                            "stage_reached": "approved",
                            "outcome": "rejected",
                            "rejection_category": "safety_check_failed",
                            "rejection_reason": "Position sizing resulted in 0 shares",
                        })
                        skipped.append({"symbol": symbol, "reason": "zero_shares"})
                        continue

                    # Gate 7: Execute — with ownership + strategy tagging
                    # Determine order side from direction
                    direction = c.get("direction", "LONG")
                    order_side = "buy" if direction == "LONG" else "sell"
                    result = await self.orchestrator._place_order(
                        symbol, shares, order_side, "DAY_TRADE", c,
                        ownership="bot", strategy_type="day_trade"
                    )

                    if result.get("success"):
                        exec_count += 1
                        executed.append(result)
                        existing_bot_positions.add(symbol)
                        funnel.record("executed")
                        self._post_cooldown_active = False

                        await self.transparency.log_candidate_journey({
                            **base_entry,
                            "stage_reached": "executed",
                            "outcome": "executed",
                            "shares_executed": shares,
                            "execution_price": sig.get("price", 0),
                        })

                        await self._notify("trade_opened",
                            f"{'BUY' if order_side == 'buy' else 'SELL'} {symbol} x{shares} "
                            f"(DT, conf={c.get('confidence',0)}, setup={c.get('best_setup','')}, regime={dynamic['risk_mode']})", "info")

                        # Performance tracker logging
                        tracker = getattr(self.orchestrator, 'performance_tracker', None)
                        if tracker:
                            exit_plan = exp.get("exit_plan", {})
                            await tracker.log_trade_entry({
                                "symbol": symbol,
                                "classification": "DAY_TRADE",
                                "ownership": "bot",
                                "strategy_type": "day_trade",
                                "shares": shares,
                                "entry_price": sig.get("price", 0),
                                "position_value": size.get("value", 0),
                                "position_pct": size.get("pct_of_equity", 0),
                                "confidence": c.get("confidence", 0),
                                "stop_loss": exit_plan.get("stop_loss", 0),
                                "take_profit": exit_plan.get("take_profit", 0),
                                "partial_target": exit_plan.get("partial_target", 0),
                                "entry_reasons": exp.get("entry_reasons", []),
                                "signal_count": ki.get("signal_count", 0),
                                "signals_aligned": ki.get("signals_aligned", ""),
                                "best_setup": c.get("best_setup", ""),
                                "direction": direction,
                                "momentum_mode": c.get("momentum_mode", False),
                                "is_top_mover": c.get("is_top_mover", False),
                                "source": c.get("source", "universe"),
                                "market_regime": market_regime,
                                "regime_label": market_regime.get("regime", "unknown"),
                                "risk_mode": dynamic["risk_mode"],
                                "dynamic_threshold": threshold,
                            })
                    else:
                        await self.transparency.log_candidate_journey({
                            **base_entry,
                            "stage_reached": "submitted",
                            "outcome": "rejected",
                            "rejection_category": "order_failed",
                            "rejection_reason": result.get("error", "Order submission failed"),
                        })
                        skipped.append({"symbol": symbol, "reason": result.get("error")})

            # Zero-trade diagnostics
            no_trade_summary = diagnostics.build_no_trade_summary(
                len(qualified_candidates), 0, market_regime)

            cycle_result = {
                "engine": "day_trade",
                "session": session.value,
                "scan_candidates_from_ta": len(candidates),
                "qualified_candidates": len(qualified_candidates),
                "executed": len(executed),
                "skipped": len(skipped),
                "mode": self._deployment_mode.value,
                "risk_mode": dynamic["risk_mode"],
                "threshold_used": threshold,
                "near_misses": len(diagnostics._near_misses) if hasattr(diagnostics, '_near_misses') else 0,
                "opportunity_quality": no_trade_summary.get("opportunity_quality", "LOW_OPPORTUNITY"),
                "funnel": funnel.to_dict(),
                "scan_stats": scan_stats,
                "confidence_distribution": conf_distribution,
                "top_score_breakdowns": [
                    {"symbol": sb["symbol"], "confidence": sb["confidence"],
                     "direction": sb.get("direction", ""), "best_setup": sb.get("best_setup", ""),
                     "breakdown": sb["breakdown"]}
                    for sb in top_breakdowns[:5]
                ],
                "details": {"executed": executed, "skipped": skipped, "top_candidates": [
                    {"symbol": c.get("symbol",""), "confidence": c.get("confidence",0),
                     "direction": c.get("direction",""), "best_setup": c.get("best_setup","")}
                    for c in qualified_candidates[:10]
                ]}
            }

            # Log results
            logger.info(
                f"DT CYCLE | TA candidates: {len(candidates)} | qualified (>={threshold}): {len(qualified_candidates)} | "
                f"executed: {len(executed)} | skipped: {len(skipped)} | "
                f"conf_dist: elite={conf_distribution.get('elite_80_plus',0)} strong={conf_distribution.get('strong_70_80',0)} "
                f"accept={conf_distribution.get('acceptable_60_70',0)}"
            )
            self._last_cycle_result = cycle_result
            self._cycle_count += 1
            await self._log_execution("day_trade_cycle", cycle_result)

            # === PERFORMANCE TRACKER: Log scan cycle pipeline ===
            tracker = getattr(self.orchestrator, 'performance_tracker', None)
            if tracker:
                await tracker.log_scan_cycle({
                    "total_scanned": scan_stats.get("total_scanned", 0),
                    "top_movers_injected": scan_stats.get("top_movers_injected", 0),
                    "prefilter_passed": scan_stats.get("prefilter_passed", 0),
                    "ta_analyzed": scan_stats.get("ta_analyzed", 0),
                    "setups_found": scan_stats.get("setups_found", 0),
                    "filters_passed": scan_stats.get("filters_passed", 0),
                    "confidence_passed": scan_stats.get("day_trade_candidates", 0),
                    "candidates": len(qualified_candidates),
                    "executed": len(executed),
                    "top_rejections": funnel.to_dict().get("top_rejections", {}),
                    "market_regime": market_regime.get("regime", "unknown"),
                    "risk_mode": dynamic["risk_mode"],
                    "threshold_used": threshold,
                })

            # Persist confidence distribution for post-session analysis
            await self.db.confidence_distribution.insert_one({
                "date": _now_et().date().isoformat(),
                "timestamp": _now_utc().isoformat(),
                "session": session.value,
                "threshold_used": threshold,
                "scan_candidates": len(candidates),
                "qualified_candidates": len(qualified_candidates),
                "distribution": conf_distribution,
                "executed": len(executed),
                "regime": market_regime,
            })

            # Full-day zero-trade alert
            if len(qualified_candidates) == 0 and session == MarketSession.REGULAR:
                await self._notify("no_trades",
                    f"No day trades: {'; '.join(no_trade_summary.get('top_reasons', [])[:3])}", "info")

        except Exception as e:
            logger.error(f"Day trade cycle error: {e}")
            self._api_failure_count += 1
            await self._log_execution("day_trade_error", {"error": str(e)})

    async def _run_long_term_cycle(self, session: MarketSession):
        """Run one long-term investment scan + execution cycle with enhanced safety"""
        safe, reasons = await self._check_safety("LONG_TERM", session)
        if not safe:
            await self._log_execution("long_term_skipped", {"reasons": reasons})
            return

        can_exec, _ = self.session_manager.can_execute(session, self._scheduler_settings)

        try:
            settings = await self.orchestrator.get_settings()
            if not settings.lt_enabled:
                return

            market_regime = await self.orchestrator.regime_detector.detect()

            from ai_trading_system import (
                StockClassifier, ConfidenceScoringEngine,
                LongTermEngine, PositionSizer, DynamicThresholdManager,
                TradeFrequencyController
            )

            dynamic = DynamicThresholdManager.get_thresholds(
                market_regime, settings,
                post_cooldown=self._post_cooldown_active,
                daily_loss_pct=self._daily_loss_pct_of_max
            )
            threshold = dynamic["lt_threshold"]

            freq_ctrl = TradeFrequencyController(self.db)
            can_freq, freq_reason = await freq_ctrl.can_trade("LONG_TERM", market_regime)
            if not can_freq:
                await self._log_execution("long_term_freq_limited", {"reason": freq_reason})
                return

            inv_signals = await self.db.investment_signals.find({}, {"_id": 0}).to_list(2000)
            if not inv_signals:
                return

            account = await self.orchestrator.get_account()
            positions = await self.orchestrator.get_positions()
            equity = float(account.get("equity", 0))

            trade_signals = await self.db.trading_signals.find({}, {"_id": 0}).to_list(2000)
            trade_lookup = {s["symbol"]: s for s in trade_signals if s.get("symbol")}

            max_pos = DynamicThresholdManager.get_max_positions("LONG_TERM", settings, market_regime)

            candidates = []
            for sig in inv_signals:
                symbol = sig.get("symbol", "")
                if not symbol:
                    continue

                cls_result = StockClassifier.classify(trade_lookup.get(symbol), sig)
                if cls_result["classification"] != "LONG_TERM":
                    continue

                confidence = ConfidenceScoringEngine.score_long_term(sig, market_regime)
                if confidence < threshold:
                    continue

                explanation = LongTermEngine.evaluate_buy(sig, market_regime, settings)
                explanation.confidence_score = confidence

                if explanation.action == "BUY":
                    candidates.append({
                        "symbol": symbol,
                        "confidence": confidence,
                        "explanation": explanation.dict(),
                        "signal": sig
                    })

            candidates.sort(key=lambda x: x["confidence"], reverse=True)

            executed = []
            skipped = []

            if can_exec and self._deployment_mode not in (DeploymentMode.SHADOW,):
                risk_mult = self.session_manager.get_risk_multiplier(session)

                soft_lock_mult = 1.0
                if self._daily_loss_pct_of_max >= 80:
                    soft_lock_mult = 0.5

                for c in candidates[:min(3, max_pos)]:
                    approved, checks = await self.orchestrator.risk_manager.check_all(
                        c["signal"], c["confidence"], "LONG_TERM",
                        settings, account, positions, market_regime
                    )
                    if approved:
                        size = PositionSizer.calculate(
                            "LONG_TERM", c["confidence"], settings, equity,
                            settings.lt_trailing_stop_pct, c["signal"],
                            market_regime, dynamic
                        )
                        shares = max(1, int(size["shares"] * risk_mult * self._get_size_multiplier() * soft_lock_mult))
                        if shares > 0:
                            result = await self.orchestrator._place_order(
                                c["symbol"], shares, "buy", "LONG_TERM", c
                            )
                            if result.get("success"):
                                executed.append(result)
                                self._post_cooldown_active = False
                                await self._notify("trade_opened",
                                    f"BUY {c['symbol']} x{shares} (LT, conf={c['confidence']}, regime={dynamic['risk_mode']})", "info")
                            else:
                                skipped.append({"symbol": c["symbol"], "reason": result.get("error")})
                    else:
                        skipped.append({"symbol": c["symbol"], "reason": "; ".join(
                            ch for ch in checks if "VIOLATION" in ch)})

            cycle_result = {
                "engine": "long_term",
                "session": session.value,
                "candidates": len(candidates),
                "executed": len(executed),
                "skipped": len(skipped),
                "mode": self._deployment_mode.value,
                "risk_mode": dynamic["risk_mode"],
                "threshold_used": threshold,
                "details": {"executed": executed, "skipped": skipped, "top_candidates": [
                    {"symbol": c["symbol"], "confidence": c["confidence"]} for c in candidates[:10]
                ]}
            }
            self._last_cycle_result = cycle_result
            self._cycle_count += 1
            await self._log_execution("long_term_cycle", cycle_result)

        except Exception as e:
            logger.error(f"Long-term cycle error: {e}")
            self._api_failure_count += 1
            await self._log_execution("long_term_error", {"error": str(e)})

    async def _monitor_positions_cycle(self, session: MarketSession):
        """Check existing positions for exit signals (TP, SL, trailing, thesis break, time)"""
        try:
            settings = await self.orchestrator.get_settings()
            market_regime = await self.orchestrator.regime_detector.detect()
            sell_results = await self.orchestrator._monitor_positions(settings, market_regime)

            for sell in sell_results:
                pnl = sell.get("pnl", 0)
                symbol = sell.get("symbol", "")
                reasons = sell.get("reason", [])

                # === PERFORMANCE TRACKER: Log trade exit ===
                tracker = getattr(self.orchestrator, 'performance_tracker', None)
                if tracker:
                    await tracker.log_trade_exit({
                        "symbol": symbol,
                        "classification": "DAY_TRADE",
                        "shares": sell.get("shares", 0),
                        "entry_price": sell.get("entry_price", 0),
                        "exit_price": sell.get("exit_price", sell.get("price", 0)),
                        "pnl": pnl,
                        "exit_reasons": reasons if isinstance(reasons, list) else [str(reasons)],
                        "entry_time": sell.get("entry_time"),
                        "confidence": sell.get("confidence", 0),
                        "best_setup": sell.get("best_setup", ""),
                        "entry_signals": sell.get("entry_signals", []),
                        "signal_count": sell.get("signal_count", 0),
                        "is_top_mover": sell.get("is_top_mover", False),
                        "source": sell.get("source", "universe"),
                        "entry_regime": sell.get("entry_regime", "unknown"),
                        "exit_regime": sell.get("exit_regime", "unknown"),
                        "risk_mode": sell.get("risk_mode", "NORMAL"),
                        "stop_loss": sell.get("stop_loss", 0),
                        "entry_time_window": sell.get("entry_time_window", "unknown"),
                    })

                if pnl < 0:
                    self._consecutive_losses += 1
                    if any("stop" in str(r).lower() for r in reasons):
                        await self._notify("stop_loss_hit",
                            f"STOP LOSS: {symbol} P&L=${pnl:.2f}", "warning")
                    else:
                        await self._notify("trade_closed",
                            f"SELL {symbol} P&L=${pnl:.2f} ({'; '.join(str(r) for r in reasons)})", "info")
                else:
                    self._consecutive_losses = 0
                    if any("take profit" in str(r).lower() for r in reasons):
                        await self._notify("take_profit_hit",
                            f"TAKE PROFIT: {symbol} P&L=+${pnl:.2f}", "info")
                    elif any("thesis" in str(r).lower() or "deterioration" in str(r).lower() for r in reasons):
                        await self._notify("thesis_break",
                            f"THESIS BREAK: {symbol} - {'; '.join(str(r) for r in reasons)}", "warning")
                    else:
                        await self._notify("trade_closed",
                            f"SELL {symbol} P&L=${'+' if pnl >=0 else ''}{pnl:.2f}", "info")

                if self._consecutive_losses >= self._scheduler_settings["max_consecutive_losses"]:
                    cooldown_min = self._scheduler_settings["cooldown_minutes"]
                    self._cooldown_until = _now_utc() + timedelta(minutes=cooldown_min)
                    self._post_cooldown_active = False  # Will activate when cooldown ends
                    await self._notify("auto_paused",
                        f"Cooldown activated: {self._consecutive_losses} consecutive losses. "
                        f"Resuming in {cooldown_min} min (thresholds will be raised by +{self._scheduler_settings.get('post_cooldown_threshold_boost', 5)} after)",
                        "warning")

        except Exception as e:
            logger.error(f"Position monitor error: {e}")

    # =================== SAFETY & RISK ===================

    async def _check_safety(self, engine: str, session: MarketSession) -> Tuple[bool, List[str]]:
        reasons = []

        if self._status == SchedulerStatus.EMERGENCY_STOP:
            return False, ["Emergency stop active"]

        if self._status == SchedulerStatus.PAUSED:
            return False, [f"Scheduler paused: {self._pause_reason}"]

        # Cooldown check
        if self._cooldown_until and _now_utc() < self._cooldown_until:
            remaining = int((self._cooldown_until - _now_utc()).total_seconds())
            reasons.append(f"Cooldown active: {remaining}s remaining")
            return False, reasons

        # Closing session - no weak day trades
        if session == MarketSession.CLOSING and engine == "DAY_TRADE":
            min_conf = self._scheduler_settings.get("min_confidence_day", 80) + 15
            reasons.append(f"Closing session: raised DT confidence to {min_conf}")

        # API failure check
        if self._api_failure_count >= self._scheduler_settings["max_api_failures"]:
            reasons.append(f"API failures ({self._api_failure_count}) exceeded limit")
            return False, reasons

        # Daily loss check with soft lock tracking
        try:
            account = await self.orchestrator.get_account()
            equity = float(account.get("equity", 0))
            daily_pnl = await self.orchestrator.risk_manager._get_daily_pnl()
            max_loss = equity * (self._scheduler_settings["max_daily_loss_pct"] / 100)

            # Track how close we are to daily loss limit (for soft lock)
            if max_loss > 0 and daily_pnl < 0:
                self._daily_loss_pct_of_max = min(100, int(abs(daily_pnl) / max_loss * 100))
            else:
                self._daily_loss_pct_of_max = 0

            if daily_pnl < -max_loss:
                reasons.append(f"Daily loss limit: ${daily_pnl:.0f} (max -${max_loss:.0f})")
                await self._notify("daily_loss_limit",
                    f"Daily loss limit reached: ${daily_pnl:.0f}", "critical")
                return False, reasons

            # Soft lock at 80% of daily max
            soft_lock_pct = self._scheduler_settings.get("soft_lock_daily_loss_pct", 80)
            if self._daily_loss_pct_of_max >= soft_lock_pct:
                reasons.append(f"Soft lock: {self._daily_loss_pct_of_max}% of daily loss used (positions reduced)")

            # Drawdown check
            peak = await self.orchestrator.risk_manager._get_peak_equity(equity)
            dd = ((equity - peak) / peak * 100) if peak > 0 else 0
            max_dd = self._scheduler_settings["max_portfolio_drawdown_pct"]
            if dd < -max_dd:
                reasons.append(f"Drawdown limit: {dd:.1f}% (max -{max_dd}%)")
                return False, reasons
        except Exception as e:
            logger.warning(f"Safety check error: {e}")

        return len(reasons) == 0 or all("Soft lock" in r or "Closing session" in r for r in reasons), reasons

    async def _auto_pause(self, reason: str):
        self._status = SchedulerStatus.PAUSED
        self._pause_reason = reason
        await self._save_state()
        await self._notify("auto_paused", f"Auto-trading paused: {reason}", "critical")

    def _get_confidence_threshold(self, engine: str) -> int:
        base = (self._scheduler_settings["min_confidence_day"]
                if engine == "DAY_TRADE"
                else self._scheduler_settings["min_confidence_long"])
        if self._deployment_mode in (DeploymentMode.LIMITED_LIVE, DeploymentMode.FULL_LIVE):
            base += self._scheduler_settings.get("live_confidence_boost", 10)
        return base

    def _get_size_multiplier(self) -> float:
        if self._deployment_mode == DeploymentMode.PAPER:
            return 1.0
        elif self._deployment_mode == DeploymentMode.SHADOW:
            return 0.0
        elif self._deployment_mode == DeploymentMode.LIMITED_LIVE:
            return self._scheduler_settings.get("live_position_size_multiplier", 0.5)
        return 1.0

    # =================== NOTIFICATIONS & LOGGING ===================

    async def _notify(self, event: str, message: str, severity: str = "info"):
        doc = {
            "event": event,
            "message": message,
            "severity": severity,
            "timestamp": _now_utc().isoformat(),
            "read": False
        }
        await self.db.scheduler_notifications.insert_one(doc)
        logger.info(f"[NOTIFY:{severity}] {event}: {message}")

    async def _log_execution(self, action: str, data: Dict):
        doc = {
            "action": action,
            "data": data,
            "deployment_mode": self._deployment_mode.value,
            "market_session": self.session_manager.get_session().value,
            "timestamp": _now_utc().isoformat()
        }
        await self.db.scheduler_execution_log.insert_one(doc)

    async def mark_notifications_read(self) -> int:
        result = await self.db.scheduler_notifications.update_many(
            {"read": False}, {"$set": {"read": True}}
        )
        return result.modified_count
