# ObaidTradez - AI Trading & Investing Platform

## Original Problem Statement
Secure, dark-themed AI day trading and long-term investing platform protected by access code (`Bullishalmarkhan7.7`). Dual modes: Trading (short-term TA pipeline) and Investments (long-term fundamentals). Tiered Technical Analysis via Polygon OHLCV data with MTF confirmation, Momentum Mode bypass, and strict risk controls. Autonomous paper trading with live price streaming, dynamic re-evaluation, validated price integrity, and overvaluation protection.

## Architecture
```
/app/
├── backend/
│   ├── ai_trading_system.py (Orchestrator, Risk Manager, Trade Logging, DT/LT Engines, entry_status classification)
│   ├── enhanced_investment_engine.py (Fundamental scoring with overvaluation penalty)
│   ├── technical_analysis_engine.py (TA math, MTF, Confidence Scoring)
│   ├── auto_trade_scheduler.py (Background loop, state auto-recovery from MongoDB)
│   ├── live_price_engine.py (Alpaca WebSocket + REST fallback, stale detection)
│   ├── live_reeval_engine.py (Dynamic re-evaluation, TRADE_NOW/WATCHLIST/MISSED/STALE_SETUP/BLOWN_STOP)
│   ├── price_integrity.py (Single source of truth, freshness validation, ticker normalization, dead ticker detection)
│   ├── tests/
│   └── server.py (FastAPI routes)
├── frontend/
│   ├── src/hooks/useLivePrices.js (SSE + polling, LiveIndicator, watchlist/positions hooks)
│   ├── src/pages/AutoTrade.jsx (Scheduler, Diagnostics, Live Prices, Re-Eval UI)
```

## Completed (March 31, 2026)

### Phase 1: Live Price Fix
- [x] Fixed React hook ordering, WS infinite reconnect, FastAPI route ordering, SSE auth
- [x] Live Prices UI with mode indicator, engine stats, REST fallback
- [x] Dynamic Re-Evaluation Engine with VWAP/S-R/breakout triggers

### Phase 2: Price Integrity
- [x] Price Integrity Service — validates trade freshness, 165+ dead tickers flagged
- [x] 14 known ticker renames (ZI→GTM, TWTR→X, FB→META, etc.)
- [x] price_data + entry_status in every candidate, price_audit debug logging
- [x] Diagnostics: /api/debug/price_integrity, /api/debug/ticker_mappings

### Phase 3: Scoring & Setup Validation Fix (P1 Bug)
- [x] **Overvaluation penalty**: stocks with upside < -25% get score penalty, blocked from "Buy"
- [x] **Entry status classification**: TRADE_NOW / WATCHLIST / MISSED / STALE_SETUP (>10% drift) / BLOWN_STOP (price at/below stop)
- [x] **Investment scan override**: stocks with upside < -25% or "Overvalued" classification forced to "Overpriced/Hold"
- [x] MRVL fixed: was "Hot/Buy" with -76% upside → now "Overpriced/Hold"
- [x] 463 overvalued stocks correctly moved to Overpriced category

## Key API Endpoints
- `/api/debug/price_integrity` — Full universe audit
- `/api/debug/price_integrity/{symbol}` — Single symbol with ticker_canonical, is_renamed
- `/api/debug/ticker_mappings` — Known renames + dead tickers
- `/api/prices/sync-signals` — Manual price sync
- `/api/auto-trade/scan` — Returns price_data, entry_status, price_audit
- `/api/investments/scan` — Categories: hot, bullish, undervalued, overpriced, bearish, watch

## Upcoming / Backlog
- [ ] Verify live re-evaluation during market hours (P0)
- [ ] Compare stocks side-by-side (P3)
- [ ] Modularize server.py and AutoTrade.jsx (P3)

## Access: `Bullishalmarkhan7.7`
