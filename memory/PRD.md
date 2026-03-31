# ObaidTradez - AI Trading & Investing Platform

## Original Problem Statement
Secure, dark-themed AI day trading and long-term investing platform protected by access code (`Bullishalmarkhan7.7`). Dual modes: Trading (short-term TA pipeline) and Investments (long-term fundamentals). Tiered Technical Analysis via Polygon OHLCV data with MTF confirmation, Momentum Mode bypass, and strict risk controls. Autonomous paper trading with live price streaming, dynamic re-evaluation, and validated price integrity.

## Architecture
```
/app/
├── backend/
│   ├── ai_trading_system.py (Orchestrator, Risk Manager, Trade Logging, DT/LT Engines)
│   ├── technical_analysis_engine.py (TA math, MTF, Confidence Scoring)
│   ├── auto_trade_scheduler.py (Background loop, state auto-recovery from MongoDB)
│   ├── live_price_engine.py (Alpaca WebSocket + REST fallback, stale detection)
│   ├── live_reeval_engine.py (Dynamic re-evaluation on price changes)
│   ├── price_integrity.py (Single source of truth, freshness validation, dead ticker detection)
│   ├── tests/conftest.py, test_live_prices_reeval.py, test_price_integrity.py
│   └── server.py (FastAPI routes)
├── frontend/
│   ├── src/hooks/useLivePrices.js (SSE + polling, LiveIndicator, watchlist/positions hooks)
│   ├── src/pages/AutoTrade.jsx (Scheduler, Diagnostics, Live Prices, Re-Eval UI)
```

## Key DB Collections
- `trading_signals`: Cached TA signals with `dead_ticker`, `price_status`, `price_source`, `price_synced_at` fields
- `investment_signals`: Fundamental signals with same price integrity fields
- `trade_log`, `auto_trade_log`, `auto_trade_settings`, `scheduler_state`, `reeval_events`

## Key API Endpoints
- `/api/debug/price_integrity` — Full universe audit (dead/stale/healthy counts)
- `/api/debug/price_integrity/{symbol}` — Single symbol integrity check
- `/api/prices/sync-signals` — Manual price sync trigger
- `/api/live-prices/stream` — SSE stream (token via query param)
- `/api/live-prices/status/engine` — Engine status with mode
- `/api/reeval/stats` — Re-evaluation engine statistics
- `/api/reeval/events` — Recent re-eval events
- `/api/auto-trade/scan`, `/api/investments/scan` — Both filter out dead_ticker=true

## Completed (March 31, 2026)
- [x] Fixed React hook ordering bug in AutoTrade.jsx
- [x] Fixed Alpaca WebSocket infinite reconnect (graceful fallback to REST after 3 failures)
- [x] Fixed FastAPI route ordering (static routes before {symbol} wildcard)
- [x] Fixed SSE auth (token via query param for EventSource)
- [x] Added LiveIndicator, useWatchlistPrices, usePositionsPrices exports
- [x] Live Prices UI: Mode indicator (WebSocket/REST/Offline), engine stats, price table
- [x] Dynamic Re-Evaluation Engine: VWAP, S/R, breakout/breakdown, stop-loss/TP, spread, overextension
- [x] Re-eval throttling (30s/symbol), MongoDB logging, UI stats + event cards
- [x] **P1: Price Integrity Service** — Single source of truth. Validates trade freshness (rejects >5-day-old trades). Identified and flagged 175 dead/renamed tickers (ZI->GTM, TWTR->X, SIVB, etc.). All scan endpoints filter dead_ticker!=true.
- [x] Price sync on startup + every 5 min during market hours
- [x] Diagnostics endpoint `/api/debug/price_integrity` for real-time auditing

## Previously Completed
- [x] Tiered TA Pipeline, MTF Confirmation, Momentum Mode Bypass
- [x] Autonomous Paper Trading with MongoDB auto-recovery
- [x] Backend Test Suite: 345+ tests passing
- [x] Execution Validation Logging, Trade Analytics Dashboard
- [x] LT Pipeline Transparency + Momentum Diagnostics

## Upcoming / Backlog
- [ ] Verify re-evaluation during live market hours (P0 - next market open)
- [ ] Compare stocks side-by-side (P3)
- [ ] Modularize server.py and AutoTrade.jsx (P3)

## Access
- Access Code: `Bullishalmarkhan7.7`

## 3rd Party Integrations
- OpenAI GPT-5.2 (Emergent LLM Key)
- Polygon.io (User API Key, Starter Plan)
- Alpaca (User API Key, Paper Trading + WebSocket Market Data)
- FMP / Finnhub (User API Keys)
