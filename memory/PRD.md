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
│   ├── live_reeval_engine.py (Dynamic re-evaluation, TRADE_NOW/WATCHLIST/MISSED classification)
│   ├── price_integrity.py (Single source of truth, freshness validation, ticker normalization, dead ticker detection)
│   ├── tests/
│   └── server.py (FastAPI routes)
├── frontend/
│   ├── src/hooks/useLivePrices.js (SSE + polling, LiveIndicator, watchlist/positions hooks)
│   ├── src/pages/AutoTrade.jsx (Scheduler, Diagnostics, Live Prices, Re-Eval UI)
```

## Key DB Collections
- `trading_signals`: Cached TA signals with dead_ticker, price_status, price_source, price_synced_at, live_bid, live_ask
- `investment_signals`: Fundamental signals with same price integrity fields
- `trade_log`, `auto_trade_log`, `auto_trade_settings`, `scheduler_state`, `reeval_events`

## Key API Endpoints
- `/api/debug/price_integrity` — Full universe audit (dead/stale/healthy counts)
- `/api/debug/price_integrity/{symbol}` — Single symbol: validated price, DB cached, mismatch, ticker_canonical, is_renamed
- `/api/debug/ticker_mappings` — Known renames (14) + dead tickers (165+) + stats
- `/api/prices/sync-signals` — Manual price sync {updated, dead_flagged, rejected, total}
- `/api/live-prices/stream` — SSE stream (token via query param)
- `/api/live-prices/status/engine` — Engine status with mode
- `/api/reeval/stats` — Re-evaluation engine statistics
- `/api/reeval/events` — Recent re-eval events
- `/api/auto-trade/scan` — Returns price_data, entry_status, price_audit per candidate

## Completed (March 31, 2026)
### Phase 1: Live Price Fix
- [x] Fixed React hook ordering bug in AutoTrade.jsx
- [x] Fixed Alpaca WebSocket infinite reconnect (graceful REST fallback after 3 failures)
- [x] Fixed FastAPI route ordering (static routes before {symbol} wildcard)
- [x] Fixed SSE auth (token via query param for EventSource)
- [x] Added LiveIndicator, useWatchlistPrices, usePositionsPrices exports
- [x] Live Prices UI: Mode indicator (WebSocket/REST/Offline), engine stats, price table
- [x] Dynamic Re-Evaluation Engine: VWAP, S/R, breakout/breakdown, stop-loss/TP, spread, overextension

### Phase 2: Price Integrity (P1 Bug Fix)
- [x] Price Integrity Service (single source of truth) — validates trade freshness, rejects >5-day-old trades
- [x] 165+ dead/renamed tickers flagged and excluded from all scans and trading
- [x] Price sync on startup + every 5 min during market hours

### Phase 3: Full P2 Requirements
- [x] #1 Single source of truth: All prices from Alpaca snapshots/WS, never stale candle close
- [x] #2 Ticker normalization: 14 known renames (ZI→GTM, TWTR→X, FB→META, etc.), logged on resolution
- [x] #3 Price freshness: Timestamp, age, stale flag on every price; dead ticker detection
- [x] #4 Sync UI + algorithm: price_data block in every candidate with price/source/synced_at/status/bid/ask
- [x] #5 Recompute on change: entry_status classification (TRADE_NOW/WATCHLIST/MISSED) in re-eval + scan
- [x] #6 Debug logging: price_audit (50 entries) in scan response with per-symbol price/source/status/stale/entry_status
- [x] #7 Diagnostics: /api/debug/price_integrity, /api/debug/ticker_mappings

## Previously Completed
- [x] Tiered TA Pipeline, MTF Confirmation, Momentum Mode Bypass
- [x] Autonomous Paper Trading with MongoDB auto-recovery
- [x] Backend Test Suite: 345+ tests passing
- [x] Execution Validation Logging, Trade Analytics Dashboard
- [x] LT Pipeline Transparency + Momentum Diagnostics

## Upcoming / Backlog
- [ ] Verify live re-evaluation during market hours (P0 — next market open)
- [ ] Compare stocks side-by-side (P3)
- [ ] Modularize server.py and AutoTrade.jsx (P3)

## Access
- Access Code: `Bullishalmarkhan7.7`

## 3rd Party Integrations
- OpenAI GPT-5.2 (Emergent LLM Key)
- Polygon.io (User API Key)
- Alpaca (User API Key, Paper Trading + WebSocket)
- FMP / Finnhub (User API Keys)
