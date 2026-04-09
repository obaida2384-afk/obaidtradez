"""
ObaidTradez Execution Transparency Engine
Logs the complete journey of every candidate from detection → evaluation → execution/rejection.
Provides clear answers to "why didn't this trade execute?"
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

REJECTION_CATEGORIES = {
    "timing_block": "Execution timing — market session does not allow execution",
    "session_phase": "Market phase (pre-market/after-hours/closing) blocked execution",
    "closing_hour_tightening": "Closing hour — confidence threshold raised, candidate below raised minimum",
    "confidence_below_threshold": "Confidence score below dynamic threshold for current session",
    "entry_window_expired": "Entry window expired — signal too old or price moved past entry zone",
    "liquidity_spread": "Liquidity/spread rule — bid-ask spread too wide or volume too thin",
    "duplicate_position": "Duplicate position — already holding this symbol",
    "ownership_mismatch": "Ownership mismatch — position belongs to different strategy",
    "risk_violation": "Risk manager violation (daily loss, drawdown, position count, concentration)",
    "max_trades_reached": "Maximum daily trades reached",
    "cooldown_active": "Post-loss cooldown active",
    "scheduler_paused": "Scheduler paused or emergency stop",
    "shadow_mode": "Shadow/paper-only mode — no live execution",
    "order_failed": "Order submission failed at Alpaca",
    "classifier_mismatch": "Stock classified for different strategy (not DAY_TRADE)",
    "safety_check_failed": "Pre-execution safety check failed",
    "soft_lock_block": "Near daily loss limit — reduced or blocked execution",
    "unknown": "Unknown blocker",
}


class ExecutionTransparencyTracker:
    """Tracks every qualified candidate through the execution pipeline."""

    def __init__(self, db):
        self.db = db
        self.collection = "execution_transparency"

    async def log_candidate_journey(self, entry: Dict):
        """Log a candidate's full pipeline journey."""
        doc = {
            "symbol": entry.get("symbol", ""),
            "engine": entry.get("engine", "day_trade"),
            "scan_cycle_id": entry.get("scan_cycle_id", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),

            # Signal quality
            "confidence": entry.get("confidence", 0),
            "signal_count": entry.get("signal_count", 0),
            "direction": entry.get("direction", ""),
            "best_setup": entry.get("best_setup", ""),
            "is_top_mover": entry.get("is_top_mover", False),
            "price": entry.get("price", 0),
            "entry_reasons": entry.get("entry_reasons", []),

            # Pipeline stages
            "stage_reached": entry.get("stage_reached", "candidate"),
            # candidate → risk_check → approved → submitted → executed
            # candidate → risk_check → rejected_by_risk
            # candidate → timing_blocked
            # candidate → not_reached (can_exec=False)

            # Final outcome
            "outcome": entry.get("outcome", "unknown"),
            # "executed", "rejected", "blocked", "skipped"

            # Rejection details (if not executed)
            "rejection_category": entry.get("rejection_category", ""),
            "rejection_reason": entry.get("rejection_reason", ""),
            "rejection_details": entry.get("rejection_details", {}),

            # Execution details (if executed)
            "shares_executed": entry.get("shares_executed", 0),
            "execution_price": entry.get("execution_price", 0),

            # Context
            "market_session": entry.get("market_session", ""),
            "market_regime": entry.get("market_regime", ""),
            "risk_mode": entry.get("risk_mode", ""),
            "threshold_used": entry.get("threshold_used", 0),
            "dynamic_threshold": entry.get("dynamic_threshold", {}),
        }
        await self.db[self.collection].insert_one(doc)
        logger.info(
            f"TRANSPARENCY | {doc['symbol']} | stage={doc['stage_reached']} | "
            f"outcome={doc['outcome']} | reason={doc['rejection_category'] or 'N/A'}"
        )

    async def get_rejection_report(self, date: str = None, engine: str = None, limit: int = 100) -> Dict:
        """Get a full rejection report for a date/engine."""
        query = {}
        if date:
            query["date"] = date
        if engine:
            query["engine"] = engine

        cursor = self.db[self.collection].find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
        entries = await cursor.to_list(length=limit)

        # Summary stats
        executed = [e for e in entries if e.get("outcome") == "executed"]
        rejected = [e for e in entries if e.get("outcome") in ("rejected", "blocked", "skipped")]

        # Rejection breakdown
        rejection_breakdown = {}
        for e in rejected:
            cat = e.get("rejection_category", "unknown")
            rejection_breakdown[cat] = rejection_breakdown.get(cat, 0) + 1

        # Strong candidates that were NOT executed
        strong_missed = [
            e for e in rejected
            if e.get("confidence", 0) >= 70 and e.get("signal_count", 0) >= 3
        ]

        return {
            "total_candidates": len(entries),
            "executed": len(executed),
            "rejected": len(rejected),
            "execution_rate": round(len(executed) / len(entries) * 100, 1) if entries else 0,
            "rejection_breakdown": rejection_breakdown,
            "strong_candidates_missed": len(strong_missed),
            "strong_missed_details": [{
                "symbol": e["symbol"],
                "confidence": e["confidence"],
                "signal_count": e.get("signal_count", 0),
                "best_setup": e.get("best_setup", ""),
                "rejection_category": e.get("rejection_category", ""),
                "rejection_reason": e.get("rejection_reason", ""),
            } for e in strong_missed],
            "entries": entries,
            "rejection_categories": REJECTION_CATEGORIES,
        }

    async def get_pipeline_stages(self, date: str = None) -> Dict:
        """Breakdown showing how many candidates reached each pipeline stage."""
        query = {}
        if date:
            query["date"] = date

        cursor = self.db[self.collection].find(query, {"_id": 0, "stage_reached": 1, "outcome": 1})
        entries = await cursor.to_list(length=1000)

        stages = {
            "candidate": 0,
            "timing_blocked": 0,
            "risk_check": 0,
            "approved": 0,
            "submitted": 0,
            "executed": 0,
            "rejected_by_risk": 0,
            "not_reached": 0,
        }
        for e in entries:
            stage = e.get("stage_reached", "candidate")
            stages[stage] = stages.get(stage, 0) + 1

        return {"date": date, "stages": stages, "total": len(entries)}
