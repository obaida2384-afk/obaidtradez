# ObaidTradez - AI Trading & Investing Platform

## Original Problem Statement
Secure, dark-themed AI day trading and long-term investing platform protected by access code (`Bullishalmarkhan7.7`). Dual modes: Trading (short-term TA pipeline) and Investments (long-term fundamentals). Tiered Technical Analysis via Polygon OHLCV data with MTF confirmation, Momentum Mode bypass, and strict risk controls.

## Current Phase: Validation & Diagnostics
The platform is in a **validation phase** — no new trading strategies. Focus on trustworthy tests, execution data, and analytics.

## Architecture
```
/app/
├── backend/
│   ├── ai_trading_system.py (Orchestrator, Risk Manager, Trade Logging, LT Engine, Momentum Diagnostics)
│   ├── technical_analysis_engine.py (TA math, MTF, Confidence Scoring)
│   ├── auto_trade_scheduler.py
│   ├── tests/conftest.py (URL config for all tests)
│   ├── tests/ (22 test files, 345 tests)
│   └── server.py (FastAPI routes)
├── frontend/
│   ├── src/pages/AutoTrade.jsx (Scheduler, Diagnostics, Candidates, MTF Heatmap, Trade Log, Analytics, LT Pipeline, Momentum, Guide)
```

## Key DB Collections
- `trade_log`: Full lifecycle trade records (executed + skipped, slippage, timing, P&L)
- `auto_trade_log`: Basic execution log
- `auto_trade_settings`: Dynamic thresholds
- `trading_signals`, `paper_trades`, `watchlist`, `investment_signals`

## Key API Endpoints
- `/api/auto-trade/scan` — Tiered pipeline + lt_pipeline + momentum_diagnostics
- `/api/auto-trade/analytics` — Win rate, P&L, drawdown, by setup/confidence/session, skip/rejection reasons, slippage, timing
- `/api/auto-trade/trade-log` — Full lifecycle trade log (executed + skipped)
- `/api/auto-trade/mtf-heatmap` — MTF distribution

## Completed Features (Validation Phase - March 2026)
- [x] Backend Test Gap: 345/345 tests passing (100%)
- [x] Execution Validation Logging: signal/exec timestamps, slippage, skip reasons, actual exit reason
- [x] Trade Log Analytics Dashboard: total trades, win rate, avg win/loss, R multiple, P&L, drawdown, long vs short, by setup type, by confidence band, by session, P&L curve, skip/rejection reasons, slippage stats, execution timing
- [x] LT Pipeline Transparency: funnel visualization, confidence distribution, rejection reasons, top 10 missed opportunities
- [x] Momentum Mode Diagnostics: near-miss candidates, blocked conditions (RelVol, spread, VWAP), filter status (STRICT unchanged)

## Previously Completed Features
- [x] Tiered TA Pipeline (Tier 1 fast scan → Tier 2 deep analysis)
- [x] Multi-Timeframe Confirmation (15m trend, 5m structure, 1m timing)
- [x] Momentum Mode Bypass for explosive stocks
- [x] Pre-Market Safety gate (no execution before 9:30 AM ET)
- [x] MTF Heatmap UI
- [x] Algorithm Explanation User Guide tab
- [x] Strict trade quality filters (volume, timing, trend, spread)
- [x] MongoDB trade logging system
- [x] 1,097+ company universe with background batch processing
- [x] Risky stocks blocklist (83+ meme/crypto/leveraged)

## Upcoming / Backlog
- [ ] Daily Summary Generator (P2)
- [ ] Scheduler Performance Tracker (P3)
- [ ] Compare stocks side-by-side (P3)
- [ ] server.py modularization refactor (P3)

## Access
- Access Code: `Bullishalmarkhan7.7`

## 3rd Party Integrations
- OpenAI GPT-5.2 (Emergent LLM Key)
- Polygon.io (User API Key, Starter Plan)
- Alpaca (User API Key, Paper Trading)
- FMP / Finnhub (User API Keys)
