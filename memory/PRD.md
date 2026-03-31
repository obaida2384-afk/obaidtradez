# ObaidTradez - AI Trading & Investing Platform

## Original Problem Statement
Secure, dark-themed AI day trading and long-term investing platform protected by access code (`Bullishalmarkhan7.7`). Dual modes: Trading (short-term TA pipeline) and Investments (long-term fundamentals). Tiered Technical Analysis via Polygon OHLCV data with MTF confirmation, Momentum Mode bypass, and strict risk controls. Autonomous paper trading with live price streaming and dynamic re-evaluation.

## Current Phase: Live Price Integration & Dynamic Re-Evaluation
The platform runs autonomous paper trading with live Alpaca WebSocket price streaming. Dynamic re-evaluation triggers TA checks on meaningful price changes without waiting for the 5-minute scheduler scan.

## Architecture
```
/app/
├── backend/
│   ├── ai_trading_system.py (Orchestrator, Risk Manager, Trade Logging, DT/LT Engines)
│   ├── technical_analysis_engine.py (TA math, MTF, Confidence Scoring)
│   ├── auto_trade_scheduler.py (Background loop, state auto-recovery from MongoDB)
│   ├── live_price_engine.py (Alpaca WebSocket + REST fallback, stale detection)
│   ├── live_reeval_engine.py (Dynamic re-evaluation on price changes)
│   ├── tests/conftest.py, test_live_prices_reeval.py
│   └── server.py (FastAPI routes)
├── frontend/
│   ├── src/hooks/useLivePrices.js (SSE + polling, LiveIndicator, watchlist/positions hooks)
│   ├── src/pages/AutoTrade.jsx (Scheduler, Diagnostics, Live Prices, Re-Eval UI)
```

## Key DB Collections
- `trade_log`: Full lifecycle trade records
- `auto_trade_log`: Basic execution log
- `auto_trade_settings`: Dynamic thresholds + auto_enabled
- `paper_execution_settings`: auto_execution, manual_approval, kill_switch
- `scheduler_state`: Persists deployment_mode and status for auto-recovery
- `reeval_events`: Dynamic re-evaluation event log

## Key API Endpoints
- `/api/auto-trade/scan` — Tiered pipeline
- `/api/auto-trade/analytics` — Full analytics dashboard
- `/api/scheduler/start` — Start autonomous scheduler
- `/api/live-prices/start` — Start live price engine
- `/api/live-prices/all` — All tracked prices + engine status
- `/api/live-prices/stream` — SSE stream (token via query param)
- `/api/live-prices/status/engine` — Engine status with mode
- `/api/reeval/stats` — Re-evaluation engine statistics
- `/api/reeval/events` — Recent re-eval events
- `/api/reeval/history` — Persisted re-eval events from MongoDB

## Completed Features (March 31, 2026)
- [x] Fixed React hook ordering bug in AutoTrade.jsx (token before useLivePrices)
- [x] Fixed Alpaca WebSocket infinite reconnect (graceful fallback to REST after 3 failures)
- [x] Fixed FastAPI route ordering (static routes before {symbol} wildcard)
- [x] Fixed SSE auth (token via query param for EventSource compatibility)
- [x] Added missing exports: LiveIndicator, useWatchlistPrices, usePositionsPrices
- [x] Live Prices UI: Mode indicator (WebSocket/REST/Offline), engine stats, price table
- [x] Dynamic Re-Evaluation Engine: triggers on VWAP crossings, S/R touches, breakout/breakdown, stop-loss/take-profit, spread changes, overextension
- [x] Re-eval throttling: max 1 eval per symbol per 30s
- [x] Re-eval logging: MongoDB persistence + in-memory ring buffer
- [x] Re-eval UI: stats grid + event cards in Live Prices tab
- [x] **Price Sync Engine**: Bulk-updates all cached signal prices from Alpaca snapshots (startup + every 5 min during market hours + manual trigger). Fixes stale prices like MRVL showing $94.88 instead of actual $87.84

## Previously Completed Features
- [x] Tiered TA Pipeline (Tier 1 fast scan -> Tier 2 deep analysis)
- [x] Multi-Timeframe Confirmation (15m trend, 5m structure, 1m timing)
- [x] Momentum Mode Bypass for explosive stocks
- [x] Autonomous Paper Trading with MongoDB auto-recovery
- [x] Backend Test Suite: 345+ tests passing
- [x] Execution Validation Logging (slippage, timing, skip reasons)
- [x] Trade Analytics Dashboard
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
