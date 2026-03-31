# ObaidTradez - AI Trading & Investing Platform

## Original Problem Statement
Secure, dark-themed AI day trading and long-term investing platform. Dual modes: Trading (TA pipeline) and Investments (fundamentals). Autonomous paper trading with live price streaming, dynamic re-evaluation, validated price integrity, overvaluation protection, and automated market-open verification.

## Architecture
```
/app/backend/
├── ai_trading_system.py      (Orchestrator, entry_status: TRADE_NOW/WATCHLIST/MISSED/STALE_SETUP/BLOWN_STOP)
├── enhanced_investment_engine.py (Scoring with overvaluation penalty)
├── auto_trade_scheduler.py   (Background loop, MongoDB auto-recovery)
├── live_price_engine.py      (Alpaca WS + REST fallback)
├── live_reeval_engine.py     (Dynamic re-eval on price changes)
├── price_integrity.py        (Single source of truth, dead ticker detection)
├── reeval_verifier.py        (Market-open automated verification)
└── server.py                 (FastAPI routes)
```

## Completed (March 31, 2026)
- [x] Live Prices: WS + REST fallback, SSE stream, mode indicator UI
- [x] Dynamic Re-Evaluation: VWAP/S-R/breakout triggers, 30s throttle
- [x] Price Integrity: 167 dead tickers flagged, 14 ticker renames, freshness validation
- [x] Overvaluation penalty: stocks with upside < -25% blocked from "Buy"
- [x] Entry status: TRADE_NOW/WATCHLIST/MISSED/STALE_SETUP/BLOWN_STOP
- [x] Debug: price_audit in scan, /api/debug/price_integrity, /api/debug/ticker_mappings
- [x] Market-open auto-verifier: captures re-eval events for 30 min, health checks, persists to MongoDB

## Key Verification Endpoints
- `GET /api/reeval/verify` — Live verification report with health checks
- `POST /api/reeval/verify/start` — Manual start
- `POST /api/reeval/verify/stop` — Manual stop + final report

## Upcoming
- [ ] Check verification report after next market open (9:30 AM ET)
- [ ] Compare stocks side-by-side (P3)
- [ ] Modularize server.py and AutoTrade.jsx (P3)

## Access: `Bullishalmarkhan7.7`
