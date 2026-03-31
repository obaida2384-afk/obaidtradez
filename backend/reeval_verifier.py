"""
Market-Open Live Re-Evaluation Verifier
Automatically captures and validates re-evaluation events when the market opens.
Provides a /api/reeval/verify endpoint for on-demand status checks.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# How many events to capture before stopping detailed logging
MAX_VERIFICATION_EVENTS = 50
# How long to run verification after market open (seconds)
VERIFICATION_WINDOW_SECONDS = 1800  # 30 minutes


class ReEvalVerifier:
    """Captures and validates re-evaluation events during market open."""

    def __init__(self):
        self._active = False
        self._started_at: Optional[str] = None
        self._events: List[Dict] = []
        self._price_snapshots: Dict[str, Dict] = {}  # symbol -> first seen price
        self._symbol_event_count: Dict[str, int] = {}
        self._summary = {
            "total_events": 0,
            "unique_symbols": 0,
            "setup_changes": 0,
            "confidence_changes": 0,
            "entry_status_changes": 0,
            "stop_target_hits": 0,
            "position_actions": 0,
            "stale_setups_detected": 0,
            "blown_stops_detected": 0,
            "trade_now_signals": 0,
            "missed_signals": 0,
            "data_sources": {"live": 0, "snapshot": 0, "other": 0},
            "triggers": {},
        }
        self._ws_status_at_start: Optional[Dict] = None
        self._ws_status_latest: Optional[Dict] = None
        self._errors: List[str] = []

    def start(self, engine_status: Dict):
        """Start verification window."""
        self._active = True
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._ws_status_at_start = engine_status
        self._events = []
        self._price_snapshots = {}
        self._symbol_event_count = {}
        self._errors = []
        # Reset summary counters
        for k in self._summary:
            if isinstance(self._summary[k], int):
                self._summary[k] = 0
            elif isinstance(self._summary[k], dict):
                self._summary[k] = {} if k == "triggers" else {"live": 0, "snapshot": 0, "other": 0}
        logger.info(f"ReEval Verifier STARTED — capturing events for {VERIFICATION_WINDOW_SECONDS}s")

    def stop(self):
        self._active = False
        logger.info(f"ReEval Verifier STOPPED — captured {len(self._events)} events across {len(self._symbol_event_count)} symbols")

    @property
    def is_active(self) -> bool:
        return self._active

    def record_event(self, event_dict: Dict):
        """Record a re-evaluation event for verification."""
        if not self._active:
            return

        symbol = event_dict.get("symbol", "")
        self._summary["total_events"] += 1

        # Track per-symbol
        self._symbol_event_count[symbol] = self._symbol_event_count.get(symbol, 0) + 1
        self._summary["unique_symbols"] = len(self._symbol_event_count)

        # Capture first price for each symbol
        if symbol not in self._price_snapshots:
            self._price_snapshots[symbol] = {
                "first_price": event_dict.get("new_price", 0),
                "first_seen": event_dict.get("timestamp", ""),
            }

        # Count change types
        if event_dict.get("setup_changed"):
            self._summary["setup_changes"] += 1
        if event_dict.get("confidence_changed"):
            self._summary["confidence_changes"] += 1
        if event_dict.get("entry_readiness_changed"):
            self._summary["entry_status_changes"] += 1
        if event_dict.get("stop_target_changed"):
            self._summary["stop_target_hits"] += 1
        if event_dict.get("position_action"):
            self._summary["position_actions"] += 1

        # Track entry status
        for detail in event_dict.get("details", []):
            if "STALE_SETUP" in str(detail):
                self._summary["stale_setups_detected"] += 1
            if "BLOWN_STOP" in str(detail):
                self._summary["blown_stops_detected"] += 1
            if "TRADE_NOW" in str(detail):
                self._summary["trade_now_signals"] += 1
            if "MISSED" in str(detail):
                self._summary["missed_signals"] += 1

        # Track data source
        source = event_dict.get("data_source", "other")
        if source in self._summary["data_sources"]:
            self._summary["data_sources"][source] += 1
        else:
            self._summary["data_sources"]["other"] += 1

        # Track trigger types
        trigger = event_dict.get("trigger_reason", "")
        for keyword in ["VWAP", "BREAKOUT", "BREAKDOWN", "Support", "Resistance", "Spread", "Overextension", "Price moved"]:
            if keyword.lower() in trigger.lower():
                self._summary["triggers"][keyword] = self._summary["triggers"].get(keyword, 0) + 1

        # Store detailed event (capped)
        if len(self._events) < MAX_VERIFICATION_EVENTS:
            self._events.append({
                "seq": len(self._events) + 1,
                **event_dict,
            })

    def update_engine_status(self, status: Dict):
        self._ws_status_latest = status

    def record_error(self, error: str):
        if self._active and len(self._errors) < 20:
            self._errors.append(f"{datetime.now(timezone.utc).isoformat()}: {error}")

    def get_report(self) -> Dict:
        """Generate the verification report."""
        now = datetime.now(timezone.utc)
        elapsed = 0
        if self._started_at:
            try:
                start = datetime.fromisoformat(self._started_at)
                elapsed = (now - start).total_seconds()
            except (ValueError, TypeError):
                pass

        # Build per-symbol summary
        symbol_summaries = []
        for sym, count in sorted(self._symbol_event_count.items(), key=lambda x: -x[1]):
            snap = self._price_snapshots.get(sym, {})
            # Find latest event for this symbol
            latest = None
            for e in reversed(self._events):
                if e.get("symbol") == sym:
                    latest = e
                    break
            symbol_summaries.append({
                "symbol": sym,
                "event_count": count,
                "first_price": snap.get("first_price", 0),
                "latest_price": latest.get("new_price", 0) if latest else 0,
                "price_change": round(latest["new_price"] - snap.get("first_price", 0), 4) if latest and snap.get("first_price") else 0,
                "latest_trigger": latest.get("trigger_reason", "") if latest else "",
            })

        # Health checks
        health = []
        if self._ws_status_latest:
            ws = self._ws_status_latest
            if ws.get("ws_connected"):
                health.append({"check": "WebSocket", "status": "PASS", "detail": "Connected via WS"})
            elif ws.get("mode") == "rest_fallback":
                health.append({"check": "WebSocket", "status": "WARN", "detail": "Fell back to REST polling"})
            else:
                health.append({"check": "WebSocket", "status": "FAIL", "detail": f"Mode: {ws.get('mode')}"})

            if ws.get("stale_count", 0) == 0:
                health.append({"check": "Stale Data", "status": "PASS", "detail": "No stale symbols"})
            else:
                health.append({"check": "Stale Data", "status": "WARN", "detail": f"{ws['stale_count']} symbols stale"})

            trades_rx = ws.get("stats", {}).get("trades_received", 0)
            if trades_rx > 0:
                health.append({"check": "Trade Data", "status": "PASS", "detail": f"{trades_rx} trades received"})
            else:
                health.append({"check": "Trade Data", "status": "WARN", "detail": "No trades received yet"})

        if self._summary["total_events"] > 0:
            health.append({"check": "Re-eval Pipeline", "status": "PASS", "detail": f"{self._summary['total_events']} events triggered"})
        elif elapsed > 600:  # 10 minutes with no events
            health.append({"check": "Re-eval Pipeline", "status": "WARN", "detail": f"No events after {elapsed:.0f}s — check price change thresholds"})

        if not self._errors:
            health.append({"check": "Errors", "status": "PASS", "detail": "No errors"})
        else:
            health.append({"check": "Errors", "status": "FAIL", "detail": f"{len(self._errors)} errors logged"})

        return {
            "active": self._active,
            "started_at": self._started_at,
            "elapsed_seconds": round(elapsed, 1),
            "summary": self._summary,
            "health_checks": health,
            "symbol_summaries": symbol_summaries[:20],
            "recent_events": self._events[-10:],
            "engine_status_at_start": self._ws_status_at_start,
            "engine_status_current": self._ws_status_latest,
            "errors": self._errors,
        }
