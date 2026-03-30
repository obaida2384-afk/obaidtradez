# ObaidTradez - AI Trading & Investing Platform

## Original Problem Statement
Secure, dark-themed AI day trading and long-term investing platform protected by access code (`Bullishalmarkhan7.7`). Dual modes: Trading (short-term TA pipeline) and Investments (long-term fundamentals). Tiered Technical Analysis via Polygon OHLCV data with MTF confirmation, Momentum Mode bypass, and strict risk controls.

## Current Phase: Validation & Autonomous Paper Trading
The platform is in a **validation phase** — no new trading strategies. Focus on trustworthy tests, execution data, and analytics. Autonomous paper trading is ACTIVE.

## Architecture
```
/app/
├── backend/
│   ├── ai_trading_system.py (Orchestrator, Risk Manager, Trade Logging, LT Engine, Momentum Diagnostics)
│   ├── technical_analysis_engine.py (TA math, MTF, Confidence Scoring)
│   ├── auto_trade_scheduler.py
│   ├── tests/conftest.py (URL config for all tests)
│   ├── tests/ (22 test files, 345 tests, 100% pass rate)
│   └── server.py (FastAPI routes)
├── frontend/
│   ├── src/pages/AutoTrade.jsx (Scheduler, Diagnostics, Candidates, MTF Heatmap, Trade Log, Analytics, LT Pipeline, Momentum, Guide)
```

## Key DB Collections
- `trade_log`: Full lifecycle trade records (executed + skipped, slippage, timing, P&L)
- `auto_trade_log`: Basic execution log
- `auto_trade_settings`: Dynamic thresholds + auto_enabled
- `paper_execution_settings`: auto_execution, manual_approval, kill_switch, block_extended_hours
- `trading_signals`, `paper_trades`, `watchlist`, `investment_signals`

## Key API Endpoints
- `/api/auto-trade/scan` — Tiered pipeline + lt_pipeline + momentum_diagnostics
- `/api/auto-trade/analytics` — Full analytics dashboard (win rate, P&L, drawdown, slippage, etc.)
- `/api/auto-trade/trade-log` — Full lifecycle trade log (executed + skipped)
- `/api/auto-trade/mtf-heatmap` — MTF distribution
- `/api/scheduler/start` — Start autonomous scheduler
- `/api/scheduler/status` — Check scheduler state
- `/api/paper/settings` — Paper execution settings (auto_execution, manual_approval, etc.)

## Current Autonomous Trading Configuration (March 30, 2026)
- Scheduler: RUNNING (paper mode)
- Auto Execution: ON
- Manual Approval: OFF (fully autonomous)
- Kill Switch: OFF
- Pre-market/After-hours: BLOCKED
- Execution window: 9:30 AM - 4:00 PM ET, Mon-Fri
- DT scan interval: 5 min, LT scan interval: 30 min
- Alpaca Paper Account: $100K equity, ACTIVE
- Max daily loss: 3.0%, Max consecutive losses: 2 (then 30 min cooldown)

## Completed Features (Validation Phase - March 2026)
- [x] Backend Test Gap: 345/345 tests passing (100%)
- [x] Execution Validation Logging: signal/exec timestamps, slippage, skip reasons, actual exit reason
- [x] Trade Log Analytics Dashboard: total trades, win rate, avg win/loss, R multiple, P&L, drawdown, long vs short, by setup type, by confidence band, by session, P&L curve, skip/rejection reasons, slippage stats, execution timing
- [x] LT Pipeline Transparency: funnel visualization, confidence distribution, rejection reasons, top 10 missed opportunities
- [x] Momentum Mode Diagnostics: near-miss candidates, blocked conditions, filter status STRICT
- [x] Autonomous Paper Trading: Verified Alpaca connection, order submission, trade logging, scheduler started

## Previously Completed Features
- [x] Tiered TA Pipeline (Tier 1 fast scan -> Tier 2 deep analysis)
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
- [ ] Review first autonomous trading session results (P0 - next morning)
- [ ] Persistent auto-start on server boot (P1 - after validation)
- [ ] Daily Summary Generator (P2)
- [ ] Scheduler Performance Tracker (P3)
- [ ] Compare stocks side-by-side (P3)
- [ ] server.py modularization refactor (P3)

## Access
- Access Code: `Bullishalmarkhan7.7`

## 3rd Party Integrations
- OpenAI GPT-5.2 (Emergent LLM Key)
- Polygon.io (User API Key, Starter Plan)
- Alpaca (User API Key, Paper Trading - VERIFIED WORKING)
- FMP / Finnhub (User API Keys)
